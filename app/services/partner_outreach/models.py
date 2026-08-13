from dataclasses import dataclass
from enum import StrEnum


class ProspectStatus(StrEnum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    QUEUED = "queued"
    CONTACTED = "contacted"
    REPLIED = "replied"
    DECLINED = "declined"
    DISQUALIFIED = "disqualified"


class OutreachMessageStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    SENDING = "sending"
    SENT = "sent"
    RETRY = "retry"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class SuppressionKind(StrEnum):
    EMAIL = "email"
    DOMAIN = "domain"
    NIF = "nif"
    ORGANIZATION = "organization"


@dataclass(frozen=True)
class RenderedPartnerOutreach:
    subject: str
    text_body: str
    html_body: str
