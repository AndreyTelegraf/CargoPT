"""Deterministic Telegram operations, persisted before delivery starts."""
import html
import re

from app.bot.completion_keyboard import build_completion_keyboard
from app.bot.offer_keyboard import build_offer_keyboard


def utf16_length(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def split_text(text: str, *, parse_mode=None, limit=4096) -> list[str]:
    """Keep entities and balanced HTML tags intact at conservative UTF-16 limits.

    Offer HTML is generated and user input escaped by build_offer_text. Entity
    tokens count by their decoded value; tags consume no displayed characters.
    """
    if parse_mode != "HTML":
        chunks, current, size = [], [], 0
        for char in text:
            units = utf16_length(char)
            if size + units > limit:
                chunks.append("".join(current))
                current, size = [], 0
            current.append(char)
            size += units
        return chunks + (["".join(current)] if current else [])

    tokens = re.findall(r"<[^>]*>|&(?:#[0-9]+|#x[0-9a-fA-F]+|[a-zA-Z]+);|[\s\S]", text)
    chunks, current, stack, size = [], [], [], 0
    for token in tokens:
        if token.startswith("<"):
            match = re.fullmatch(r"<(/?)([\w-]+)(?:\s[^>]*)?>", token)
            if not match:
                raise ValueError("unsupported HTML token")
            closing, tag = match.groups()
            if closing:
                if not stack or stack[-1][0] != tag:
                    raise ValueError("unbalanced notification HTML")
                stack.pop()
            else:
                stack.append((tag, token))
            current.append(token)
            continue
        units = utf16_length(html.unescape(token))
        if size + units > limit:
            chunks.append("".join(current) + "".join(f"</{tag}>" for tag, _ in reversed(stack)))
            current = [opening for _, opening in stack]
            size = 0
        current.append(token)
        size += units
    if stack:
        raise ValueError("unbalanced notification HTML")
    if size:
        chunks.append("".join(current))
    return chunks


def build_delivery_plan(snapshot: dict) -> list[dict]:
    payload = snapshot["payload"]
    text = payload.get("text")
    if not isinstance(text, str) or not text:
        raise ValueError("Telegram notification payload text is missing")
    carrier_offer = snapshot["notification_type"] == "carrier_offer"
    parse_mode = "HTML" if carrier_offer else payload.get("parse_mode")
    markup = payload.get("reply_markup")
    if carrier_offer:
        markup = build_offer_keyboard(snapshot["offer_id"], locale=payload.get("locale")).model_dump(mode="json")
    elif payload.get("completion_keyboard"):
        markup = build_completion_keyboard(snapshot["job_id"]).model_dump(mode="json")

    chunks = split_text(text, parse_mode=parse_mode)
    media = snapshot.get("media", []) if carrier_offer else []
    media = [item for item in media if item["media_type"] in {"photo", "video"}]
    caption_fits = len(split_text(text, parse_mode=parse_mode, limit=1024)) == 1
    if len(media) == 1 and caption_fits:
        item = media[0]
        method = item["media_type"]
        return [{"method": "send_"+method, "kwargs": {
            method: item["telegram_file_id"], "caption": text,
            "parse_mode": parse_mode, "reply_markup": markup,
        }}]

    plan = []
    # Albums support 2-10 items; retain every attachment, including a last single.
    for offset in range(0, len(media), 10):
        group = media[offset:offset+10]
        if len(group) == 1:
            item = group[0]
            method = item["media_type"]
            plan.append({"method": "send_"+method, "kwargs": {method: item["telegram_file_id"]}})
        else:
            plan.append({"method": "send_media_group", "kwargs": {"media": [
                {"type": item["media_type"], "media": item["telegram_file_id"]}
                for item in group
            ]}})
    for index, chunk in enumerate(chunks):
        plan.append({"method": "send_message", "kwargs": {
            "text": chunk, "parse_mode": parse_mode,
            "reply_markup": markup if index == len(chunks)-1 else None,
        }})
    return plan
