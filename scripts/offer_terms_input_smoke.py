import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.bot.handlers.job_offer_response import _parse_offer_price_input
from app.bot.handlers.job_offer_response import _parse_offer_price_only
from app.bot.handlers.job_offer_response import _parse_estimate_status_input
from app.bot.handlers.job_offer_response import _build_conversational_offer
from app.bot.offer_keyboard import build_offer_estimate_status_keyboard
from app.bot.offer_keyboard import build_offer_included_services_keyboard
from app.bot.offer_keyboard import build_offer_service_window_keyboard
from app.bot.offer_keyboard import build_offer_surcharges_keyboard
from app.bot.offer_locale import offer_text
from app.repositories.job import JobRepository


def verify_parser() -> None:
    parsed = _parse_offer_price_input(
        "120,50\nLoading and unloading\nTolls if applicable\n"
        "12 Sep, 14:00-16:00\nfinal\nCall before arrival"
    )
    assert parsed.price_cents == 12050
    assert parsed.included_services == "Loading and unloading"
    assert parsed.possible_surcharges == "Tolls if applicable"
    assert parsed.service_window == "12 Sep, 14:00-16:00"
    assert parsed.estimate_status == "final"
    assert parsed.carrier_note == "Call before arrival"

    assert _parse_offer_price_input(
        "90\nCarga e descarga\nnenhum\n13/09 manhã\nestimativa"
    ).estimate_status == "estimate"
    assert _parse_offer_price_input(
        "75\nПогрузка\nнет\n14.09 вечером\nпредварительная"
    ).estimate_status == "estimate"

    for invalid in (
        "120",
        "120\nIncluded\nNone\nTomorrow",
        "120\nIncluded\nNone\nTomorrow\nunknown",
        "0\nIncluded\nNone\nTomorrow\nfinal",
    ):
        try:
            _parse_offer_price_input(invalid)
        except ValueError:
            continue
        raise AssertionError(f"invalid offer input accepted: {invalid!r}")


def verify_conversational_input() -> None:
    assert _parse_offer_price_only("120") == 12000
    assert _parse_offer_price_only("120,50 €") == 12050
    assert _parse_offer_price_only("€ 99.90") == 9990
    assert _parse_offer_price_only("75 euros") == 7500
    assert _parse_offer_price_only("80 евро") == 8000

    for invalid in ("", "0", "price 120", "120.999", "-10"):
        try:
            _parse_offer_price_only(invalid)
        except ValueError:
            continue
        raise AssertionError(f"invalid price-only input accepted: {invalid!r}")

    parsed = _build_conversational_offer(
        {
            "offer_price_cents": 12050,
            "offer_included_services": "Loading and unloading",
            "offer_possible_surcharges": "none",
            "offer_service_window": "As stated in the request",
        },
        estimate_status="final",
    )
    assert parsed.price_cents == 12050
    assert parsed.included_services == "Loading and unloading"
    assert parsed.possible_surcharges == "none"
    assert parsed.service_window == "As stated in the request"
    assert parsed.estimate_status == "final"
    assert parsed.carrier_note is None

    assert _parse_estimate_status_input("final") == ("final", None)
    assert _parse_estimate_status_input(
        "окончательная — позвонить за час"
    ) == ("final", "позвонить за час")
    assert _parse_estimate_status_input(
        "estimativa: confirmar estacionamento"
    ) == ("estimate", "confirmar estacionamento")
    try:
        _parse_estimate_status_input("finally")
    except ValueError:
        pass
    else:
        raise AssertionError("status prefix without a separator was accepted")


def verify_conversational_ui() -> None:
    assert (
        build_offer_included_services_keyboard(17, "ru")
        .inline_keyboard[0][0]
        .callback_data
        == "offer_terms:included:17:requested"
    )
    assert (
        build_offer_surcharges_keyboard(17, "pt")
        .inline_keyboard[0][0]
        .callback_data
        == "offer_terms:surcharges:17:none"
    )
    assert (
        build_offer_service_window_keyboard(17, "en")
        .inline_keyboard[0][0]
        .callback_data
        == "offer_terms:window:17:requested"
    )
    status_keyboard = build_offer_estimate_status_keyboard(17, "ru")
    assert [row[0].callback_data for row in status_keyboard.inline_keyboard] == [
        "offer_terms:status:17:final",
        "offer_terms:status:17:estimate",
    ]

    for locale, forbidden in (
        ("pt", "5 linhas"),
        ("en", "5 lines"),
        ("ru", "5 строк"),
    ):
        prompt = offer_text(locale, "price_prompt")
        assert forbidden not in prompt
        assert "\n1." not in prompt
        assert offer_text(locale, "included_services_prompt")
        assert offer_text(locale, "possible_surcharges_prompt")
        assert offer_text(locale, "service_window_prompt")
        assert offer_text(locale, "estimate_status_prompt")


async def verify_repository_storage() -> None:
    offer = SimpleNamespace()
    session = SimpleNamespace(flush=AsyncMock())
    repository = JobRepository(session)
    repository.get_offer_by_id = AsyncMock(return_value=offer)
    now = datetime.now(UTC)

    result = await repository.update_offer_terms(
        offer_id=7,
        price_cents=12050,
        included_services="Loading and unloading",
        possible_surcharges="Tolls if applicable",
        service_window="12 Sep, 14:00-16:00",
        estimate_status="final",
        carrier_note="Call before arrival",
        updated_at=now,
    )

    assert result is offer
    assert offer.price_cents == 12050
    assert offer.included_services == "Loading and unloading"
    assert offer.possible_surcharges == "Tolls if applicable"
    assert offer.service_window == "12 Sep, 14:00-16:00"
    assert offer.estimate_status == "final"
    assert offer.carrier_note == "Call before arrival"
    assert offer.updated_at == now
    session.flush.assert_awaited_once()


verify_parser()
verify_conversational_input()
verify_conversational_ui()
asyncio.run(verify_repository_storage())
print("OFFER_TERMS_INPUT_SMOKE_OK")
