from pydantic import ValidationError

from app.config import Settings


BASE = {
    "bot_token": "test-token",
    "database_url": "sqlite+aiosqlite:///:memory:",
}


disabled = Settings(**BASE)
assert disabled.email_enabled is False
assert disabled.email_transport == "smtp"
assert disabled.email_smtp_host == ""

try:
    Settings(**BASE, email_enabled=True)
except ValidationError as exc:
    message = str(exc)
    assert "EMAIL_FROM_ADDRESS" in message
    assert "EMAIL_SMTP_PASSWORD" in message
else:
    raise AssertionError("enabled email accepted incomplete configuration")

valid = Settings(
    **BASE,
    email_enabled=True,
    email_from_address="noreply@cargopt.pt",
    email_smtp_host="smtp-relay.brevo.com",
    email_smtp_username="smtp-user",
    email_smtp_password="smtp-secret-value",
)
assert valid.email_enabled is True
assert valid.email_smtp_password.get_secret_value() == "smtp-secret-value"
assert "smtp-secret-value" not in repr(valid)

try:
    Settings(
        **BASE,
        email_smtp_starttls=True,
        email_smtp_use_tls=True,
    )
except ValidationError as exc:
    assert "cannot both be enabled" in str(exc)
else:
    raise AssertionError("conflicting TLS modes were accepted")

print("EMAIL_CONFIG_VALIDATION_OK")
