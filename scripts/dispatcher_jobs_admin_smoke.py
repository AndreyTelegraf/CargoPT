import os
import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.bot.handlers.dispatcher_jobs_admin import _format_job_line
from app.bot.handlers.dispatcher_jobs_admin import _format_status
from app.bot.handlers.dispatcher_jobs_admin import _parse_jobs_report_period
from app.bot.handlers.dispatcher_jobs_admin import dispatcher_jobs
from app.bot.handlers.dispatcher_jobs_admin import dispatcher_jobs_attention
from app.bot.handlers.dispatcher_jobs_admin import dispatcher_jobs_report
from app.bot.handlers.dispatcher_jobs_admin import dispatcher_job_detail
from app.bot.handlers.dispatcher_jobs_admin import _build_job_card_text
from app.bot.handlers.dispatcher_jobs_admin import _parse_job_command_id
from app.bot.handlers.dispatcher_jobs_admin import _job_admin_keyboard
from app.bot.handlers.dispatcher_jobs_admin import _build_manual_dispatch_keyboard
from app.bot.handlers.dispatcher_jobs_admin import dispatcher_job_admin_action
from app.bot.handlers.dispatcher_jobs_admin import router
from app.repositories.job import JobRepository

assert router is not None
assert dispatcher_jobs is not None
assert dispatcher_jobs_attention is not None
assert dispatcher_jobs_report is not None
assert dispatcher_job_detail is not None
assert dispatcher_job_admin_action is not None
assert _build_manual_dispatch_keyboard is not None
assert _parse_job_command_id('/job 26') == 26
assert _parse_job_command_id('/job_26') == 26
assert _parse_job_command_id('/job abc') is None
assert _parse_job_command_id('/jobs') is None
keyboard = _job_admin_keyboard(26)
callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]
assert callbacks == ['job:26:retry', 'job:26:manual', 'job:26:close']
assert _parse_jobs_report_period("/jobs_report") == ("2026-06-25 00:00:00", None)
assert _parse_jobs_report_period("/jobs_report 2026-06-27") == ("2026-06-27 00:00:00", None)
assert _parse_jobs_report_period("/jobs_report 2026-06-25 2026-06-28") == ("2026-06-25 00:00:00", "2026-06-28 23:59:59")
assert _parse_jobs_report_period("/jobs_report 2026-06-25 12:00 2026-06-27 18:30") == ("2026-06-25 12:00:00", "2026-06-27 18:30:00")
assert hasattr(JobRepository, "list_recent_jobs")
assert hasattr(JobRepository, "list_attention_jobs")

job = SimpleNamespace(
    id=42,
    status="assigned",
    client_telegram_username="client_user",
    client_telegram_user_id=987654321,
    customer_name="Client Name",
    client_phone="+351900000000",
    client_whatsapp="+351900000001",
    customer_email="client@example.test",
    preferred_contact="whatsapp",
    requested_date=None,
    assigned_at=None,
    started_at=None,
    completed_at=None,
    cancelled_at=None,
    created_at=None,
    updated_at=None,
    required_loaders=2,
    estimated_payload_kg=100,
    estimated_volume_m3=3.5,
    needs_assembly=False,
    needs_packing=True,
    needs_tail_lift=False,
    needs_crane=False,
    needs_mobile_lift=False,
    comment="Test comment",
    source="telegram",
    source_locale="ru",
    utm_source=None,
    utm_campaign=None,
    landing_version=None,
    attention_reason="price_not_agreed",
    offers_count=17,
)

line = _format_job_line(job)
assert _format_status("offered") == "отправлена перевозчикам"
assert _format_status("unmatched") == "перевозчик не найден"
assert _format_status("no_carriers_found") == "нет подходящих перевозчиков"
assert _format_status("offers_exhausted") == "все перевозчики отказались"
assert _format_status("expired_without_response") == "нет ответов от перевозчиков"
assert _format_status("manual_review_required") == "требует ручного контроля"
assert _format_status("assigned_pending_confirmation") == "ожидает подтверждения сделки"
assert _format_status("assigned") == "перевозчик назначен"
assert _format_status("unknown_status") == "unknown_status"
assert "<b>#42</b> — перевозчик назначен — @client_user" in line
assert "Дата: —" in line
assert "Назначена: —" in line
assert "Офферов: 17" in line
assert "Причина: Не договорились по цене" in line


