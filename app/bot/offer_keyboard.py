from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup

from app.bot.offer_locale import decline_reason_text
from app.bot.offer_locale import offer_text as t
from app.domain.job_decline_reason import DECLINE_REASONS


def build_offer_keyboard(
    offer_id: int,
    locale: str | None = None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(locale, "accept"),
                    callback_data=f"offer:accept:{offer_id}",
                ),
                InlineKeyboardButton(
                    text=t(locale, "decline"),
                    callback_data=f"offer:decline:{offer_id}",
                ),
            ]
        ]
    )


def _build_offer_terms_shortcut_keyboard(
    *,
    offer_id: int,
    field: str,
    button_text: str,
    value: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"offer_terms:{field}:{offer_id}:{value}",
                )
            ]
        ]
    )


def build_offer_included_services_keyboard(
    offer_id: int,
    locale: str | None = None,
) -> InlineKeyboardMarkup:
    return _build_offer_terms_shortcut_keyboard(
        offer_id=offer_id,
        field="included",
        button_text=t(locale, "included_services_as_requested"),
        value="requested",
    )


def build_offer_surcharges_keyboard(
    offer_id: int,
    locale: str | None = None,
) -> InlineKeyboardMarkup:
    return _build_offer_terms_shortcut_keyboard(
        offer_id=offer_id,
        field="surcharges",
        button_text=t(locale, "possible_surcharges_none"),
        value="none",
    )


def build_offer_service_window_keyboard(
    offer_id: int,
    locale: str | None = None,
) -> InlineKeyboardMarkup:
    return _build_offer_terms_shortcut_keyboard(
        offer_id=offer_id,
        field="window",
        button_text=t(locale, "service_window_as_requested"),
        value="requested",
    )


def build_offer_estimate_status_keyboard(
    offer_id: int,
    locale: str | None = None,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(locale, "estimate_final_button"),
                    callback_data=f"offer_terms:status:{offer_id}:final",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(locale, "estimate_estimate_button"),
                    callback_data=f"offer_terms:status:{offer_id}:estimate",
                )
            ],
        ]
    )

def build_client_offer_selection_keyboard(
    offers,
    locale: str | None = None,
) -> InlineKeyboardMarkup:
    rows = []

    for index, offer in enumerate(offers, start=1):
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(locale, "select_offer", index=index),
                    callback_data=f"client_offer:select:{offer.job_id}:{offer.offer_id}",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def parse_client_offer_selection_callback(data: str) -> tuple[int, int]:
    parts = data.split(":")
    if len(parts) != 4 or parts[0] != "client_offer" or parts[1] != "select":
        raise ValueError("invalid client offer callback data")

    return int(parts[2]), int(parts[3])


def build_offer_decline_reason_keyboard(
    offer_id: int,
    locale: str | None = None,
) -> InlineKeyboardMarkup:
    rows = []

    for index in range(0, len(DECLINE_REASONS), 2):
        rows.append(
            [
                InlineKeyboardButton(
                    text=decline_reason_text(locale, reason.code),
                    callback_data=f"offer_decline_reason:{offer_id}:{reason.code}",
                )
                for reason in DECLINE_REASONS[index:index + 2]
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows)
