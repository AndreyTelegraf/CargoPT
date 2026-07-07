from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup

from app.domain.job_decline_reason import DECLINE_REASONS


def build_assignment_confirmation_keyboard(job_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Сделка подтверждена",
                    callback_data=f"assignment:confirm:{job_id}",
                ),
                InlineKeyboardButton(
                    text="Не договорились",
                    callback_data=f"assignment:fail:{job_id}",
                ),
            ]
        ]
    )


def build_assignment_failure_reason_keyboard(job_id: int) -> InlineKeyboardMarkup:
    rows = []

    for index in range(0, len(DECLINE_REASONS), 2):
        rows.append(
            [
                InlineKeyboardButton(
                    text=reason.label,
                    callback_data=f"assignment:fail_reason:{job_id}:{reason.code}",
                )
                for reason in DECLINE_REASONS[index:index + 2]
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_client_reopen_assignment_keyboard(job_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Не договорились с перевозчиком",
                    callback_data=f"assignment:fail_reason:{job_id}:unspecified",
                ),
            ],
        ]
    )
