from email.message import EmailMessage as MimeEmailMessage
from email.utils import formataddr

import aiosmtplib
from aiosmtplib.errors import SMTPAuthenticationError
from aiosmtplib.errors import SMTPException
from aiosmtplib.errors import SMTPRecipientsRefused

from app.services.email.models import EmailMessage
from app.services.email.models import EmailSendResult
from app.services.email.transport import PermanentEmailTransportError
from app.services.email.transport import TemporaryEmailTransportError


class SmtpEmailTransport:
    def __init__(
        self,
        *,
        hostname: str,
        port: int,
        username: str,
        password: str,
        start_tls: bool,
        use_tls: bool,
        timeout_seconds: int,
    ) -> None:
        self.hostname = hostname
        self.port = port
        self.username = username
        self._password = password
        self.start_tls = start_tls
        self.use_tls = use_tls
        self.timeout_seconds = timeout_seconds

    async def send(self, message: EmailMessage) -> EmailSendResult:
        mime = MimeEmailMessage()
        mime["From"] = formataddr((message.from_name, message.from_address))
        mime["To"] = message.to
        mime["Subject"] = message.subject
        if message.reply_to:
            mime["Reply-To"] = message.reply_to
        mime.set_content(message.text_body, subtype="plain", charset="utf-8")
        mime.add_alternative(
            message.html_body,
            subtype="html",
            charset="utf-8",
        )

        try:
            _, response = await aiosmtplib.send(
                mime,
                hostname=self.hostname,
                port=self.port,
                username=self.username,
                password=self._password,
                start_tls=self.start_tls,
                use_tls=self.use_tls,
                timeout=self.timeout_seconds,
            )
        except (SMTPAuthenticationError, SMTPRecipientsRefused) as exc:
            raise PermanentEmailTransportError(
                "SMTP rejected credentials or recipient"
            ) from exc
        except (SMTPException, OSError, TimeoutError) as exc:
            raise TemporaryEmailTransportError(
                "SMTP delivery temporarily unavailable"
            ) from exc

        provider_message_id = str(response).strip()[:255] or None
        return EmailSendResult(provider_message_id=provider_message_id)
