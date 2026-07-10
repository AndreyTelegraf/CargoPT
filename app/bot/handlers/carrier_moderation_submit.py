import html

from aiogram import F
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import Message
from aiogram.types import ReplyKeyboardRemove
from sqlalchemy import select

from app.domain.admin_access import ADMIN_TELEGRAM_USER_IDS
from app.bot.states.carrier_onboarding import CarrierOnboardingStates
from app.db.session import async_session_maker
from app.domain.carrier_status import CarrierStatus
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.models.job import Job
from app.services.carrier_onboarding import CarrierOnboardingService
from app.services.carrier_search import CarrierSearchService
from app.services.job_matching import JobMatchingService
from app.services.job_offer import JobOfferService
from app.services.offer_distribution import OfferDistributionService
from app.services.offer_notification import send_job_offers_to_carriers

router = Router()

DEFAULT_ADMIN_USERNAME = "andreytelegraf"


def _safe(value) -> str:
    return html.escape(str(value), quote=False)


def _format_bool(value: bool | None) -> str:
    return "Да" if value else "Нет"


def moderation_keyboard(carrier_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"carrier_moderation:approve:{carrier_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"carrier_moderation:reject:{carrier_id}",
                ),
            ],
        ],
    )


def build_admin_moderation_text(*, carrier, vehicles, data: dict, telegram_user) -> str:
    username = telegram_user.username if telegram_user and telegram_user.username else None
    telegram_line = f"@{_safe(username)}" if username else "username не указан"

    vehicle_lines = []
    for index, vehicle in enumerate(vehicles, start=1):
        vehicle_lines.append(
            f"{index}) {_safe(vehicle.vehicle_type)} — "
            f"{_safe(vehicle.volume_m3 or 'не указано')} м³ — "
            f"{_safe(vehicle.payload_kg or 'не указано')} кг\n"
            f"   Гидроборт: {_format_bool(vehicle.has_tail_lift)}\n"
            f"   Кран: {_format_bool(vehicle.has_crane)}\n"
            f"   Мобильный лифт: {_format_bool(vehicle.has_mobile_lift)}\n"
            f"   Макс. этаж мобильного лифта: {_safe(vehicle.mobile_lift_max_floor or 'не указано')}\n"
            f"   Макс. вес мобильного лифта: {_safe(vehicle.mobile_lift_max_weight_kg or 'не указано')} кг\n"
            f"   Макс. вес крана: {_safe(vehicle.crane_max_weight_kg or 'не указано')} кг\n"
            f"   Вылет стрелы крана: {_safe(vehicle.crane_reach_meters or 'не указано')} м\n"
            f"   Макс. грузчиков: {_safe(vehicle.max_loaders or 'не указано')}"
        )

    vehicles_text = "\n\n".join(vehicle_lines) if vehicle_lines else "не указаны"

    return (
        f"<b>🚚 Новая анкета перевозчика</b>\n\n"
        f"<b>Компания</b>\n{_safe(carrier.company_name)}\n\n"
        f"<b>Контакт</b>\n{_safe(carrier.contact_name or 'не указан')}\n\n"
        f"<b>Телефон</b>\n{_safe(data.get('company_phone') or carrier.phone or 'не указан')}\n\n"
        f"<b>Email</b>\n{_safe(data.get('company_email') or 'не указан')}\n\n"
        f"<b>Регионы</b>\n{_safe(carrier.operating_regions or data.get('operating_regions') or 'не указаны')}\n\n"
        f"<b>Сборка мебели</b>\n{_format_bool(carrier.assembly_required)}\n\n"
        f"<b>Упаковка</b>\n{_format_bool(carrier.packing_required)}\n\n"
        f"<b>Автомобили</b>\n{vehicles_text}\n\n"
        f"<b>Telegram</b>\n{telegram_line}\n"
        f"ID: {_safe(carrier.telegram_user_id or 'не указан')}\n\n"
        f"<b>Статус</b>\nОжидает модерации"
    )


