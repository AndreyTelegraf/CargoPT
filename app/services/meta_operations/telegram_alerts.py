from datetime import UTC
from datetime import datetime
from html import escape
import json

from aiogram import Bot
from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup

from app.config import settings
from app.models.meta_operations import MetaInboundEvent
from app.models.meta_operations import MetaSourceGroup


def build_event_keyboard(event: MetaInboundEvent) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if event.source_url:
        rows.append([InlineKeyboardButton(text="Открыть источник", url=event.source_url)])
    rows.append(
        [
            InlineKeyboardButton(text="Целевой", callback_data=f"metaevt:target:{event.id}"),
            InlineKeyboardButton(text="Мусор", callback_data=f"metaevt:noise:{event.id}"),
            InlineKeyboardButton(text="Обработано", callback_data=f"metaevt:handled:{event.id}"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_event_alert(event: MetaInboundEvent, group: MetaSourceGroup | None) -> str:
    group_name = group.name if group else "Группа не сопоставлена"
    excerpt = event.text.strip()
    if len(excerpt) > 900:
        excerpt = excerpt[:897].rstrip() + "..."
    label = {"target": "Целевой запрос", "review": "Нужна проверка"}.get(
        event.classification_label,
        event.classification_label,
    )
    lines = [
        f"<b>{escape(label)}</b> · {event.score}/100",
        f"<b>Группа:</b> {escape(group_name)}",
        f"<b>Язык:</b> {escape(event.language or '—')}",
        "",
        escape(excerpt),
    ]
    if event.draft_reply:
        lines.extend(("", "<b>Черновик ответа:</b>", escape(event.draft_reply)))
    return "\n".join(lines)


async def send_event_alert(
    bot: Bot,
    event: MetaInboundEvent,
    group: MetaSourceGroup | None,
) -> list[dict[str, int]]:
    message_refs: list[dict[str, int]] = []
    for chat_id in settings.meta_operations_chat_ids:
        message = await bot.send_message(
            chat_id=chat_id,
            text=format_event_alert(event, group),
            parse_mode="HTML",
            reply_markup=build_event_keyboard(event),
            disable_web_page_preview=True,
        )
        message_refs.append({"chat_id": chat_id, "message_id": message.message_id})
    if message_refs:
        now = datetime.now(UTC)
        event.telegram_alerted_at = now
        event.telegram_message_refs_json = json.dumps(message_refs)
        event.updated_at = now
    return message_refs
