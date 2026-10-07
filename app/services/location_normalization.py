from __future__ import annotations

import asyncio
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
from dataclasses import dataclass
from time import monotonic
from time import time
from urllib.parse import parse_qs
from urllib.parse import quote_plus
from urllib.parse import unquote
from urllib.parse import unquote_plus
from urllib.parse import urljoin
from urllib.parse import urlparse

import httpx


NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_MIN_INTERVAL_SECONDS = 1.05
NOMINATIM_CACHE_TTL_SECONDS = 86400
NOMINATIM_USER_AGENT = (
    "CargoPT/1.0 (+https://cargopt.pt; contact: hello@cargopt.pt)"
)

_nominatim_cache: dict[tuple[str, tuple[tuple[str, str], ...]], tuple[float, list]] = {}


def _configured_nominatim_provider_url() -> str:
    return os.environ.get("LOCATION_SEARCH_PROVIDER_URL", NOMINATIM_SEARCH_URL)


def _nominatim_shared_state_path() -> Path:
    return Path(
        os.environ.get(
            "LOCATION_SEARCH_CACHE_PATH",
            "data/nominatim_shared_state.sqlite3",
        )
    )


def _claim_nominatim_request(
    cache_key: str,
) -> tuple[str, float | list]:
    state_path = _nominatim_shared_state_path()
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(state_path, timeout=10, isolation_level=None)
        try:
            connection.execute("PRAGMA busy_timeout=10000")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS nominatim_cache (
                    cache_key TEXT PRIMARY KEY,
                    response_json TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS nominatim_rate_state (
                    state_key TEXT PRIMARY KEY,
                    last_request_started_at REAL NOT NULL
                )
                """
            )
            connection.execute("BEGIN IMMEDIATE")
            now = time()
            cached = connection.execute(
                """
                SELECT response_json
                FROM nominatim_cache
                WHERE cache_key = ? AND expires_at > ?
                """,
                (cache_key, now),
            ).fetchone()
            if cached is not None:
                connection.commit()
                data = json.loads(cached[0])
                if not isinstance(data, list):
                    raise ValueError("unexpected shared Nominatim cache value")
                return "cached", data

            connection.execute(
                "DELETE FROM nominatim_cache WHERE expires_at <= ?",
                (now,),
            )
            rate_state = connection.execute(
                """
                SELECT last_request_started_at
                FROM nominatim_rate_state
                WHERE state_key = ?
                """,
                ("provider",),
            ).fetchone()
            last_request_started_at = rate_state[0] if rate_state else 0.0
            wait_seconds = NOMINATIM_MIN_INTERVAL_SECONDS - (
                now - last_request_started_at
            )
            if wait_seconds > 0:
                connection.commit()
                return "wait", wait_seconds

            connection.execute(
                """
                INSERT INTO nominatim_rate_state (
                    state_key,
                    last_request_started_at
                ) VALUES (?, ?)
                ON CONFLICT(state_key) DO UPDATE SET
                    last_request_started_at = excluded.last_request_started_at
                """,
                ("provider", now),
            )
            connection.commit()
            return "reserved", 0.0
        finally:
            connection.close()
    except (OSError, sqlite3.Error) as exc:
        raise ValueError("Nominatim shared state unavailable") from exc


async def _read_shared_cache_or_reserve(cache_key: str) -> list | None:
    while True:
        action, value = await asyncio.to_thread(
            _claim_nominatim_request,
            cache_key,
        )
        if action == "cached":
            return value if isinstance(value, list) else []
        if action == "reserved":
            return None
        wait_seconds = float(value)
        await asyncio.sleep(wait_seconds)


def _store_nominatim_shared_cache(cache_key: str, data: list) -> None:
    state_path = _nominatim_shared_state_path()
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(state_path, timeout=10)
        try:
            connection.execute("PRAGMA busy_timeout=10000")
            connection.execute(
                """
                INSERT INTO nominatim_cache (
                    cache_key,
                    response_json,
                    expires_at
                ) VALUES (?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    response_json = excluded.response_json,
                    expires_at = excluded.expires_at
                """,
                (
                    cache_key,
                    json.dumps(data, ensure_ascii=False, separators=(",", ":")),
                    time() + NOMINATIM_CACHE_TTL_SECONDS,
                ),
            )
            connection.commit()
        finally:
            connection.close()
    except (OSError, sqlite3.Error) as exc:
        raise ValueError("Nominatim shared cache unavailable") from exc

LOCATION_SEARCH_LANGUAGES = {
    "pt": "pt-PT,pt;q=0.9",
    "en": "en",
    "ru": "ru",
}


@dataclass(frozen=True)
class LocationSuggestion:
    display_name: str
    latitude: float
    longitude: float
    map_url: str
    country_code: str = "pt"
    postal_code: str | None = None
    address_details_hint: str | None = None


async def _nominatim_search(
    *,
    provider_url: str,
    params: dict[str, str],
    wrap_object: bool = False,
) -> list:
    cache_key = (provider_url, tuple(sorted(params.items())))
    now = monotonic()
    cached = _nominatim_cache.get(cache_key)
    if cached is not None and cached[0] > now:
        return cached[1]

    serialized_key = json.dumps(
        [provider_url, sorted(params.items())],
        ensure_ascii=True,
        separators=(",", ":"),
    )
    shared_cached = await _read_shared_cache_or_reserve(serialized_key)
    if shared_cached is not None:
        _nominatim_cache[cache_key] = (
            monotonic() + NOMINATIM_CACHE_TTL_SECONDS,
            shared_cached,
        )
        return shared_cached

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(5.0),
        headers={"User-Agent": NOMINATIM_USER_AGENT},
    ) as client:
        response = await client.get(provider_url, params=params)
        response.raise_for_status()
        data = response.json()

    if wrap_object and isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ValueError("unexpected Nominatim response")

    await asyncio.to_thread(_store_nominatim_shared_cache, serialized_key, data)
    _nominatim_cache[cache_key] = (
        monotonic() + NOMINATIM_CACHE_TTL_SECONDS,
        data,
    )
    return data


MAPS_URL_RE = re.compile(
    r"https?://(?:www\.)?(?:(?:google\.[^\s]+/maps|maps\.app\.goo\.gl|goo\.gl/maps)|(?:maps?\.apple\.com)|(?:waze\.com/ul|ul\.waze\.com/ul))[^\s]*",
    re.IGNORECASE,
)

TRUSTED_MAPS_HOSTS = frozenset(
    {
        "consent.google.com",
        "consent.google.pt",
        "goo.gl",
        "google.com",
        "google.pt",
        "maps.app.goo.gl",
        "maps.apple.com",
        "maps.google.com",
        "maps.google.pt",
        "ul.waze.com",
        "waze.com",
        "www.google.com",
        "www.google.pt",
        "www.waze.com",
    }
)
MAPS_REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})
MAPS_MAX_REDIRECTS = 5

POSTAL_CODE_RE = re.compile(r"\b\d{4}-\d{3}\b")

COORDINATE_RE = re.compile(
    r"(?P<lat>-?\d{1,2}\.\d+)\s*,\s*(?P<lon>-?\d{1,3}\.\d+)"
)

GOOGLE_PLACE_COORDINATE_RE = re.compile(
    r"!3d(?P<lat>-?\d{1,2}\.\d+)!4d(?P<lon>-?\d{1,3}\.\d+)"
)


def extract_maps_url(raw_text: str) -> str | None:
    match = MAPS_URL_RE.search(raw_text)
    if not match:
        return None
    candidate = match.group(0).rstrip(".,;)")
    if not is_trusted_maps_url(candidate):
        return None
    return candidate


def is_trusted_maps_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError:
        return False

    return (
        parsed.scheme.casefold() == "https"
        and parsed.username is None
        and parsed.password is None
        and port in (None, 443)
        and (parsed.hostname or "").casefold() in TRUSTED_MAPS_HOSTS
    )


async def _maps_url_resolves_to_public_ips(url: str) -> bool:
    parsed = urlparse(url)
    hostname = parsed.hostname
    if hostname is None:
        return False

    try:
        addresses = await asyncio.to_thread(
            socket.getaddrinfo,
            hostname,
            443,
            type=socket.SOCK_STREAM,
        )
    except OSError:
        return False

    resolved_ips = {
        ipaddress.ip_address(sockaddr[0])
        for *_, sockaddr in addresses
    }
    return bool(resolved_ips) and all(address.is_global for address in resolved_ips)


def extract_postal_code(raw_text: str) -> str | None:
    match = POSTAL_CODE_RE.search(raw_text)
    if not match:
        return None
    return match.group(0)


def _valid_coordinates(
    latitude: float,
    longitude: float,
) -> tuple[float | None, float | None]:
    if not (-90 <= latitude <= 90):
        return None, None

    if not (-180 <= longitude <= 180):
        return None, None

    return latitude, longitude


def extract_coordinates(raw_text: str) -> tuple[float | None, float | None]:
    decoded = unquote(raw_text)

    place_match = GOOGLE_PLACE_COORDINATE_RE.search(decoded)
    if place_match:
        return _valid_coordinates(
            float(place_match.group("lat")),
            float(place_match.group("lon")),
        )

    parsed = urlparse(decoded)
    query = parse_qs(parsed.query)
    for key in ("q", "query", "ll"):
        for value in query.get(key, []):
            query_match = COORDINATE_RE.search(value)
            if query_match:
                return _valid_coordinates(
                    float(query_match.group("lat")),
                    float(query_match.group("lon")),
                )

    match = COORDINATE_RE.search(decoded)
    if not match:
        return None, None

    return _valid_coordinates(
        float(match.group("lat")),
        float(match.group("lon")),
    )


def build_google_maps_search_url(raw_text: str) -> str:
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(raw_text)


def build_google_maps_coordinate_url(latitude: float, longitude: float) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"


def strip_maps_url(raw_text: str) -> str:
    maps_url = extract_maps_url(raw_text)
    if maps_url is None:
        return raw_text.strip()

    return raw_text.replace(maps_url, "").strip(" \n\t,.;-")


def extract_google_continue_url(raw_text: str) -> str | None:
    parsed = urlparse(raw_text)
    if "consent.google." not in parsed.netloc:
        return None

    values = parse_qs(parsed.query).get("continue", [])
    if not values:
        return None

    return values[0]


def extract_google_maps_query_address(raw_text: str) -> str | None:
    parsed = urlparse(raw_text)
    query_values = parse_qs(parsed.query).get("q", [])
    if not query_values:
        return None

    value = query_values[0].strip()
    if not value:
        return None

    latitude, longitude = extract_coordinates(value)
    if latitude is not None and longitude is not None:
        return None

    return value


def extract_link_query_address(raw_text: str) -> str | None:
    parsed = urlparse(raw_text)
    query = parse_qs(parsed.query)

    for key in ("q", "address", "daddr"):
        for value in query.get(key, []):
            value = value.strip()
            if not value:
                continue

            latitude, longitude = extract_coordinates(value)
            if latitude is None and longitude is None:
                return value

    path_parts = [part for part in parsed.path.split("/") if part]
    try:
        place_index = path_parts.index("place")
    except ValueError:
        place_index = -1

    if place_index >= 0 and place_index + 1 < len(path_parts):
        value = " ".join(
            unquote_plus(path_parts[place_index + 1]).strip().split()
        )
        if value and value.casefold() != "data":
            latitude, longitude = extract_coordinates(value)
            if latitude is None and longitude is None:
                return value

    return None


def normalize_text_location(raw_text: str) -> dict[str, str | float | None]:
    clean = raw_text.strip()
    original_google_maps_url = extract_maps_url(clean)
    normalized_address = strip_maps_url(clean)
    postal_code = extract_postal_code(clean)

    latitude, longitude = extract_coordinates(clean)

    if latitude is not None and longitude is not None:
        map_url = build_google_maps_coordinate_url(latitude, longitude)
    elif original_google_maps_url is not None:
        map_url = original_google_maps_url
        query_address = extract_link_query_address(clean)
        if query_address:
            normalized_address = query_address
            postal_code = extract_postal_code(query_address)
    else:
        map_url = build_google_maps_search_url(normalized_address or clean)

    return {
        "raw_text": clean,
        "original_google_maps_url": original_google_maps_url,
        "normalized_address": normalized_address or clean,
        "postal_code": postal_code,
        "latitude": latitude,
        "longitude": longitude,
        "map_url": map_url,
    }


async def resolve_google_maps_url(url: str) -> str:
    if not is_trusted_maps_url(url):
        return url

    original_url = url
    current_url = url

    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=httpx.Timeout(5.0),
            headers={"User-Agent": "Mozilla/5.0 CargoPT location resolver"},
        ) as client:
            for _ in range(MAPS_MAX_REDIRECTS + 1):
                if (
                    not is_trusted_maps_url(current_url)
                    or not await _maps_url_resolves_to_public_ips(current_url)
                ):
                    return original_url

                response = await client.get(current_url)
                if response.status_code not in MAPS_REDIRECT_STATUS_CODES:
                    response_url = str(response.url)
                    return (
                        response_url
                        if is_trusted_maps_url(response_url)
                        else original_url
                    )

                location = response.headers.get("location")
                if not location:
                    return original_url
                current_url = urljoin(current_url, location)

            return original_url
    except (httpx.HTTPError, ValueError):
        return original_url


def build_geocoding_queries(address: str) -> list[str]:
    clean = address.strip()
    if not clean:
        return []

    queries = [clean]
    postal_code = extract_postal_code(clean)

    if postal_code is not None:
        queries.append(postal_code + " Portugal")

        after_postal_code = clean.split(postal_code, 1)[-1].strip(" ,")
        if after_postal_code:
            queries.append(postal_code + " " + after_postal_code + ", Portugal")

    deduped = []
    for query in queries:
        if query not in deduped:
            deduped.append(query)

    return deduped


async def geocode_text_address(address: str) -> tuple[float | None, float | None]:
    queries = build_geocoding_queries(address)
    if not queries:
        return None, None

    try:
        for query in queries:
            data = await _nominatim_search(
                provider_url=_configured_nominatim_provider_url(),
                params={
                    "q": query,
                    "format": "jsonv2",
                    "limit": "1",
                    "countrycodes": "pt",
                },
            )

            if not data:
                continue

            try:
                return _valid_coordinates(
                    float(data[0]["lat"]),
                    float(data[0]["lon"]),
                )
            except (KeyError, TypeError, ValueError):
                continue

    except (httpx.HTTPError, ValueError):
        return None, None

    return None, None


async def search_location_suggestions(
    query: str,
    *,
    locale: str = "pt",
    limit: int = 5,
    provider_url: str = NOMINATIM_SEARCH_URL,
) -> list[LocationSuggestion]:
    clean = " ".join(query.strip().split())
    if len(clean) < 3:
        return []

    safe_limit = min(max(limit, 1), 5)
    language = LOCATION_SEARCH_LANGUAGES.get(locale, LOCATION_SEARCH_LANGUAGES["pt"])

    try:
        queries = [clean]
        # Users often append an apartment after the street number, for example
        # "Warszawa, Leszno 32, 89". Nominatim searches the building address;
        # the apartment/access data is stored separately with the request.
        unit_pattern = (
            r"(?<=\d),\s*((?:(?:apt|apto|apartamento|lok|кв)\.?\s*)?"
            r"[\w/-]{1,20})$"
        )
        unit_match = re.search(unit_pattern, clean, flags=re.IGNORECASE)
        address_details_hint = unit_match.group(1).strip() if unit_match else None
        without_unit = re.sub(
            unit_pattern,
            "",
            clean,
            flags=re.IGNORECASE,
        ).strip()
        if without_unit and without_unit != clean:
            queries.append(without_unit)

        data = []
        for search_query in queries:
            data = await _nominatim_search(
                provider_url=provider_url,
                params={
                    "q": search_query,
                    "format": "jsonv2",
                    "limit": str(safe_limit),
                    "addressdetails": "1",
                    "accept-language": language,
                },
            )
            if data:
                break
    except (httpx.HTTPError, ValueError):
        return []

    suggestions = []
    seen = set()

    for item in data if isinstance(data, list) else []:
        try:
            display_name = " ".join(str(item["display_name"]).strip().split())
            latitude = float(item["lat"])
            longitude = float(item["lon"])
            address_details = item.get("address") or {}
            country_code = str(address_details.get("country_code") or "").lower()
            postal_code = address_details.get("postcode")
        except (KeyError, TypeError, ValueError):
            continue

        valid_latitude, valid_longitude = _valid_coordinates(latitude, longitude)
        if (
            valid_latitude is None
            or valid_longitude is None
            or not display_name
            or len(country_code) != 2
        ):
            continue

        key = (display_name.casefold(), round(latitude, 6), round(longitude, 6))
        if key in seen:
            continue
        seen.add(key)

        suggestions.append(
            LocationSuggestion(
                display_name=display_name,
                latitude=latitude,
                longitude=longitude,
                map_url=build_google_maps_coordinate_url(latitude, longitude),
                country_code=country_code,
                postal_code=str(postal_code) if postal_code else None,
                address_details_hint=address_details_hint,
            )
        )

    return suggestions


async def geocode_normalized_location(
    normalized: dict[str, str | float | None],
) -> dict[str, str | float | None]:
    if normalized["latitude"] is not None and normalized["longitude"] is not None:
        return normalized

    address = normalized["normalized_address"]
    if not isinstance(address, str) or not address.strip():
        return normalized

    if address == normalized["original_google_maps_url"]:
        return normalized

    latitude, longitude = await geocode_text_address(address)
    if latitude is None or longitude is None:
        return normalized

    normalized["latitude"] = latitude
    normalized["longitude"] = longitude
    normalized["map_url"] = build_google_maps_coordinate_url(latitude, longitude)
    return normalized


async def normalize_text_location_resolved(raw_text: str) -> dict[str, str | float | None]:
    normalized = normalize_text_location(raw_text)
    original_google_maps_url = normalized["original_google_maps_url"]

    if (
        original_google_maps_url is None
        or normalized["latitude"] is not None
        or normalized["longitude"] is not None
    ):
        return await geocode_normalized_location(normalized)

    resolved_url = await resolve_google_maps_url(str(original_google_maps_url))
    latitude, longitude = extract_coordinates(resolved_url)
    if latitude is not None and longitude is not None:
        normalized["latitude"] = latitude
        normalized["longitude"] = longitude
        normalized["map_url"] = build_google_maps_coordinate_url(latitude, longitude)

        if normalized["normalized_address"] == original_google_maps_url:
            normalized["normalized_address"] = resolved_url

        return normalized

    continue_url = extract_google_continue_url(resolved_url)
    query_address = None
    if continue_url is not None:
        query_address = extract_google_maps_query_address(continue_url)

    if query_address is None:
        query_address = extract_link_query_address(resolved_url)

    if query_address:
        normalized["normalized_address"] = query_address
        normalized["postal_code"] = extract_postal_code(query_address)
        normalized["map_url"] = build_google_maps_search_url(query_address)

    return await geocode_normalized_location(normalized)


async def reverse_geocode_portugal_district(latitude: float, longitude: float) -> str | None:
    """Resolve a mainland district without treating neighbouring Spain as Portugal."""
    if _valid_coordinates(latitude, longitude) == (None, None):
        return None
    provider_url = _configured_nominatim_provider_url().rsplit("/", 1)[0] + "/reverse"
    try:
        data = await _nominatim_search(
            provider_url=provider_url,
            params={
                "lat": str(latitude), "lon": str(longitude),
                "format": "jsonv2", "zoom": "10", "addressdetails": "1",
            },
            wrap_object=True,
        )
        address = data[0].get("address", {}) if data else {}
        if not isinstance(address, dict) or address.get("country_code") != "pt":
            return None
        district = address.get("ISO3166-2-lvl6")
        return district if isinstance(district, str) else None
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        return None
