import json
from asyncio import Lock
from pathlib import Path
from typing import Any

from aiogram.types import LinkPreviewOptions

from app.config import settings

SELF_AD_TEXTS = (
    """🚚 <b>Нужно быстро перевезти мебель, вещи или технику?</b>

Заполните заявку через <a href="https://cargopt.pt">cargopt.pt</a>, агрегатор оперативно подберёт лучшую транспортную компанию, а подходящий исполнитель сам с вами свяжется.

Это проще и эффективнее, чем обзванивать перевозчиков самостоятельно.""",

    """🚚 <b>Не хотите тратить время на поиск перевозчика?</b>

Оставьте одну заявку через <a href="https://cargopt.pt">cargopt.pt</a>, а сервис передаст её подходящим транспортным компаниям.

Вместо множества звонков исполнитель сам свяжется с вами.""",

    """🚚 <b>Ищете перевозчика для переезда или доставки?</b>

Не отправляйте одинаковое сообщение разным компаниям.

Заполните заявку один раз через <a href="https://cargopt.pt">cargopt.pt</a> — подходящий исполнитель сам выйдет с вами на связь.""",

    """🚚 <b>Переезд, доставка мебели или техники?</b>

Пара минут на заявку в <a href="https://cargopt.pt">cargopt.pt</a> может сэкономить часы поиска перевозчика.

Сервис найдёт подходящую транспортную компанию, и исполнитель сам свяжется с вами.""",

    """🚚 <b>CargoPT — агрегатор перевозчиков по Португалии.</b>

Опишите, что и куда нужно перевезти, через <a href="https://cargopt.pt">cargopt.pt</a>.

Сервис передаст заявку подходящим исполнителям и поможет быстрее найти перевозчика.""",

    """🚚 <b>Нет времени искать перевозчика самостоятельно?</b>

Заполните заявку через <a href="https://cargopt.pt">cargopt.pt</a>.

Пока вы занимаетесь своими делами, сервис подберёт подходящего исполнителя, и он сам с вами свяжется.""",

    """🚚 <b>Одна заявка вместо долгих поисков.</b>

Опишите перевозку через <a href="https://cargopt.pt">cargopt.pt</a>.

Агрегатор подберёт подходящую транспортную компанию, а исполнитель свяжется с вами для обсуждения деталей.""",
)

# Сохраняем имя для обратной совместимости с существующими импортами.
SELF_AD_TEXT = SELF_AD_TEXTS[0]

_SELF_AD_TEXT_VALUES = frozenset(text.strip() for text in SELF_AD_TEXTS)

SELF_AD_TARGETS = {
    ("baraholka_pt", 429),
    ("proflistpt", 8490),
}

SELF_AD_TARGET_EVERY_N = {
    "baraholka_pt:429": 20,
    "proflistpt:8490": 9,
}

_lock = Lock()


def _state_path() -> Path:
    return Path(settings.self_ad_state_path)


def _valid_non_negative_ints(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): item
        for key, item in value.items()
        if isinstance(item, int) and item >= 0
    }


def _load_state() -> tuple[dict[str, int], dict[str, int]]:
    path = _state_path()
    if not path.exists():
        return {}, {}

    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}, {}

    counts = _valid_non_negative_ints(data.get("text_counts"))
    variant_indexes = _valid_non_negative_ints(data.get("variant_indexes"))

    if not counts:
        legacy_value = data.get("text_count", 0)
        if isinstance(legacy_value, int) and legacy_value >= 0:
            counts = {"baraholka_pt:429": legacy_value}

    return counts, variant_indexes


def _save_state(
    counts: dict[str, int],
    variant_indexes: dict[str, int],
) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "text_counts": counts,
                "variant_indexes": variant_indexes,
            },
            ensure_ascii=False,
            indent=2,
        )
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

    if text.strip() in _SELF_AD_TEXT_VALUES:
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

    ad_text: str | None = None

    async with _lock:
        counts, variant_indexes = _load_state()

        count = counts.get(target_key, 0) + 1
        counts[target_key] = count

        every_n = SELF_AD_TARGET_EVERY_N.get(
            target_key,
            settings.self_ad_every_n,
        )
        should_post = count % every_n == 0

        if should_post:
            variant_index = (
                variant_indexes.get(target_key, 0) % len(SELF_AD_TEXTS)
            )
            ad_text = SELF_AD_TEXTS[variant_index]
            variant_indexes[target_key] = (
                variant_index + 1
            ) % len(SELF_AD_TEXTS)

        _save_state(counts, variant_indexes)

    if ad_text is not None:
        await message.answer(
            ad_text,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                url="https://cargopt.pt",
            ),
        )

    return should_post
