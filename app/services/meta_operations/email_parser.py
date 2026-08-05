from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from html import unescape
import re


URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class ParsedInboundEmail:
    message_id: str | None
    sender: str | None
    subject: str | None
    text: str
    urls: tuple[str, ...]


def _clean_html(value: str) -> str:
    value = re.sub(r"<(br|/p|/div)\b[^>]*>", "\n", value, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", unescape(TAG_RE.sub(" ", value))).strip()


def parse_rfc822(payload: bytes) -> ParsedInboundEmail:
    message = BytesParser(policy=policy.default).parsebytes(payload)
    text_parts: list[str] = []
    html_parts: list[str] = []

    if message.is_multipart():
        for part in message.walk():
            if part.get_content_disposition() == "attachment":
                continue
            content_type = part.get_content_type()
            if content_type not in {"text/plain", "text/html"}:
                continue
            content = part.get_content()
            if content_type == "text/plain":
                text_parts.append(str(content))
            else:
                html_parts.append(str(content))
    else:
        content = str(message.get_content())
        if message.get_content_type() == "text/html":
            html_parts.append(content)
        else:
            text_parts.append(content)

    body = "\n".join(text_parts).strip()
    if not body and html_parts:
        body = "\n".join(_clean_html(value) for value in html_parts)
    urls = tuple(dict.fromkeys(URL_RE.findall(body)))
    return ParsedInboundEmail(
        message_id=(message.get("Message-ID") or "").strip() or None,
        sender=(message.get("From") or "").strip() or None,
        subject=(message.get("Subject") or "").strip() or None,
        text=body[:20000],
        urls=urls[:30],
    )
