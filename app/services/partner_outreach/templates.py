from html import escape
from urllib.parse import urlencode

from app.services.partner_outreach.models import RenderedPartnerOutreach
from app.services.partner_outreach.policy import normalize_locale


_COPY = {
    "pt": {
        "subject": "Parceria útil para clientes em mudança — CargoPT",
        "intro": (
            "A CargoPT é uma plataforma portuguesa onde clientes descrevem "
            "uma mudança ou transporte, recebem propostas de transportadores "
            "e escolhem a opção mais adequada."
        ),
        "fit": {
            "real_estate": "clientes que estão prestes a mudar de casa",
            "relocation": "clientes que estão a instalar-se em Portugal",
            "property_management": "proprietários e inquilinos em mudança",
            "coliving_student_housing": "residentes que entram ou saem do alojamento",
            "interior_renovation": "clientes que precisam de transportar móveis e materiais",
            "cleaning": "clientes que estão a preparar uma entrada ou saída de imóvel",
        },
        "body": (
            "Estamos a criar uma pequena rede de parceiros na Área Metropolitana "
            "de Lisboa. O serviço pode ser útil para {fit}.\n\n"
            "A colaboração é simples: podem incluir a CargoPT no vosso guia de "
            "serviços recomendados ou indicar-nos quando surgir uma pergunta sobre "
            "mudanças e transporte. Fornecemos um texto curto em português, inglês "
            "e russo e uma ligação identificada para a vossa empresa. Não há custo, "
            "exclusividade nem obrigação de contrapartida.\n\n"
            "Faria sentido prepararmos esse material para a {company}?"
        ),
        "link_label": "Conhecer a CargoPT",
        "disclosure": (
            "Esta proposta comercial foi enviada para o contacto empresarial "
            "público indicado no site da empresa. Para não receber mais mensagens "
            "da CargoPT, basta responder «não»; o endereço será bloqueado de imediato."
        ),
    },
    "en": {
        "subject": "A practical moving-service partner for your clients — CargoPT",
        "intro": (
            "CargoPT is a Portuguese platform where customers describe a move or "
            "transport job, receive offers from carriers, and choose the option "
            "that suits them."
        ),
        "fit": {
            "real_estate": "clients who are about to move home",
            "relocation": "clients who are settling in Portugal",
            "property_management": "owners and tenants who are moving",
            "coliving_student_housing": "residents moving into or out of accommodation",
            "interior_renovation": "clients who need furniture or materials transported",
            "cleaning": "clients preparing to move into or out of a property",
        },
        "body": (
            "We are building a small partner network in the Lisbon Metropolitan "
            "Area. The service can be useful for {fit}.\n\n"
            "The collaboration can be simple: include CargoPT in your recommended "
            "services guide, or mention us when a moving or transport question comes "
            "up. We provide a short description in Portuguese, English, and Russian, "
            "plus a link identified for your company. There is no fee, exclusivity, "
            "or obligation to reciprocate.\n\n"
            "Would it make sense for us to prepare that material for {company}?"
        ),
        "link_label": "View CargoPT",
        "disclosure": (
            "This commercial partnership proposal was sent to the public business "
            "contact shown on the company website. To receive no further messages "
            "from CargoPT, simply reply “no”; the address will be suppressed immediately."
        ),
    },
    "ru": {
        "subject": "CargoPT для клиентов, которым нужен переезд в Португалии",
        "intro": (
            "CargoPT — португальская платформа, где клиент описывает переезд или "
            "перевозку, получает предложения перевозчиков и выбирает подходящий вариант."
        ),
        "fit": {
            "real_estate": "клиентов, которые готовятся к переезду",
            "relocation": "клиентов, которые обустраиваются в Португалии",
            "property_management": "собственников и арендаторов во время переезда",
            "coliving_student_housing": "жильцов при заселении и выезде",
            "interior_renovation": "клиентов, которым нужно перевезти мебель или материалы",
            "cleaning": "клиентов, которые готовят жильё к заселению или выезду",
        },
        "body": (
            "Мы формируем небольшую партнёрскую сеть в Лиссабонском регионе. "
            "Сервис может быть полезен для {fit}.\n\n"
            "Сотрудничество может быть простым: добавить CargoPT в памятку с "
            "рекомендованными сервисами или упоминать нас, когда возникает вопрос "
            "о переезде и перевозке. Мы подготовим короткий текст на португальском, "
            "английском и русском и отдельную ссылку для вашей компании. Без оплаты, "
            "эксклюзивности и обязательных ответных шагов.\n\n"
            "Имеет смысл подготовить такой материал для {company}?"
        ),
        "link_label": "Посмотреть CargoPT",
        "disclosure": (
            "Это коммерческое предложение о партнёрстве отправлено на публичный "
            "корпоративный адрес с сайта компании. Чтобы больше не получать письма "
            "CargoPT, достаточно ответить «нет»; адрес будет сразу исключён из рассылки."
        ),
    },
}


def build_partner_url(
    *,
    locale: str,
    prospect_id: int,
    public_base_url: str,
) -> str:
    normalized_locale = normalize_locale(locale)
    locale_path = "" if normalized_locale == "pt" else f"/{normalized_locale}"
    query = urlencode(
        {
            "utm_source": "partner_outreach",
            "utm_medium": "email",
            "utm_campaign": "lisbon_partners",
            "utm_content": f"prospect-{prospect_id}",
        }
    )
    return f"{public_base_url.rstrip('/')}{locale_path}/?{query}"


def render_partner_outreach(
    *,
    locale: str,
    company_name: str,
    category: str,
    prospect_id: int,
    public_base_url: str,
    sender_signature: str,
    legal_identity: str,
) -> RenderedPartnerOutreach:
    normalized_locale = normalize_locale(locale)
    copy = _COPY[normalized_locale]
    fit = copy["fit"].get(category)
    if fit is None:
        raise ValueError("unsupported partner category")
    company = company_name.strip()
    if not company:
        raise ValueError("company_name is required")
    sender_legal_identity = legal_identity.strip()
    if not sender_legal_identity:
        raise ValueError("partner outreach legal identity is required")
    partner_url = build_partner_url(
        locale=normalized_locale,
        prospect_id=prospect_id,
        public_base_url=public_base_url,
    )
    body = copy["body"].format(fit=fit, company=company)
    text_body = (
        f"{copy['intro']}\n\n{body}\n\n"
        f"{copy['link_label']}: {partner_url}\n\n"
        f"{sender_signature}\n{sender_legal_identity}\n\n---\n"
        f"{copy['disclosure']}"
    )
    paragraphs = "".join(
        f"<p>{escape(paragraph)}</p>" for paragraph in body.split("\n\n")
    )
    html_body = (
        "<!doctype html><html><body>"
        f"<p>{escape(copy['intro'])}</p>{paragraphs}"
        f'<p><a href="{escape(partner_url, quote=True)}">'
        f"{escape(copy['link_label'])}</a></p>"
        f"<p>{escape(sender_signature)}<br>"
        f"{escape(sender_legal_identity)}</p>"
        f"<hr><p><small>{escape(copy['disclosure'])}</small></p>"
        "</body></html>"
    )
    return RenderedPartnerOutreach(
        subject=copy["subject"],
        text_body=text_body,
        html_body=html_body,
    )
