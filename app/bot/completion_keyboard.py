from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup


def build_completion_keyboard(job_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Перевозка завершена",
                    callback_data=f"completion:confirm:{job_id}",
                ),
                InlineKeyboardButton(
                    text="Возникла проблема",
                    callback_data=f"completion:problem:{job_id}",
                ),
            ]
        ]
    )
