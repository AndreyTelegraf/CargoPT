from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup

from app.domain.job_decline_reason import DECLINE_REASONS


def build_offer_keyboard(offer_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Принять",
                    callback_data=f"offer:accept:{offer_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"offer:decline:{offer_id}",
                ),
            ]
        ]
    )

from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup


def build_client_offer_selection_keyboard(offers) -> InlineKeyboardMarkup:
    rows = []

    for index, offer in enumerate(offers, start=1):
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"Выбрать предложение {index}",
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


def build_offer_decline_reason_keyboard(offer_id: int) -> InlineKeyboardMarkup:
    rows = []

    for index in range(0, len(DECLINE_REASONS), 2):
        rows.append(
            [
                InlineKeyboardButton(
                    text=reason.label,
                    callback_data=f"offer_decline_reason:{offer_id}:{reason.code}",
                )
                for reason in DECLINE_REASONS[index:index + 2]
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows)