@router.message(
    CarrierOnboardingStates.moderation_review,
    F.text == "Отправить на модерацию",
)
async def submit_carrier_to_moderation(
    message: Message,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    carrier_id = data["carrier_id"]

    async with async_session_maker() as session:
        repository = CarrierRepository(session)
        carrier = await repository.get_carrier_by_id(carrier_id)

        if carrier is None:
            await message.answer(
                "Анкета не найдена. Обратитесь к администратору CargoPT.",
                reply_markup=ReplyKeyboardRemove(),
            )
            await state.clear()
            return

        vehicles = await repository.list_vehicles_by_carrier(carrier_id)

    admin_text = build_admin_moderation_text(
        carrier=carrier,
        vehicles=vehicles,
        data=data,
        telegram_user=message.from_user,
    )

    for admin_id in ADMIN_TELEGRAM_USER_IDS:
        await message.bot.send_message(
            chat_id=admin_id,
            text=admin_text,
            reply_markup=moderation_keyboard(carrier_id),
            parse_mode="HTML",
        )

    await state.clear()

    await message.answer(
        "Анкета отправлена на модерацию.\n\n"
        f"После проверки вы получите уведомление. По вопросам: @{DEFAULT_ADMIN_USERNAME}",
        reply_markup=ReplyKeyboardRemove(),
    )


async def redispatch_open_jobs_to_new_carrier(
    *,
    bot,
    session,
) -> tuple[int, int]:
    job_repository = JobRepository(session)
    carrier_repository = CarrierRepository(session)

    distribution = OfferDistributionService(
        matching_service=JobMatchingService(
            CarrierSearchService(carrier_repository)
        ),
        offer_service=JobOfferService(job_repository),
        job_repository=job_repository,
    )

    stmt = (
        select(Job)
        .where(
            Job.status.in_(
                (
                    "ready_for_matching",
                    "matching",
                    "offered",
                    "manual_review_required",
                    "offers_exhausted",
                    "expired_without_response",
                    "no_carriers_found",
                )
            )
        )
        .order_by(Job.requested_date.is_(None), Job.requested_date, Job.id)
    )
    result = await session.execute(stmt)
    jobs = list(result.scalars().all())

    created_total = 0
    sent_total = 0

    for job in jobs:
        previous_status = job.status

        offers = await distribution.create_offers_for_job(
            job,
            limit=None,
            expires_in_minutes=60,
        )

        if not offers:
            await job_repository.update_job_status(
                job_id=job.id,
                status=previous_status,
                updated_at=job.updated_at,
            )
            continue

        created_total += len(offers)

        sent_total += await send_job_offers_to_carriers(
            bot=bot,
            job=job,
            offers=offers,
            job_repository=job_repository,
            carrier_repository=carrier_repository,
        )

    return created_total, sent_total


def build_carrier_decision_notification(*, approved: bool) -> str:
    if approved:
        return (
            "Ваша анкета CargoPT одобрена.\n\n"
            "Теперь вы участвуете в распределении заказов.\n\n"
            "Когда появится подходящий заказ, бот пришлёт вам предложение "
            "с кнопками «Принять» и «Отказаться».\n\n"
            f"По вопросам: @{DEFAULT_ADMIN_USERNAME}"
        )

    return (
        "Ваша анкета CargoPT не была одобрена.\n\n"
        "Для уточнения деталей свяжитесь с администратором:\n"
        f"@{DEFAULT_ADMIN_USERNAME}"
    )


def build_admin_decision_suffix(*, action: str, moderator_username: str | None) -> str:
    moderator = f"@{moderator_username}" if moderator_username else f"@{DEFAULT_ADMIN_USERNAME}"

    if action == "approve":
        return f"\n\n<b>Статус</b>\n✅ Одобрено\n<b>Модератор</b>\n{_safe(moderator)}"

    return f"\n\n<b>Статус</b>\n❌ Отклонено\n<b>Модератор</b>\n{_safe(moderator)}"


@router.callback_query(F.data.startswith("carrier_moderation:"))
async def carrier_moderation_action(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMIN_TELEGRAM_USER_IDS:
        await callback.answer(
            "Недостаточно прав.",
            show_alert=True,
        )
        return

    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer(
            "Некорректное действие.",
            show_alert=True,
        )
        return

    _, action, raw_carrier_id = parts

    if action not in {"approve", "reject"}:
        await callback.answer(
            "Некорректное действие.",
            show_alert=True,
        )
        return

    try:
        carrier_id = int(raw_carrier_id)
    except ValueError:
        await callback.answer(
            "Некорректный ID анкеты.",
            show_alert=True,
        )
        return

    async with async_session_maker() as session:
        repository = CarrierRepository(session)
        service = CarrierOnboardingService(repository)

        carrier = await repository.get_carrier_by_id(carrier_id)

        if carrier is None:
            await callback.answer(
                "Анкета не найдена.",
                show_alert=True,
            )
            return

        if carrier.status != CarrierStatus.PENDING_MODERATION:
            await callback.answer(
                "Эта анкета уже обработана.",
                show_alert=True,
            )
            return

        redispatch_created = 0
        redispatch_sent = 0

        if action == "approve":
            carrier = await service.approve_carrier(carrier_id)
            approved = True
            redispatch_created, redispatch_sent = await redispatch_open_jobs_to_new_carrier(
                bot=callback.bot,
                session=session,
            )
        else:
            carrier = await service.reject_carrier(carrier_id)
            approved = False

        await session.commit()

    if carrier.telegram_user_id is not None:
        await callback.bot.send_message(
            chat_id=carrier.telegram_user_id,
            text=build_carrier_decision_notification(approved=approved),
        )

    original_text = callback.message.html_text if callback.message else ""
    suffix = build_admin_decision_suffix(
        action=action,
        moderator_username=callback.from_user.username,
    )

    if callback.message:
        await callback.message.edit_text(
            text=original_text + suffix,
            reply_markup=None,
            parse_mode="HTML",
        )

    if approved and redispatch_created:
        await callback.answer(
            f"Анкета одобрена. Новые офферы: {redispatch_created}, отправлено: {redispatch_sent}."
        )
    else:
        await callback.answer(
            "Анкета одобрена." if approved else "Анкета отклонена."
        )
