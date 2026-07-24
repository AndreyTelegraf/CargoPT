from app.services.email.models import EmailEventType
from app.services.email.templates import render_email


EXPECTED_SUBJECTS = {
    "pt": {
        EmailEventType.REQUEST_RECEIVED:
            "CargoPT — recebemos o seu pedido",
        EmailEventType.OFFER_AVAILABLE:
            "CargoPT — recebeu uma proposta",
        EmailEventType.CARRIER_SELECTED:
            "CargoPT — a sua escolha foi guardada",
        EmailEventType.ASSIGNMENT_CONFIRMED:
            "CargoPT — transportador confirmado",
        EmailEventType.REQUEST_CANCELLED:
            "CargoPT — pedido cancelado",
    },
    "en": {
        EmailEventType.REQUEST_RECEIVED:
            "CargoPT — your request has been received",
        EmailEventType.OFFER_AVAILABLE:
            "CargoPT — an offer is available",
        EmailEventType.CARRIER_SELECTED:
            "CargoPT — your selection has been saved",
        EmailEventType.ASSIGNMENT_CONFIRMED:
            "CargoPT — carrier confirmed",
        EmailEventType.REQUEST_CANCELLED:
            "CargoPT — request cancelled",
    },
    "ru": {
        EmailEventType.REQUEST_RECEIVED:
            "CargoPT — заявка получена",
        EmailEventType.OFFER_AVAILABLE:
            "CargoPT — по заявке поступило предложение",
        EmailEventType.CARRIER_SELECTED:
            "CargoPT — выбор перевозчика сохранён",
        EmailEventType.ASSIGNMENT_CONFIRMED:
            "CargoPT — перевозчик подтверждён",
        EmailEventType.REQUEST_CANCELLED:
            "CargoPT — заявка отменена",
    },
}

URLS = {
    "pt": "https://cargopt.pt/track/token-pt",
    "en": "https://cargopt.pt/en/track/token-en",
    "ru": "https://cargopt.pt/ru/track/token-ru",
}


for locale, events in EXPECTED_SUBJECTS.items():
    for event_type, expected_subject in events.items():
        for name in (None, "Ana <script>alert(1)</script>"):
            rendered = render_email(
                event_type=event_type,
                locale=locale,
                tracking_url=URLS[locale],
                customer_name=name,
            )
            assert rendered.subject == expected_subject
            assert URLS[locale] in rendered.text_body
            assert URLS[locale] in rendered.html_body
            assert "None" not in rendered.text_body
            assert "undefined" not in rendered.text_body
            assert "<script>" not in rendered.html_body
            assert "text/html" not in rendered.html_body

fallback = render_email(
    event_type=EmailEventType.REQUEST_RECEIVED,
    locale="de",
    tracking_url=URLS["pt"],
)
assert fallback.subject == EXPECTED_SUBJECTS["pt"][
    EmailEventType.REQUEST_RECEIVED
]
assert "Olá," in fallback.text_body

print("EMAIL_TEMPLATE_LOCALE_OK")
