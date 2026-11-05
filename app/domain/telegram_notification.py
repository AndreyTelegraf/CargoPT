from enum import StrEnum


class TelegramNotificationType(StrEnum):
    CARRIER_OFFER = "carrier_offer"
    MANUAL_REVIEW = "manual_review"
    LIFECYCLE_MESSAGE = "lifecycle_message"


class TelegramDeliveryStatus(StrEnum):
    PENDING = "pending"
    SENDING = "sending"
    RETRY = "retry"
    SENT = "sent"
    FAILED = "failed"
    UNCERTAIN = "uncertain"
