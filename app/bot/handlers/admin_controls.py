from datetime import UTC
from datetime import datetime
from datetime import timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.domain.admin_access import ADMIN_TELEGRAM_USER_IDS
from app.db.session import async_session_maker
from app.repositories.job import JobRepository

router = Router()


async def _resolve_carrier_target(repo, raw_value):
    value = raw_value.strip()

    if value.isdigit():
        return await repo.get_carrier_by_id(int(value))

    return await repo.get_carrier_by_username(value)



def _is_admin(message: Message) -> bool:
    return message.from_user is not None and message.from_user.id in ADMIN_TELEGRAM_USER_IDS


async def _resolve_client_target(
    repo: JobRepository,
    raw_value: str,
) -> tuple[int, str | None] | None:
    value = raw_value.strip()

    if value.isdigit():
        return int(value), None

    cleaned_username = value.lstrip("@").strip()
    if not cleaned_username:
        return None

    latest_job = await repo.get_latest_job_by_client_username(cleaned_username)
    if latest_job is None:
        return None

    return latest_job.client_telegram_user_id, latest_job.client_telegram_username


@router.message(Command("ban"))
async def ban_client(message: Message) -> None:
    if not _is_admin(message):
        await message.answer("Команда доступна только администратору CargoPT.")
        return

    parts = (message.text or "").split(maxsplit=2)

    if len(parts) < 2:
        await message.answer("Формат: /ban <telegram_user_id|@username> [причина]")
        return

    target = parts[1]
    reason = parts[2] if len(parts) > 2 else None

    async with async_session_maker() as session:
        repo = JobRepository(session)
        resolved = await _resolve_client_target(repo, target)

        if resolved is None:
            await message.answer("Клиент не найден. Используйте telegram_user_id или @username из уже созданных заявок.")
            return

        telegram_user_id, username = resolved

        await repo.ban_client(
            telegram_user_id=telegram_user_id,
            username=username,
            reason=reason,
            banned_by_admin_id=message.from_user.id,
        )

        await session.commit()

    label = f"@{username}" if username else str(telegram_user_id)
    await message.answer(f"Клиент {label} заблокирован.")


@router.message(Command("unban"))
async def unban_client(message: Message) -> None:
    if not _is_admin(message):
        await message.answer("Команда доступна только администратору CargoPT.")
        return

    parts = (message.text or "").split(maxsplit=1)

    if len(parts) != 2:
        await message.answer("Формат: /unban <telegram_user_id|@username>")
        return

    target = parts[1]

    async with async_session_maker() as session:
        repo = JobRepository(session)
        resolved = await _resolve_client_target(repo, target)

        if resolved is None:
            await message.answer("Клиент не найден. Используйте telegram_user_id или @username из уже созданных заявок.")
            return

        telegram_user_id, username = resolved

        ban = await repo.unban_client(
            telegram_user_id=telegram_user_id,
            unbanned_by_admin_id=message.from_user.id,
        )

        await session.commit()

    if ban is None:
        await message.answer("Активная блокировка не найдена.")
    else:
        label = f"@{username}" if username else str(telegram_user_id)
        await message.answer(f"Клиент {label} разблокирован.")


@router.message(Command("suspend_carrier"))
async def suspend_carrier(message: Message) -> None:
    if not _is_admin(message):
        await message.answer("Команда доступна только администратору CargoPT.")
        return

    parts = (message.text or "").split(maxsplit=1)

    if len(parts) != 2:
        await message.answer("Формат: /suspend_carrier <carrier_id|@username>")
        return

    target = parts[1]

    from app.repositories.carrier import CarrierRepository

    async with async_session_maker() as session:
        repo = CarrierRepository(session)

        carrier = await _resolve_carrier_target(repo, target)
        if carrier is None:
            await message.answer("Перевозчик не найден.")
            return

        carrier = await repo.suspend_carrier(carrier.id)

        await session.commit()

    await message.answer(
        f"Перевозчик #{carrier.id} временно отключён от получения заявок."
    )


@router.message(Command("unsuspend_carrier"))
async def unsuspend_carrier(message: Message) -> None:
    if not _is_admin(message):
        await message.answer("Команда доступна только администратору CargoPT.")
        return

    parts = (message.text or "").split(maxsplit=1)

    if len(parts) != 2:
        await message.answer("Формат: /unsuspend_carrier <carrier_id|@username>")
        return

    target = parts[1]

    from app.repositories.carrier import CarrierRepository

    async with async_session_maker() as session:
        repo = CarrierRepository(session)

        carrier = await _resolve_carrier_target(repo, target)
        if carrier is None:
            await message.answer("Перевозчик не найден.")
            return

        carrier = await repo.unsuspend_carrier(carrier.id)

        await session.commit()

    await message.answer(
        f"Перевозчик #{carrier.id} возвращён в ротацию заявок."
    )


@router.message(Command("pay_carrier"))
async def pay_carrier(message: Message) -> None:
    if not _is_admin(message):
        await message.answer("Команда доступна только администратору CargoPT.")
        return

    parts = (message.text or "").split(maxsplit=3)

    if len(parts) < 3:
        await message.answer("Формат: /pay_carrier <carrier_id|@username> <days> [note]")
        return

    target = parts[1]
    raw_days = parts[2]
    note = parts[3] if len(parts) > 3 else None

    try:
        days = int(raw_days)
    except ValueError:
        await message.answer("Количество дней должно быть числом.")
        return

    if days <= 0:
        await message.answer("Количество дней должно быть больше нуля.")
        return

    from app.repositories.carrier import CarrierRepository

    now = datetime.now(UTC)

    async with async_session_maker() as session:
        repo = CarrierRepository(session)

        carrier = await _resolve_carrier_target(repo, target)
        if carrier is None:
            await message.answer("Перевозчик не найден.")
            return

        base = carrier.paid_until
        if base is not None and base.tzinfo is None:
            base = base.replace(tzinfo=UTC)

        if base is None or base < now:
            base = now

        carrier.paid_until = base + timedelta(days=days)
        carrier.updated_at = now

        if note:
            previous_note = carrier.internal_note or ""
            carrier.internal_note = (previous_note + "\n" if previous_note else "") + (
                f"Payment extended by admin {message.from_user.id}: +{days} days. Note: {note}"
            )

        await session.commit()

        paid_until = carrier.paid_until
        carrier_id = carrier.id
        company_name = carrier.company_name

    await message.answer(
        f"Оплата перевозчика #{carrier_id} ({company_name}) продлена до "
        f"{paid_until.strftime('%d.%m.%Y %H:%M')} UTC."
    )
