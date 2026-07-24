from typing import Protocol

from app.services.email.models import EmailMessage
from app.services.email.models import EmailSendResult


class EmailTransportError(Exception):
    pass


class TemporaryEmailTransportError(EmailTransportError):
    pass


class PermanentEmailTransportError(EmailTransportError):
    pass


class EmailTransport(Protocol):
    async def send(self, message: EmailMessage) -> EmailSendResult:
        ...
