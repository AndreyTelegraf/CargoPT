from pathlib import Path
from types import SimpleNamespace

from app.services.carrier_public_profile import missing_public_profile_fields


ROOT = Path(__file__).resolve().parents[1]


empty = SimpleNamespace(
    public_name=None,
    experience_since_year=None,
    logo_file_name=None,
    publication_consent_at=None,
    operating_regions=None,
)
assert missing_public_profile_fields(empty) == [
    "public_name",
    "experience_since_year",
    "logo",
    "publication_consent",
    "operating_regions",
]

complete = SimpleNamespace(
    public_name="Cargo Lisboa",
    experience_since_year=2018,
    logo_file_name="carrier_1.jpg",
    publication_consent_at="2026-07-31",
    operating_regions="Lisboa",
)
assert missing_public_profile_fields(complete) == []

model = (ROOT / "app/models/carrier.py").read_text(encoding="utf-8")
states = (ROOT / "app/bot/states/carrier_onboarding.py").read_text(encoding="utf-8")
handler = (ROOT / "app/bot/handlers/carrier_public_profile.py").read_text(
    encoding="utf-8"
)
invite = (ROOT / "app/bot/handlers/invite.py").read_text(encoding="utf-8")
regions = (ROOT / "app/bot/handlers/regions.py").read_text(encoding="utf-8")
api = (ROOT / "app/api/web_requests.py").read_text(encoding="utf-8")
schema = (ROOT / "app/api/web_request_schemas.py").read_text(encoding="utf-8")
workspace = (ROOT / "app/static/assets/js/tracking-workspace.js").read_text(
    encoding="utf-8"
)
css = (ROOT / "app/static/assets/css/components.css").read_text(encoding="utf-8")

for field in (
    "public_name",
    "experience_since_year",
    "logo_file_name",
    "publication_consent_at",
    "public_profile_requested_at",
):
    assert field in model

for state_name in (
    "public_name = State()",
    "experience_since_year = State()",
    "logo = State()",
    "publication_consent = State()",
):
    assert state_name in states

assert 'Command("profile")' in handler
assert "Разрешаю публикацию" in handler
assert 'token == "profile"' in invite
assert "bind_carrier_telegram_identity(" in invite
assert "username_carrier.telegram_user_id is None" in invite
assert 'data.get("profile_update_only")' in regions
assert '"/carriers/{carrier_id}/logo"' in api
assert "logo_url" in schema
assert "tracking-offer-avatar" in workspace
assert "experienceSinceLabel" in workspace
assert ".tracking-offer-logo" in css

print("CARRIER_PUBLIC_PROFILE_CONTRACT_OK")
