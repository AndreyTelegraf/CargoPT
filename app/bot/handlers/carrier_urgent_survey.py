from datetime import UTC
from datetime import datetime

from aiogram import F
from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from app.db.session import async_session_maker
from app.models.carrier_urgent_survey import CarrierUrgentSurvey
from app.services.carrier_urgent_survey import CALLBACK_PREFIX
from app.services.carrier_urgent_survey import build_urgent_survey_keyboard
from app.services.carrier_urgent_survey import parse_urgent_survey_callback
from app.services.carrier_urgent_survey import saved_text


router = Router()


@router.callback_query(F.data.startswith(f"{CALLBACK_PREFIX}:"))
async def handle_carrier_urgent_survey(callback: CallbackQuery) -> None:
    parsed = parse_urgent_survey_callback(callback.data)
    if parsed is None or callback.from_user is None:
        await callback.answer()
        return

    survey_id, response_code = parsed
    async with async_session_maker() as session:
        survey = await session.get(CarrierUrgentSurvey, survey_id)
        if survey is None or survey.recipient_chat_id != callback.from_user.id:
            await callback.answer()
            return

        now = datetime.now(UTC)
        survey.response_code = response_code
        survey.responded_at = now
        survey.updated_at = now
        await session.commit()
        locale = survey.locale

    if callback.message is not None:
        try:
            await callback.message.edit_reply_markup(
                reply_markup=build_urgent_survey_keyboard(
                    survey_id=survey_id,
                    locale=locale,
                    selected_response=response_code,
                )
            )
        except TelegramBadRequest:
            pass

    await callback.answer(
        saved_text(locale, response_code),
        show_alert=True,
    )
