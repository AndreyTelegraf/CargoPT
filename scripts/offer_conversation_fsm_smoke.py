import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

import app.bot.handlers.job_offer_response as handler
from app.bot.states.offer_response import OfferResponseStates


class FakeState:
    def __init__(self, data: dict, state: str):
        self.data = dict(data)
        self.state = state

    async def get_data(self) -> dict:
        return dict(self.data)

    async def update_data(self, **kwargs) -> None:
        self.data.update(kwargs)

    async def set_state(self, state) -> None:
        self.state = state.state

    async def get_state(self) -> str:
        return self.state

    async def clear(self) -> None:
        self.data.clear()
        self.state = None


class FakeMessage:
    def __init__(self, text: str | None, *, user_id: int = 77, locale: str = "ru"):
        self.text = text
        self.from_user = SimpleNamespace(id=user_id, language_code=locale)
        self.bot = SimpleNamespace(edit_message_reply_markup=AsyncMock())
        self.chat = SimpleNamespace(id=user_id)
        self.message_id = 100
        self.answers = []
        self.edit_reply_markup = AsyncMock()

    async def answer(self, text: str, **kwargs):
        sent = SimpleNamespace(
            chat=self.chat,
            message_id=101 + len(self.answers),
            text=text,
            reply_markup=kwargs.get("reply_markup"),
        )
        self.answers.append(sent)
        return sent


class FakeCallback:
    def __init__(self, data: str, message: FakeMessage):
        self.data = data
        self.message = message
        self.from_user = SimpleNamespace(id=77, language_code="ru")
        self.answers = []

    async def answer(self, text=None, **kwargs):
        self.answers.append((text, kwargs))


async def verify_conversation() -> None:
    state = FakeState(
        {
            "offer_price_offer_id": 42,
            "offer_price_message_chat_id": 77,
            "offer_price_message_id": 9,
            "offer_price_locale": "ru",
        },
        OfferResponseStates.price.state,
    )

    price_message = FakeMessage("120,50 €")
    await handler.handle_offer_price_input(price_message, state)
    assert state.state == OfferResponseStates.included_services.state
    assert state.data["offer_price_cents"] == 12050
    assert "Что входит в цену?" in price_message.answers[-1].text

    included_prompt = FakeMessage(None)
    included_callback = FakeCallback(
        "offer_terms:included:42:requested",
        included_prompt,
    )
    await handler.handle_offer_terms_shortcut(included_callback, state)
    assert state.state == OfferResponseStates.possible_surcharges.state
    assert state.data["offer_included_services"] == "Услуги по условиям заявки"

    surcharges_message = FakeMessage("Парковка при необходимости")
    await handler.handle_offer_possible_surcharges_input(surcharges_message, state)
    assert state.state == OfferResponseStates.service_window.state
    assert state.data["offer_possible_surcharges"] == "Парковка при необходимости"

    window_prompt = FakeMessage(None)
    window_callback = FakeCallback(
        "offer_terms:window:42:requested",
        window_prompt,
    )
    await handler.handle_offer_terms_shortcut(window_callback, state)
    assert state.state == OfferResponseStates.estimate_status.state
    assert state.data["offer_service_window"] == "Как указано в заявке"

    original_submit = handler._submit_offer_response
    handler._submit_offer_response = AsyncMock(return_value=True)
    try:
        status_prompt = FakeMessage(None)
        status_callback = FakeCallback(
            "offer_terms:status:42:final",
            status_prompt,
        )
        await handler.handle_offer_terms_shortcut(status_callback, state)
        handler._submit_offer_response.assert_awaited_once()
        submitted = handler._submit_offer_response.await_args.kwargs
        assert submitted["telegram_user_id"] == 77
        assert submitted["parsed_offer"].price_cents == 12050
        assert submitted["parsed_offer"].estimate_status == "final"
        assert submitted["parsed_offer"].carrier_note is None
    finally:
        handler._submit_offer_response = original_submit


async def verify_legacy_message_still_works() -> None:
    state = FakeState(
        {
            "offer_price_offer_id": 43,
            "offer_price_message_chat_id": 77,
            "offer_price_message_id": 10,
            "offer_price_locale": "en",
        },
        OfferResponseStates.price.state,
    )
    message = FakeMessage(
        "120\nLoading and unloading\nNone\nTomorrow 14:00-16:00\nfinal",
        locale="en",
    )

    original_submit = handler._submit_offer_response
    handler._submit_offer_response = AsyncMock(return_value=True)
    try:
        await handler.handle_offer_price_input(message, state)
        handler._submit_offer_response.assert_awaited_once()
        parsed = handler._submit_offer_response.await_args.kwargs["parsed_offer"]
        assert parsed.price_cents == 12000
        assert parsed.included_services == "Loading and unloading"
        assert parsed.estimate_status == "final"
    finally:
        handler._submit_offer_response = original_submit


async def verify_status_message_with_comment() -> None:
    state = FakeState(
        {
            "offer_price_offer_id": 44,
            "offer_price_message_chat_id": 77,
            "offer_price_message_id": 11,
            "offer_price_locale": "ru",
            "offer_price_cents": 9900,
            "offer_included_services": "Услуги по условиям заявки",
            "offer_possible_surcharges": "нет",
            "offer_service_window": "Как указано в заявке",
        },
        OfferResponseStates.estimate_status.state,
    )
    message = FakeMessage("окончательная — позвонить за час")

    original_submit = handler._submit_offer_response
    handler._submit_offer_response = AsyncMock(return_value=True)
    try:
        await handler.handle_offer_estimate_status_input(message, state)
        submitted = handler._submit_offer_response.await_args.kwargs
        assert submitted["parsed_offer"].estimate_status == "final"
        assert submitted["parsed_offer"].carrier_note == "позвонить за час"
    finally:
        handler._submit_offer_response = original_submit


asyncio.run(verify_conversation())
asyncio.run(verify_legacy_message_still_works())
asyncio.run(verify_status_message_with_comment())
print("OFFER_CONVERSATION_FSM_SMOKE_OK")
