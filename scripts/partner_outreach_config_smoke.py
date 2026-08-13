from pydantic import ValidationError

from app.config import Settings


base = {
    "bot_token": "partner-outreach-config-smoke",
    "database_url": "sqlite+aiosqlite:///:memory:",
}

disabled = Settings(**base)
assert disabled.partner_outreach_enabled is False
assert disabled.partner_outreach_send_enabled is False
assert disabled.partner_outreach_daily_limit == 5

try:
    Settings(**base, partner_outreach_send_enabled=True)
except ValidationError as exc:
    assert "EMAIL_ENABLED" in str(exc)
else:
    raise AssertionError("outreach sending was accepted without email")

email = {
    **base,
    "email_enabled": True,
    "email_from_address": "hello@cargopt.pt",
    "email_smtp_host": "smtp.example.test",
    "email_smtp_username": "smtp-user",
    "email_smtp_password": "smtp-password",
    "partner_outreach_enabled": True,
    "partner_outreach_send_enabled": True,
}
try:
    Settings(**email, partner_outreach_legal_identity="CargoPT Test Lda")
except ValidationError as exc:
    assert "EMAIL_REPLY_TO" in str(exc)
else:
    raise AssertionError("outreach sending was accepted without reply-to")

try:
    Settings(**email, email_reply_to="hello@cargopt.pt")
except ValidationError as exc:
    assert "PARTNER_OUTREACH_LEGAL_IDENTITY" in str(exc)
else:
    raise AssertionError("outreach sending was accepted without legal identity")

valid = Settings(
    **email,
    email_reply_to="hello@cargopt.pt",
    partner_outreach_legal_identity="CargoPT Test Lda",
)
assert valid.partner_outreach_send_enabled is True

print("PARTNER_OUTREACH_CONFIG_GUARDS_OK")
