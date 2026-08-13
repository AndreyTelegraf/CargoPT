from app.services.partner_outreach.dispatcher import within_business_window
from app.services.partner_outreach.policy import normalize_municipality
from app.services.partner_outreach.policy import validate_prospect_contact
from app.services.partner_outreach.templates import render_partner_outreach


email, domain = validate_prospect_contact(
    email="Parcerias@Example.pt",
    website_url="https://www.example.pt/services",
    source_url="https://example.pt/contactos",
)
assert email == "parcerias@example.pt"
assert domain == "example.pt"
assert normalize_municipality("Setúbal") == "setubal"

for invalid_email in ("maria@example.pt", "boss@gmail.com"):
    try:
        validate_prospect_contact(
            email=invalid_email,
            website_url="https://example.pt",
            source_url="https://example.pt/contactos",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("personal or mismatched email was accepted")

for locale in ("pt", "en", "ru"):
    rendered = render_partner_outreach(
        locale=locale,
        company_name="Ola Estate",
        category="real_estate",
        prospect_id=7,
        public_base_url="https://cargopt.pt",
        sender_signature="Equipa CargoPT",
    )
    assert rendered.subject
    assert "utm_source=partner_outreach" in rendered.text_body
    assert "prospect-7" in rendered.html_body
    assert "<img" not in rendered.html_body.lower()
    assert "CargoPT" in rendered.text_body

from datetime import UTC, datetime

assert within_business_window(datetime(2026, 8, 11, 10, 0, tzinfo=UTC))
assert not within_business_window(datetime(2026, 8, 9, 10, 0, tzinfo=UTC))

print("PARTNER_OUTREACH_POLICY_OK")
print("PARTNER_OUTREACH_TEMPLATE_LOCALE_OK")
