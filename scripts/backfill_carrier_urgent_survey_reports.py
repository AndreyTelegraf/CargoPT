from __future__ import annotations

import argparse
import asyncio
from datetime import UTC
from datetime import datetime

from aiogram import Bot
from sqlalchemy import exists
from sqlalchemy import select

from app.config import settings
from app.db.session import async_session_maker
from app.models.carrier import CarrierCompany
from app.models.carrier_urgent_survey import CarrierUrgentSurvey
from app.models.carrier_urgent_survey import CarrierUrgentSurveyReportEvent
from app.services.carrier_urgent_survey import CAMPAIGN_KEY
from app.services.carrier_urgent_survey_reporting import (
    deliver_urgent_survey_report_event,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--campaign-key", default=CAMPAIGN_KEY)
    return parser.parse_args()


async def create_missing_events(campaign_key: str) -> list[int]:
    async with async_session_maker() as session:
        already_reported = exists().where(
            CarrierUrgentSurveyReportEvent.survey_id == CarrierUrgentSurvey.id
        )
        rows = await session.execute(
            select(CarrierUrgentSurvey, CarrierCompany)
            .join(CarrierCompany, CarrierCompany.id == CarrierUrgentSurvey.carrier_id)
            .where(CarrierUrgentSurvey.campaign_key == campaign_key)
            .where(CarrierUrgentSurvey.response_code.is_not(None))
            .where(~already_reported)
            .order_by(CarrierUrgentSurvey.id)
        )
        now = datetime.now(UTC)
        events = []
        for survey, carrier in rows.all():
            event = CarrierUrgentSurveyReportEvent(
                survey_id=survey.id,
                carrier_id=carrier.id,
                carrier_label=carrier.public_name or carrier.company_name,
                carrier_telegram_username=carrier.telegram_username,
                locale=survey.locale,
                previous_response_code=None,
                response_code=survey.response_code,
                report_chat_id=settings.carrier_urgent_survey_report_chat_id,
                delivery_status="pending",
                provider_message_id=None,
                last_error=None,
                sent_at=None,
                created_at=now,
                updated_at=now,
            )
            session.add(event)
            events.append(event)
        await session.flush()
        event_ids = [event.id for event in events]
        await session.commit()
        return event_ids


async def list_missing_survey_ids(campaign_key: str) -> list[int]:
    async with async_session_maker() as session:
        already_reported = exists().where(
            CarrierUrgentSurveyReportEvent.survey_id == CarrierUrgentSurvey.id
        )
        rows = await session.scalars(
            select(CarrierUrgentSurvey.id)
            .where(CarrierUrgentSurvey.campaign_key == campaign_key)
            .where(CarrierUrgentSurvey.response_code.is_not(None))
            .where(~already_reported)
            .order_by(CarrierUrgentSurvey.id)
        )
        return list(rows.all())


async def main() -> None:
    args = parse_args()
    missing_survey_ids = await list_missing_survey_ids(args.campaign_key)
    print(f"MISSING_REPORT_COUNT={len(missing_survey_ids)}")
    print(
        "MISSING_SURVEY_IDS="
        + ",".join(str(survey_id) for survey_id in missing_survey_ids)
    )
    if not args.send:
        print("DRY_RUN_OK")
        return

    event_ids = await create_missing_events(args.campaign_key)
    print(f"CREATED_EVENT_COUNT={len(event_ids)}")
    print("EVENT_IDS=" + ",".join(str(event_id) for event_id in event_ids))
    results: dict[str, int] = {}
    async with Bot(settings.bot_token) as bot:
        for event_id in event_ids:
            result = await deliver_urgent_survey_report_event(bot, event_id)
            results[result] = results.get(result, 0) + 1
            print(f"event_id={event_id} result={result}")
    print(
        "SEND_RESULT="
        + ",".join(f"{key}:{value}" for key, value in sorted(results.items()))
    )
    if results.get("failed", 0):
        raise SystemExit(1)
    print("CARRIER_URGENT_SURVEY_REPORT_BACKFILL_OK")


if __name__ == "__main__":
    asyncio.run(main())
