from datetime import UTC
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.config import settings
from app.db.base import Base
from app.models.carrier import CarrierCompany
from app.models.carrier_urgent_survey import CarrierUrgentSurvey
from app.models.carrier_urgent_survey import CarrierUrgentSurveyReportEvent
from app.services.carrier_urgent_survey import RESPONSE_CODES
from app.services.carrier_urgent_survey import build_urgent_survey_keyboard
from app.services.carrier_urgent_survey import parse_urgent_survey_callback
from app.services.carrier_urgent_survey import saved_text
from app.services.carrier_urgent_survey import survey_text
from app.services.carrier_urgent_survey import build_urgent_survey_report_text


def main() -> None:
    assert settings.carrier_urgent_survey_report_chat_id == 661667
    now = datetime.now(UTC)
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        carrier = CarrierCompany(
            company_name="Smoke Carrier",
            telegram_user_id=123456,
            telegram_username="smoke_carrier",
            preferred_locale="en",
            status="active",
            paid_until=now,
            assembly_required=False,
            packing_required=False,
            created_at=now,
            updated_at=now,
        )
        session.add(carrier)
        session.flush()
        survey = CarrierUrgentSurvey(
            campaign_key="smoke",
            carrier_id=carrier.id,
            recipient_chat_id=carrier.telegram_user_id,
            locale="en",
            delivery_status="sent",
            created_at=now,
            updated_at=now,
        )
        session.add(survey)
        session.commit()
        session.refresh(survey)

        report_event = CarrierUrgentSurveyReportEvent(
            survey_id=survey.id,
            carrier_id=carrier.id,
            carrier_label=carrier.company_name,
            carrier_telegram_username=carrier.telegram_username,
            locale=survey.locale,
            previous_response_code=None,
            response_code="same_day",
            report_chat_id=661667,
            delivery_status="pending",
            provider_message_id=None,
            last_error=None,
            sent_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(report_event)
        session.commit()

        for locale in ("pt", "en", "ru"):
            assert survey_text(locale)
            for code in RESPONSE_CODES:
                assert saved_text(locale, code)
            keyboard = build_urgent_survey_keyboard(
                survey_id=survey.id,
                locale=locale,
                selected_response="same_day",
            )
            callbacks = [row[0].callback_data for row in keyboard.inline_keyboard]
            assert len(callbacks) == len(RESPONSE_CODES)
            assert all(len(value) <= 64 for value in callbacks)
            assert [parse_urgent_survey_callback(value) for value in callbacks] == [
                (survey.id, code) for code in RESPONSE_CODES
            ]

        first_report = build_urgent_survey_report_text(
            carrier_id=carrier.id,
            carrier_label=carrier.company_name,
            carrier_telegram_username=carrier.telegram_username,
            locale="en",
            response_code="same_day",
            previous_response_code=None,
        )
        assert "Новый ответ" in first_report
        assert "@smoke_carrier" in first_report
        changed_report = build_urgent_survey_report_text(
            carrier_id=carrier.id,
            carrier_label=carrier.company_name,
            carrier_telegram_username=carrier.telegram_username,
            locale="en",
            response_code="next_day",
            previous_response_code="same_day",
        )
        assert "Ответ изменён" in changed_report
        assert "→" in changed_report

    print("CARRIER_URGENT_SURVEY_SMOKE_OK")


if __name__ == "__main__":
    main()
