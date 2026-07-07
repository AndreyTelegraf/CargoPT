import json
import logging
from asyncio import Lock
from pathlib import Path
from typing import Any

from aiogram.types import LinkPreviewOptions

from app.config import settings

SELF_AD_TEXT = """🚚 <b>Нужно быстро перевезти мебель, вещи или технику?</b>

Заполните заявку через <a href="https://t.me/CargoPT_bot">@cargo_pt_bot</a>, агрегатор оперативно подберёт лучшую транспортную компанию, а подходящий исполнитель сам с вами свяжется.

Это проще и эффективнее, чем обзванивать перевозчиков самостоятельно."""

SELF_AD_TARGETS = {
    ("baraholka_pt", 429),
    ("proflistpt", 8490),
}

_lock = Lock()
logger = logging.getLogger(__name__)


def _state_path() -> Path:
    return Path(settings.self_ad_state_path)


def _load_counts() -> dict[str, int]:
    path = _state_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    if isinstance(data.get("text_counts"), dict):
        counts = data["text_counts"]
        return {
            str(key): value
            for key, value in counts.items()
            if isinstance(value, int) and value >= 0
        }
    legacy_value = data.get("text_count", 0)
    if isinstance(legacy_value, int) and legacy_value >= 0:
        return {"baraholka_pt:429": legacy_value}
    return {}


def _save_counts(counts: dict[str, int]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"text_counts": counts}, ensure_ascii=False, indent=2)
    )


def _target_key(username: str, thread_id: int) -> str:
    return f"{username.lower()}:{thread_id}"


def _message_target_key(message: Any) -> str | None:
    if not settings.self_ad_enabled:
        return None

    raw_text = getattr(message, "text", None)
    raw_caption = getattr(message, "caption", None)
    text = raw_text if isinstance(raw_text, str) else raw_caption
    if not isinstance(text, str) or not text.strip():
        return None

    if text.strip() == SELF_AD_TEXT.strip():
        return None

    thread_id = getattr(message, "message_thread_id", None)
    if not isinstance(thread_id, int):
        return None

    chat = getattr(message, "chat", None)
    username = getattr(chat, "username", None)
    if not isinstance(username, str):
        return None

    target = (username.lower(), thread_id)
    if target not in SELF_AD_TARGETS:
        return None

    return _target_key(username, thread_id)


def is_target_text_message(message: Any) -> bool:
    return _message_target_key(message) is not None


async def process_self_ad_message(message: Any) -> bool:
    target_key = _message_target_key(message)
    if target_key is None:
        return False

    async with _lock:
        counts = _load_counts()
        count = counts.get(target_key, 0) + 1
        counts[target_key] = count
        should_post = count % settings.self_ad_every_n == 0
        logger.info(
            "SELF_AD_COUNT target=%s count=%s every_n=%s should_post=%s",
            target_key,
            count,
            settings.self_ad_every_n,
            should_post,
        )
        _save_counts(counts)

    if should_post:
        await message.answer(
            SELF_AD_TEXT,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                url="https://t.me/CargoPT_bot",
            ),
        )

    return should_post
