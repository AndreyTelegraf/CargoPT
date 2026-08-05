from aiogram import F
from aiogram import Router
from aiogram.types import CallbackQuery

from app.config import settings
from app.db.session import async_session_maker
from app.domain.admin_access import CARGOPT_OPERATOR_TELEGRAM_USER_IDS
from app.repositories.meta_operations import MetaOperationsRepository


router = Router()


@router.callback_query(F.data.startswith("metaevt:"))
async def handle_meta_event_status(callback: CallbackQuery) -> None:
    if callback.from_user.id not in (
        CARGOPT_OPERATOR_TELEGRAM_USER_IDS | frozenset(settings.meta_operations_chat_ids)
    ):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    parts = (callback.data or "").split(":")
    if len(parts) != 3 or parts[1] not in {"target", "noise", "handled"}:
        await callback.answer("Некорректное действие.", show_alert=True)
        return
    try:
        event_id = int(parts[2])
    except ValueError:
        await callback.answer("Некорректный номер запроса.", show_alert=True)
        return

    async with async_session_maker() as session:
        try:
            await MetaOperationsRepository(session).update_event_status(
                event_id=event_id,
                status=parts[1],
                actor=f"telegram:{callback.from_user.id}",
            )
        except ValueError:
            await callback.answer("Запрос уже недоступен.", show_alert=True)
            return
        await session.commit()

    labels = {"target": "Целевой", "noise": "Мусор", "handled": "Обработано"}
    await callback.answer(labels[parts[1]])
