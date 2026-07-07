import os
import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.services.offer_notification import build_offer_text
from app.bot.offer_keyboard import build_offer_keyboard

job = SimpleNamespace(
    id=7,
    requested_date=None,
    estimated_payload_kg=500,
    estimated_volume_m3=10.0,
    required_loaders=1,
    needs_tail_lift=False,
    needs_crane=False,
    needs_mobile_lift=False,
    needs_assembly=True,
    needs_packing=True,
    comment=None,
    client_telegram_username="AndreyTelegraf",
    client_phone=None,
    client_whatsapp=None,
)
item = SimpleNamespace(description="Диван и 10 коробок")
pickup = SimpleNamespace(raw_text="Rua Augusta 1, Lisboa", map_url="https://maps.app.goo.gl/pickup", floor=2, has_elevator=True)
dropoff = SimpleNamespace(raw_text="Cascais", map_url="https://maps.app.goo.gl/dropoff", floor=0, has_elevator=False)

text = build_offer_text(job, [item], pickup, dropoff)
assert "\\n" not in text
assert "<b>Новая заявка #7</b>" in text
assert "<b>Откуда</b>\nRua Augusta 1, Lisboa" in text
assert "Карта: https://maps.app.goo.gl/pickup" in text
assert "<b>Груз</b>\nДиван и 10 коробок" in text
assert "Telegram: @AndreyTelegraf" not in text
assert "Грузчики: 1" in text
assert "Вес:" not in text
assert "Объём:" not in text
assert "Гидроборт:" not in text

keyboard = build_offer_keyboard(123)
buttons = keyboard.inline_keyboard[0]
assert buttons[0].text == "✅ Принять"
assert buttons[1].text == "❌ Отклонить"

print("JOB_OFFER_UX_SMOKE_OK")
