from __future__ import annotations

from datetime import UTC
from datetime import datetime

from aiogram import Bot

from app.db.session import async_session_maker
from app.models.carrier_urgent_survey import CarrierUrgentSurveyReportEvent
from app.services.carrier_urgent_survey import build_urgent_survey_report_text


async def deliver_urgent_survey_report_event(
    bot: Bot,
    event_id: int,
) -> str:
    async with async_session_maker() as session:
        event = await session.get(CarrierUrgentSurveyReportEvent, event_id)
        if event is None:
            return "missing"
        if event.delivery_status != "pending":
            return event.delivery_status

        text = build_urgent_survey_report_text(
            carrier_id=event.carrier_id,
            carrier_label=event.carrier_label,
            carrier_telegram_username=event.carrier_telegram_username,
            locale=event.locale,
            response_code=event.response_code,
            previous_response_code=event.previous_response_code,
        )

    try:
        message = await bot.send_message(
            chat_id=event.report_chat_id,
            text=text,
        )
    except Exception as exc:
        async with async_session_maker() as session:
            stored = await session.get(CarrierUrgentSurveyReportEvent, event_id)
            if stored is not None and stored.delivery_status == "pending":
                stored.delivery_status = "failed"
                stored.last_error = f"{type(exc).__name__}: {exc}"[:1000]
                stored.updated_at = datetime.now(UTC)
                await session.commit()
        return "failed"

    async with async_session_maker() as session:
        stored = await session.get(CarrierUrgentSurveyReportEvent, event_id)
        if stored is None:
            return "missing"
        now = datetime.now(UTC)
        stored.delivery_status = "sent"
        stored.provider_message_id = message.message_id
        stored.last_error = None
        stored.sent_at = now
        stored.updated_at = now
        await session.commit()
    return "sent"