address = SimpleNamespace(
    kind="pickup",
    raw_text="Lisboa",
    normalized_address="Lisboa, Portugal",
    city="Lisboa",
    postal_code=None,
    floor=3,
    has_elevator=True,
    map_url=None,
)
item = SimpleNamespace(
    description="Sofa and boxes",
    quantity=2,
    estimated_weight_kg=50,
    estimated_volume_m3=3.5,
)
offer = SimpleNamespace(
    status="declined",
    decline_reason="price_not_agreed",
)
card = _build_job_card_text(
    job=job,
    addresses=[address],
    items=[item],
    offers=[offer],
)
assert "<b>Заявка #42</b>" in card
assert "перевозчик назначен (assigned)" in card
assert "Telegram: @client_user" in card
assert "<b>Адреса</b>" in card
assert "pickup" in card
assert "Lisboa" in card
assert "<b>Груз</b>" in card
assert "Sofa and boxes" in card
assert "declined — 1" in card
assert "Последняя причина отказа: Не договорились по цене" in card

router_source = Path("app/bot/routers.py").read_text(encoding="utf-8")
assert "dispatcher_jobs_admin_router" in router_source

handler_source = Path("app/bot/handlers/dispatcher_jobs_admin.py").read_text(encoding="utf-8")
assert 'Command("jobs")' in handler_source
assert 'Command("jobs_attention")' in handler_source
assert "ADMIN_TELEGRAM_USER_IDS" in handler_source
assert "list_recent_jobs(limit=20)" in handler_source
assert "list_attention_jobs(limit=20)" in handler_source
assert 'Command("jobs_report")' in handler_source
assert 'Command("job")' in handler_source
assert 'dispatcher_job_detail' in handler_source
assert '_build_job_card_text' in handler_source
assert '_job_admin_keyboard' in handler_source
assert 'dispatcher_job_admin_action' in handler_source
assert 'callback_data=f"job:{job_id}:retry"' in handler_source
assert 'callback_data=f"job:{job_id}:manual"' in handler_source
assert 'callback_data=f"job:{job_id}:close"' in handler_source
assert 'reply_markup=_job_admin_keyboard(job.id)' in handler_source
assert "CargoPT jobs report" in handler_source
assert "2026-06-25 00:00:00" in handler_source
assert "_parse_jobs_report_period" in handler_source
assert "period_filter" in handler_source
assert 'text(f"""' in handler_source
assert handler_source.count('text(f"""') >= 3
assert 'period_filter.replace("created_at", "j.created_at")' in handler_source
assert "_format_report_job_rows" in handler_source
assert "get_decline_reason_label" in handler_source
assert "OfferDistributionService" in handler_source
assert "send_job_offers_to_carriers" in handler_source
assert "offers = await distribution.create_offers_for_job" in handler_source
assert "sent_count = await send_job_offers_to_carriers" in handler_source
assert "новых перевозчиков для рассылки не найдено" in handler_source
assert "_build_manual_dispatch_keyboard" in handler_source
assert "find_matching_vehicles_for_job" in handler_source
assert "list_offer_carrier_ids_by_job" in handler_source
assert 'callback_data=f"job:{job.id}:send:{vehicle.id}"' in handler_source
assert 'callback_data=f"job:{job.id}:back"' in handler_source
assert "Выберите перевозчика для ручной отправки заявки" in handler_source
assert "подходящих новых перевозчиков не найдено" in handler_source
assert 'action not in {"retry", "manual", "close", "back", "send"}' in handler_source
assert "vehicle = await carrier_repository.get_vehicle_by_id(vehicle_id)" in handler_source
assert "JobOfferService(job_repository).create_offer" in handler_source
assert "offers=[offer]" in handler_source
assert 'status="offered"' in handler_source
assert "уже отправлялась этому перевозчику" in handler_source
assert "вручную отправлена перевозчику" in handler_source
assert 'status="cancelled"' in handler_source
assert "Заявка #{raw_job_id} закрыта." in handler_source
assert "вручную переведена в статус cancelled" in handler_source
assert "attention_reason" in handler_source
assert "offers_count" in handler_source

print("DISPATCHER_JOBS_ADMIN_SMOKE_OK")

from app.bot.handlers.dispatcher_jobs_admin import _format_report_job_rows

accepted_report_rows = [
    {
        "id": 999,
        "status": "offered",
        "client_telegram_username": "client_test",
        "client_telegram_user_id": 123,
        "offers": 3,
        "accepted": 1,
        "declined": 1,
        "expired": 1,
        "pending": 0,
        "latest_reason": None,
    }
]

accepted_report_text = _format_report_job_rows(accepted_report_rows)
assert "ожидает выбора клиента" in accepted_report_text
assert "отправлена перевозчикам" not in accepted_report_text
assert "#999" in accepted_report_text
