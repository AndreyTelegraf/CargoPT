import re
import unicodedata
from urllib.parse import urlsplit


ALLOWED_LOCALES = frozenset({"pt", "en", "ru"})
ALLOWED_CATEGORIES = frozenset(
    {
        "real_estate",
        "relocation",
        "property_management",
        "coliving_student_housing",
        "interior_renovation",
        "cleaning",
    }
)

LISBON_METRO_MUNICIPALITIES = frozenset(
    {
        "alcochete",
        "almada",
        "amadora",
        "barreiro",
        "cascais",
        "lisboa",
        "loures",
        "mafra",
        "moita",
        "montijo",
        "odivelas",
        "oeiras",
        "palmela",
        "seixal",
        "sesimbra",
        "setubal",
        "sintra",
        "vila franca de xira",
    }
)

ROLE_MAILBOX_PREFIXES = frozenset(
    {
        "admin",
        "comercial",
        "commercial",
        "contact",
        "contacto",
        "geral",
        "hello",
        "info",
        "office",
        "parcerias",
        "partners",
        "partnerships",
        "reception",
        "sales",
        "team",
    }
)

_EMAIL_RE = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
    re.IGNORECASE,
)


def normalize_locale(value: str) -> str:
    locale = value.strip().lower().replace("_", "-").split("-", 1)[0]
    if locale not in ALLOWED_LOCALES:
        raise ValueError("partner locale must be pt, en, or ru")
    return locale


def normalize_municipality(value: str) -> str:
    normalized = normalize_organization(value)
    if normalized not in LISBON_METRO_MUNICIPALITIES:
        raise ValueError("municipality is outside Lisbon Metropolitan Area")
    return normalized


def normalize_organization(value: str) -> str:
    ascii_value = "".join(
        char
        for char in unicodedata.normalize("NFKD", value.strip().lower())
        if not unicodedata.combining(char)
    )
    return " ".join(re.sub(r"[^a-z0-9]+", " ", ascii_value).split())


def normalize_nif(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if not _EMAIL_RE.fullmatch(email):
        raise ValueError("invalid email address")
    return email


def email_domain(value: str) -> str:
    return normalize_email(value).rsplit("@", 1)[1]


def normalize_domain(value: str) -> str:
    raw = value.strip().lower()
    parsed = urlsplit(raw if "://" in raw else f"https://{raw}")
    domain = (parsed.hostname or "").strip(".")
    if domain.startswith("www."):
        domain = domain[4:]
    if not domain or "." not in domain:
        raise ValueError("invalid company domain")
    return domain.encode("idna").decode("ascii")


def require_public_http_url(value: str, *, field_name: str) -> str:
    url = value.strip()
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"{field_name} must be a public HTTP(S) URL")
    return url


def require_role_mailbox(value: str) -> str:
    email = normalize_email(value)
    local_part = email.split("@", 1)[0]
    prefix = re.split(r"[.+_-]", local_part, maxsplit=1)[0]
    if prefix not in ROLE_MAILBOX_PREFIXES:
        raise ValueError("only public role-based company mailboxes are allowed")
    return email


def validate_prospect_contact(
    *,
    email: str,
    website_url: str,
    source_url: str,
) -> tuple[str, str]:
    normalized_email = require_role_mailbox(email)
    website = require_public_http_url(website_url, field_name="website_url")
    require_public_http_url(source_url, field_name="source_url")
    domain = normalize_domain(website)
    if email_domain(normalized_email) != domain:
        raise ValueError("contact email domain must match the company website")
    return normalized_email, domain
