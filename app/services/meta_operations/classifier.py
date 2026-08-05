from dataclasses import dataclass
import re
import unicodedata
from urllib.parse import urlencode


INTENT_TERMS = {
    "pt": (
        "procuro", "preciso", "alguem conhece", "alguem recomenda",
        "recomendam", "recomendacao", "orcamento", "quem faz",
        "necessito", "estou a procura", "estou procurando",
    ),
    "en": (
        "looking for", "need a", "need someone", "can anyone recommend",
        "does anyone know", "recommend a", "quote for", "who can",
    ),
    "ru": (
        "ищу", "нужен", "нужна", "нужно", "посоветуйте",
        "кто может", "подскажите", "требуется", "сколько стоит",
    ),
}

CARGO_TERMS = {
    "pt": (
        "transportadora", "transporte", "mudanca", "mudancas", "carrinha",
        "levar", "recolha", "entrega", "motorista", "frete", "mover",
        "sofa", "mobilia", "moveis", "frigorifico", "maquina de lavar",
    ),
    "en": (
        "carrier", "transport", "moving company", "mover", "van",
        "delivery", "pickup", "move a", "furniture", "sofa", "fridge",
        "washing machine", "freight", "driver",
    ),
    "ru": (
        "перевозчик", "перевозка", "перевезти", "переезд", "доставка",
        "машина", "фургон", "водитель", "мебель", "диван", "холодильник",
        "стиральная машина", "груз", "забрать", "доставить",
    ),
}

OFFER_TERMS = (
    "fazemos mudancas", "servico de mudancas", "servicos de transporte",
    "contacte nos", "peca o seu orcamento", "temos carrinha",
    "we offer", "our moving service", "available for deliveries",
    "предлагаем перевозки", "оказываем услуги", "наша компания",
    "свободна машина", "реклама", "promocao", "promoção",
)

ROUTE_TERMS = (
    " de ", " para ", " até ", " ate ", " from ", " to ", " из ",
    " в ", " до ", "lisboa", "porto", "algarve", "faro", "cascais",
    "sintra", "braga", "coimbra", "setubal", "leiria", "aveiro",
)


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    without_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", without_marks).strip()


def detect_language(text: str) -> str:
    lowered = text.lower()
    if re.search(r"[а-яё]", lowered):
        return "ru"
    normalized = normalize_text(text)
    pt_hits = sum(term in normalized for term in ("procuro", "preciso", "mudanca", "transporte", "para"))
    en_hits = sum(term in normalized for term in ("looking", "need", "moving", "transport", "from"))
    return "pt" if pt_hits >= en_hits else "en"


@dataclass(frozen=True)
class ClassificationResult:
    label: str
    confidence: float
    score: int
    language: str
    matched_terms: tuple[str, ...]


def classify_lead(text: str) -> ClassificationResult:
    language = detect_language(text)
    normalized = normalize_text(text)
    matched: list[str] = []

    intent_hits = [term for term in INTENT_TERMS[language] if term in normalized]
    cargo_hits = [term for term in CARGO_TERMS[language] if term in normalized]
    offer_hits = [term for term in OFFER_TERMS if normalize_text(term) in normalized]
    padded = f" {normalized} "
    route_hits = [
        term.strip()
        for term in ROUTE_TERMS
        if f" {normalize_text(term)} " in padded
    ]

    score = 0
    if intent_hits:
        score += 38 + min(10, (len(intent_hits) - 1) * 5)
        matched.extend(f"intent:{term}" for term in intent_hits[:4])
    if cargo_hits:
        score += 38 + min(10, (len(cargo_hits) - 1) * 4)
        matched.extend(f"cargo:{term}" for term in cargo_hits[:5])
    if route_hits:
        score += min(12, len(route_hits) * 4)
        matched.extend(f"route:{term}" for term in route_hits[:3])
    if "?" in text:
        score += 4
    if offer_hits:
        score -= 45
        matched.extend(f"offer:{term}" for term in offer_hits[:3])
        score = min(score, 25)
    if not intent_hits and cargo_hits:
        score = min(score, 49)
    if intent_hits and not cargo_hits:
        score = min(score, 44)

    score = max(0, min(100, score))
    if score >= 65:
        label = "target"
    elif score >= 40:
        label = "review"
    else:
        label = "noise"

    confidence = round(score / 100, 2) if label != "noise" else round((100 - score) / 100, 2)
    return ClassificationResult(
        label=label,
        confidence=confidence,
        score=score,
        language=language,
        matched_terms=tuple(matched),
    )


def build_draft_reply(language: str, *, group_id: int | None = None) -> str:
    query = urlencode(
        {
            "utm_source": "facebook",
            "utm_medium": "group_response",
            "utm_campaign": "meta_operations",
            "utm_content": f"group_{group_id}" if group_id else "unmatched_group",
        }
    )
    url = f"https://cargopt.pt/?{query}"
    templates = {
        "pt": (
            "Olá! Na CargoPT pode descrever o transporte e receber propostas "
            f"de transportadores adequados ao percurso: {url}"
        ),
        "en": (
            "Hello! With CargoPT you can describe the job and receive proposals "
            f"from carriers suitable for the route: {url}"
        ),
        "ru": (
            "Здравствуйте! В CargoPT можно описать перевозку и получить предложения "
            f"от подходящих для маршрута перевозчиков: {url}"
        ),
    }
    return templates.get(language, templates["pt"])
