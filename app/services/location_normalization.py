from __future__ import annotations

import re
from urllib.parse import parse_qs
from urllib.parse import quote_plus
from urllib.parse import unquote
from urllib.parse import urlparse

import httpx


MAPS_URL_RE = re.compile(
    r"https?://(?:www\.)?(?:(?:google\.[^\s]+/maps|maps\.app\.goo\.gl|goo\.gl/maps)|(?:maps?\.apple\.com)|(?:waze\.com/ul|ul\.waze\.com/ul))[^\s]*",
    re.IGNORECASE,
)

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
    return match.group(0).rstrip(".,;)")


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
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(5.0),
            headers={"User-Agent": "Mozilla/5.0 CargoPT location resolver"},
        ) as client:
            response = await client.get(url)
            return str(response.url)
    except httpx.HTTPError:
        return url


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
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(5.0),
            headers={"User-Agent": "CargoPT/1.0 location resolver"},
        ) as client:
            for query in queries:
                response = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": query,
                        "format": "jsonv2",
                        "limit": "1",
                        "countrycodes": "pt",
                    },
                )
                response.raise_for_status()
                data = response.json()

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
