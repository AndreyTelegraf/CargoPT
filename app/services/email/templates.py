from html import escape

from app.services.email.models import EmailEventType
from app.services.email.models import RenderedEmail


_COPY = {
    "pt": {
        EmailEventType.REQUEST_RECEIVED: (
            "CargoPT — recebemos o seu pedido",
            "Recebemos o seu pedido de transporte.",
            (
                "Estamos a procurar transportadores adequados. "
                "Pode acompanhar o estado do pedido e ver novas propostas "
                "através desta ligação:"
            ),
            (
                "Guarde esta ligação para poder abrir o pedido "
                "noutro dispositivo."
            ),
        ),
        EmailEventType.OFFER_AVAILABLE: (
            "CargoPT — recebeu uma proposta",
            "Já existe uma proposta para o seu pedido.",
            (
                "Abra o pedido para consultar os detalhes e escolher "
                "um transportador:"
            ),
            "",
        ),
        EmailEventType.CARRIER_SELECTED: (
            "CargoPT — a sua escolha foi guardada",
            "A sua escolha foi guardada.",
            (
                "Estamos a concluir a confirmação com o transportador. "
                "Pode acompanhar o estado aqui:"
            ),
            "",
        ),
        EmailEventType.ASSIGNMENT_CONFIRMED: (
            "CargoPT — transportador confirmado",
            "O transportador foi confirmado para o seu pedido.",
            "Consulte os dados atuais do pedido nesta ligação:",
            "",
        ),
        EmailEventType.REQUEST_CANCELLED: (
            "CargoPT — pedido cancelado",
            "O seu pedido foi cancelado.",
            "Pode consultar o estado atual nesta ligação:",
            "",
        ),
    },
    "en": {
        EmailEventType.REQUEST_RECEIVED: (
            "CargoPT — your request has been received",
            "We have received your transport request.",
            (
                "We are looking for suitable carriers. You can follow the "
                "request status and view new offers using this link:"
            ),
            (
                "Save this link so you can open the request on "
                "another device."
            ),
        ),
        EmailEventType.OFFER_AVAILABLE: (
            "CargoPT — an offer is available",
            "An offer is now available for your request.",
            "Open the request to view the details and choose a carrier:",
            "",
        ),
        EmailEventType.CARRIER_SELECTED: (
            "CargoPT — your selection has been saved",
            "Your selection has been saved.",
            (
                "We are completing the confirmation with the carrier. "
                "You can follow the status here:"
            ),
            "",
        ),
        EmailEventType.ASSIGNMENT_CONFIRMED: (
            "CargoPT — carrier confirmed",
            "The carrier has been confirmed for your request.",
            "View the latest request details using this link:",
            "",
        ),
        EmailEventType.REQUEST_CANCELLED: (
            "CargoPT — request cancelled",
            "Your request has been cancelled.",
            "You can view its current status using this link:",
            "",
        ),
    },
    "ru": {
        EmailEventType.REQUEST_RECEIVED: (
            "CargoPT — заявка получена",
            "Мы получили вашу заявку на перевозку.",
            (
                "Сейчас мы ищем подходящих перевозчиков. Следить за статусом "
                "заявки и новыми предложениями можно по ссылке:"
            ),
            (
                "Сохраните эту ссылку, чтобы открыть заявку "
                "на другом устройстве."
            ),
        ),
        EmailEventType.OFFER_AVAILABLE: (
            "CargoPT — по заявке поступило предложение",
            "По вашей заявке появилось предложение.",
            (
                "Откройте заявку, чтобы посмотреть детали и выбрать "
                "перевозчика:"
            ),
            "",
        ),
        EmailEventType.CARRIER_SELECTED: (
            "CargoPT — выбор перевозчика сохранён",
            "Ваш выбор сохранён.",
            (
                "Мы завершаем подтверждение с перевозчиком. "
                "Следить за статусом можно здесь:"
            ),
            "",
        ),
        EmailEventType.ASSIGNMENT_CONFIRMED: (
            "CargoPT — перевозчик подтверждён",
            "Перевозчик по вашей заявке подтверждён.",
            "Актуальные данные заявки доступны по ссылке:",
            "",
        ),
        EmailEventType.REQUEST_CANCELLED: (
            "CargoPT — заявка отменена",
            "Ваша заявка отменена.",
            "Текущий статус можно посмотреть по ссылке:",
            "",
        ),
    },
}


def normalize_email_locale(locale: str | None) -> str:
    normalized = (locale or "").strip().lower().replace("_", "-")
    if normalized == "en" or normalized.startswith("en-"):
        return "en"
    if normalized == "ru" or normalized.startswith("ru-"):
        return "ru"
    return "pt"


def _greeting(locale: str, customer_name: str | None) -> str:
    name = (customer_name or "").strip()
    if locale == "en":
        return f"Hello {name}," if name else "Hello,"
    if locale == "ru":
        return f"Здравствуйте, {name}!" if name else "Здравствуйте!"
    return f"Olá {name}," if name else "Olá,"


def render_email(
    *,
    event_type: EmailEventType | str,
    locale: str | None,
    tracking_url: str,
    customer_name: str | None = None,
) -> RenderedEmail:
    event = EmailEventType(event_type)
    normalized_locale = normalize_email_locale(locale)
    subject, lead, action, closing = _COPY[normalized_locale][event]
    greeting = _greeting(normalized_locale, customer_name)

    paragraphs = [greeting, lead, action, tracking_url]
    if closing:
        paragraphs.append(closing)
    paragraphs.append("CargoPT")
    text_body = "\n\n".join(paragraphs)

    safe_url = escape(tracking_url, quote=True)
    html_paragraphs = [
        f"<p>{escape(greeting)}</p>",
        f"<p>{escape(lead)}</p>",
        f"<p>{escape(action)}</p>",
        (
            f'<p><a href="{safe_url}">'
            f"{escape(tracking_url)}</a></p>"
        ),
    ]
    if closing:
        html_paragraphs.append(f"<p>{escape(closing)}</p>")
    html_paragraphs.append("<p>CargoPT</p>")
    html_body = (
        '<!doctype html><html lang="'
        + normalized_locale
        + '"><body>'
        + "".join(html_paragraphs)
        + "</body></html>"
    )

    return RenderedEmail(
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
