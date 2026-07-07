import os
import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.services.offer_notifications import build_carrier_notification_text
from app.services.offer_notifications import build_client_notification_text
from app.bot.handlers.job_offer_response import router

assert router is not None

job = SimpleNamespace(
    id=42,
    client_telegram_user_id=987654321,
    client_telegram_username="client_user",
    client_phone="+351910000000",
    client_whatsapp="+351920000000",
)
carrier = SimpleNamespace(
    company_name="Carrier & Co",
    contact_name="João",
    phone="+351930000000",
    telegram_user_id=123456789,
)

client_text = build_client_notification_text(job, carrier)
carrier_text = build_carrier_notification_text(job, carrier)

assert "Перевозчик найден и принял заказ №42." in client_text
assert "\\n" not in client_text
assert "Компания: Carrier &amp; Co" in client_text
assert "Контакт: João" in client_text
assert 'Telegram: <a href="tg://user?id=123456789">João</a>' in client_text
assert "Телефон: +351930000000" in client_text
assert "Свяжитесь напрямую и согласуйте детали перевозки." in client_text
assert "Telegram: 123456789" not in client_text

assert "Заказ №42 закреплён за вами." in carrier_text
assert "\\n" not in carrier_text
assert 'Клиент: <a href="tg://user?id=987654321">client_user</a>' in carrier_text
assert "Username: @client_user" in carrier_text
assert "Телефон: +351910000000" in carrier_text
assert "WhatsApp: +351920000000" in carrier_text
assert "Свяжитесь с клиентом и согласуйте детали перевозки." in carrier_text
assert "Telegram: 987654321" not in carrier_text
assert "Контакты клиента" not in client_text
assert "Контакты клиента" not in carrier_text

web_job = SimpleNamespace(
    id=43,
    client_telegram_user_id=None,
    client_telegram_username=None,
    customer_name=None,
    client_phone=None,
    client_whatsapp=None,
)

web_carrier_text = build_carrier_notification_text(web_job, carrier)

assert "Клиент: S/N" in web_carrier_text
assert "Username: S/N" in web_carrier_text
assert "@None" not in web_carrier_text
assert "tg://user?id=None" not in web_carrier_text

print("JOB_OFFER_CLIENT_NOTIFY_SMOKE_OK")
