import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.bot.carrier_locale import LANGUAGE_LABELS
from app.bot.carrier_locale import SUPPORTED_CARRIER_LOCALES
from app.bot.carrier_locale import TRANSLATIONS
from app.bot.carrier_locale import normalize_carrier_locale
from app.bot.carrier_locale import parse_yes_no
from app.bot.carrier_locale import text
from app.bot.handlers.regions import REGION_LABELS
from app.bot.handlers.vehicle_type import VEHICLE_TYPE_LABELS
from app.models.carrier import CarrierCompany


assert SUPPORTED_CARRIER_LOCALES == ("pt", "en", "ru")
assert set(LANGUAGE_LABELS.values()) == set(SUPPORTED_CARRIER_LOCALES)
assert normalize_carrier_locale("pt-PT") == "pt"
assert normalize_carrier_locale("en_US") == "en"
assert normalize_carrier_locale("ru") == "ru"
assert normalize_carrier_locale("de") == "ru"

reference_keys = set(TRANSLATIONS["ru"])
assert reference_keys
for locale in SUPPORTED_CARRIER_LOCALES:
    assert set(TRANSLATIONS[locale]) == reference_keys
    assert parse_yes_no(text(locale, "yes"), locale) is True
    assert parse_yes_no(text(locale, "no"), locale) is False
    assert parse_yes_no("invalid", locale) is None
    assert set(REGION_LABELS[locale].values()) == {
        "Lisboa",
        "Porto",
        "Centro",
        "Alentejo",
        "Algarve",
        "all_portugal",
    }
    assert set(VEHICLE_TYPE_LABELS[locale].values()) == {
        "Carrinha",
        "Van",
        "Camião",
        "Camião+Reboque",
    }

assert "preferred_locale" in CarrierCompany.__table__.columns

handler_files = (
    "invite.py",
    "carrier_public_profile.py",
    "regions.py",
    "vehicle_count.py",
    "vehicle_type.py",
    "payload.py",
    "volume.py",
    "assembly.py",
    "packing.py",
    "tail_lift.py",
    "crane.py",
    "crane_weight.py",
    "crane_reach.py",
    "mobile_lift.py",
    "mobile_lift_floor.py",
    "mobile_lift_weight.py",
    "max_loaders.py",
    "company_phone.py",
    "company_email.py",
    "carrier_moderation_submit.py",
)
for filename in handler_files:
    source = (ROOT / "app/bot/handlers" / filename).read_text(encoding="utf-8")
    assert "carrier_locale" in source or "get_carrier_locale" in source, filename

print("CARRIER_LOCALE_SMOKE_OK")
