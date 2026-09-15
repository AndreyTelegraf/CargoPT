from __future__ import annotations

import argparse
import asyncio
from datetime import UTC
from datetime import datetime

from aiogram import Bot
from sqlalchemy import exists
from sqlalchemy import select

from app.bot.carrier_locale import normalize_carrier_locale
from app.config import settings
from app.db.session import async_session_maker
from app.models.carrier import CarrierCompany
from app.models.carrier import CarrierVehicle
from app.models.carrier_urgent_survey import CarrierUrgentSurvey
from app.services.carrier_urgent_survey import CAMPAIGN_KEY
from app.services.carrier_urgent_survey import build_urgent_survey_keyboard
from app.services.carrier_urgent_survey import survey_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--campaign-key", default=CAMPAIGN_KEY)
    return parser.parse_args()


async def list_recipients() -> list[CarrierCompany]:
    now = datetime.now(UTC)
    active_vehicle = exists().where(
        CarrierVehicle.carrier_id == CarrierCompany.id,
        CarrierVehicle.is_active.is_(True),
    )
    async with async_session_maker() as session:
        rows = await session.execute(
            select(CarrierCompany)
            .where(CarrierCompany.status == "active")
            .where(CarrierCompany.paid_until.is_not(None))
            .where(CarrierCompany.paid_until >= now)
            .where(CarrierCompany.telegram_user_id.is_not(None))
            .where(active_vehicle)
            .order_by(CarrierCompany.id)
        )
        return list(rows.scalars().all())


async def send_one(
    bot: Bot,
    *,
    carrier: CarrierCompany,
    campaign_key: str,
) -> tuple[str, str]:
    now = datetime.now(UTC)
    locale = normalize_carrier_locale(carrier.preferred_locale)
    async with async_session_maker() as session:
        existing = await session.scalar(
            select(CarrierUrgentSurvey).where(
                CarrierUrgentSurvey.campaign_key == campaign_key,
                CarrierUrgentSurvey.carrier_id == carrier.id,
            )
        )
        if existing is not None:
            return "skipped_existing", str(existing.id)

        survey = CarrierUrgentSurvey(
            campaign_key=campaign_key,
            carrier_id=carrier.id,
            recipient_chat_id=carrier.telegram_user_id,
            locale=locale,
            response_code=None,
            delivery_status="sending",
            provider_message_id=None,
            last_error=None,
            sent_at=None,
            responded_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(survey)
        await session.commit()
        await session.refresh(survey)

    try:
        message = await bot.send_message(
            chat_id=carrier.telegram_user_id,
            text=survey_text(locale),
            reply_markup=build_urgent_survey_keyboard(
                survey_id=survey.id,
                locale=locale,
            ),
        )
    except Exception as exc:
        async with async_session_maker() as session:
            stored = await session.get(CarrierUrgentSurvey, survey.id)
            stored.delivery_status = "failed"
            stored.last_error = f"{type(exc).__name__}: {exc}"[:1000]
            stored.updated_at = datetime.now(UTC)
            await session.commit()
        return "failed", str(survey.id)

    async with async_session_maker() as session:
        stored = await session.get(CarrierUrgentSurvey, survey.id)
        stored.delivery_status = "sent"
        stored.provider_message_id = message.message_id
        stored.sent_at = datetime.now(UTC)
        stored.updated_at = stored.sent_at
        await session.commit()
    return "sent", str(survey.id)


async def main() -> None:
    args = parse_args()
    recipients = await list_recipients()
    locale_counts: dict[str, int] = {}
    for carrier in recipients:
        locale = normalize_carrier_locale(carrier.preferred_locale)
        locale_counts[locale] = locale_counts.get(locale, 0) + 1

    print(f"CAMPAIGN_KEY={args.campaign_key}")
    print(f"RECIPIENT_COUNT={len(recipients)}")
    print(
        "LOCALE_COUNTS="
        + ",".join(f"{key}:{value}" for key, value in sorted(locale_counts.items()))
    )
    print("RECIPIENT_IDS=" + ",".join(str(carrier.id) for carrier in recipients))

    if not args.send:
        print("DRY_RUN_OK")
        return

    results: dict[str, int] = {}
    bot = Bot(settings.bot_token)
    try:
        for carrier in recipients:
            result, survey_id = await send_one(
                bot,
                carrier=carrier,
                campaign_key=args.campaign_key,
            )
            results[result] = results.get(result, 0) + 1
            print(
                f"carrier_id={carrier.id} locale="
                f"{normalize_carrier_locale(carrier.preferred_locale)} "
                f"result={result} survey_id={survey_id}"
            )
            await asyncio.sleep(0.2)
    finally:
        await bot.session.close()

    print(
        "SEND_RESULT="
        + ",".join(f"{key}:{value}" for key, value in sorted(results.items()))
    )
    if results.get("failed", 0):
        raise SystemExit(1)
    print("CARRIER_URGENT_SURVEY_SEND_OK")


if __name__ == "__main__":
    asyncio.run(main())
