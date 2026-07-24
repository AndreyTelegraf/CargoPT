from dataclasses import dataclass
from enum import StrEnum


class EmailEventType(StrEnum):
    REQUEST_RECEIVED = "request_received"
    OFFER_AVAILABLE = "offer_available"
    CARRIER_SELECTED = "carrier_selected"
    ASSIGNMENT_CONFIRMED = "assignment_confirmed"
    REQUEST_CANCELLED = "request_cancelled"


class EmailDeliveryStatus(StrEnum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    RETRY = "retry"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    text_body: str
    html_body: str
    from_address: str
    from_name: str
    reply_to: str | None = None


@dataclass(frozen=True)
class EmailSendResult:
    provider_message_id: str | None = None


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    text_body: str
    html_body: str
