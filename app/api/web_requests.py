from collections.abc import AsyncIterator

from aiogram import Bot
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.web_request_schemas import WebRequestPayload
from app.api.web_request_schemas import WebRequestResponse
from app.api.web_request_schemas import TrackingOfferSelectResponse
from app.api.web_request_schemas import TrackingOfferResponse
from app.api.web_request_schemas import TrackingJobResponse
from app.api.web_request_schemas import TrackingAssignmentActionResponse
from app.config import settings
from app.db.session import async_session_maker
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.services.assignment_confirmation import build_assignment_status_from_action
from app.services.assignment_confirmation import process_assignment_failure_redispatch
from app.services.assignment_confirmation import record_assignment_confirmation
from app.services.client_offer_presentation import ClientOfferPresentationService
from app.services.job_lifecycle import InvalidJobStatusTransitionError
from app.services.job_offer import ClientOfferSelectionError
from app.services.job_offer import JobOfferService
from app.services.request_intake import RequestIntakeAddress
from app.services.request_intake import RequestIntakeInput
from app.services.request_intake import RequestIntakeItem
from app.services.request_intake import RequestIntakeService


router = APIRouter()


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_api_bot() -> AsyncIterator[Bot]:
    bot = Bot(token=settings.bot_token)
    try:
        yield bot
    finally:
        await bot.session.close()


@router.post("/requests", response_model=WebRequestResponse)
async def submit_web_request(
    payload: WebRequestPayload,
    session: AsyncSession = Depends(get_session),
    bot: Bot = Depends(get_api_bot),
) -> WebRequestResponse:
    service_request = payload.to_service_request()
    service = RequestIntakeService(
        job_repository=JobRepository(session),
        carrier_repository=CarrierRepository(session),
        bot=bot,
    )
    result = await service.submit_web_intake(
        RequestIntakeInput(
            source_locale=service_request.source_locale,
            customer_name=service_request.customer_name,
            customer_email=service_request.customer_email,
            preferred_contact=service_request.preferred_contact,
            client_phone=service_request.client_phone,
            client_whatsapp=service_request.client_whatsapp,
            utm_source=service_request.utm_source,
            utm_campaign=service_request.utm_campaign,
            landing_version=service_request.landing_version,
            requested_date=service_request.requested_date,
            addresses=tuple(
                RequestIntakeAddress(
                    kind=address.kind,
                    raw_text=address.raw_text,
                    floor=address.floor,
                    has_elevator=address.has_elevator,
                )
                for address in service_request.addresses
            ),
            items=tuple(
                RequestIntakeItem(
                    description=item.description,
                    quantity=item.quantity,
                )
                for item in service_request.items
            ),
            needs_assembly=service_request.needs_assembly,
            needs_packing=service_request.needs_packing,
            needs_tail_lift=service_request.needs_tail_lift,
            needs_crane=service_request.needs_crane,
            needs_mobile_lift=service_request.needs_mobile_lift,
            required_loaders=service_request.required_loaders,
            estimated_payload_kg=service_request.estimated_payload_kg,
            estimated_volume_m3=service_request.estimated_volume_m3,
            comment=service_request.comment,
        )
    )

    if result.job.id is None:
        raise RuntimeError("web request job id missing")

    if result.job.tracking_token is None:
        raise RuntimeError("web request tracking token missing")

    return WebRequestResponse(
        job_id=result.job.id,
        status=str(result.job.status),
        tracking_token=result.job.tracking_token,
        tracking_url=f"/track/{result.job.tracking_token}",
        offers_count=result.offers_count,
        sent_count=result.sent_count,
    )


@router.get("/track/{tracking_token}", response_model=TrackingJobResponse)
async def get_tracking_job(
    tracking_token: str,
    session: AsyncSession = Depends(get_session),
) -> TrackingJobResponse:
    job_repository = JobRepository(session)
    carrier_repository = CarrierRepository(session)

    job = await job_repository.get_job_by_tracking_token(tracking_token)
    if job is None:
        raise HTTPException(status_code=404, detail="tracking job not found")

    presentation = ClientOfferPresentationService(
        job_repository=job_repository,
        carrier_repository=carrier_repository,
    )
    accepted_offer_views = await presentation.list_accepted_offer_views(job.id)

    return TrackingJobResponse(
        job_id=job.id,
        status=str(job.status),
        tracking_token=job.tracking_token,
        client_confirmation_status=job.client_confirmation_status,
        carrier_confirmation_status=job.carrier_confirmation_status,
        accepted_offers=[
            TrackingOfferResponse(
                offer_id=view.offer_id,
                company_name=view.company_name,
                contact_name=view.contact_name,
                phone=view.phone,
                telegram_username=view.telegram_username,
                vehicle_type=view.vehicle_type,
                payload_kg=view.payload_kg,
                volume_m3=view.volume_m3,
                max_loaders=view.max_loaders,
                has_tail_lift=view.has_tail_lift,
                has_crane=view.has_crane,
                has_mobile_lift=view.has_mobile_lift,
                carrier_note=view.carrier_note,
                price_cents=view.price_cents,
            )
            for view in accepted_offer_views
        ],
    )


@router.post(
    "/track/{tracking_token}/offers/{offer_id}/select",
    response_model=TrackingOfferSelectResponse,
)
async def select_tracking_offer(
    tracking_token: str,
    offer_id: int,
    session: AsyncSession = Depends(get_session),
) -> TrackingOfferSelectResponse:
    job_repository = JobRepository(session)
    job = await job_repository.get_job_by_tracking_token(tracking_token)
    if job is None:
        raise HTTPException(status_code=404, detail="tracking job not found")

    service = JobOfferService(job_repository)

    try:
        selected_offer = await service.select_accepted_offer_for_client(
            job_id=job.id,
            offer_id=offer_id,
        )
    except ClientOfferSelectionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    updated_job = await job_repository.get_job_by_id(job.id)
    if updated_job is None:
        raise HTTPException(status_code=404, detail="tracking job not found")

    return TrackingOfferSelectResponse(
        job_id=updated_job.id,
        status=str(updated_job.status),
        selected_offer_id=selected_offer.id,
    )


@router.post(
    "/track/{tracking_token}/assignment/{action}",
    response_model=TrackingAssignmentActionResponse,
)
async def confirm_tracking_assignment(
    tracking_token: str,
    action: str,
    session: AsyncSession = Depends(get_session),
    bot: Bot = Depends(get_api_bot),
) -> TrackingAssignmentActionResponse:
    if action not in {"confirm", "fail"}:
        raise HTTPException(status_code=400, detail="invalid assignment action")

    job_repository = JobRepository(session)
    carrier_repository = CarrierRepository(session)

    job = await job_repository.get_job_by_tracking_token(tracking_token)
    if job is None:
        raise HTTPException(status_code=404, detail="tracking job not found")

    accepted_offer = await job_repository.get_accepted_offer_by_job_id(job.id)
    confirmation_status = build_assignment_status_from_action(action)

    try:
        updated_job = await record_assignment_confirmation(
            job_repository,
            job_id=job.id,
            actor="client",
            status=confirmation_status,
        )
    except InvalidJobStatusTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if action == "fail":
        await process_assignment_failure_redispatch(
            bot=bot,
            job=updated_job,
            accepted_offer=accepted_offer,
            job_repository=job_repository,
            carrier_repository=carrier_repository,
        )

    return TrackingAssignmentActionResponse(
        job_id=updated_job.id,
        status=str(updated_job.status),
        client_confirmation_status=updated_job.client_confirmation_status,
        carrier_confirmation_status=updated_job.carrier_confirmation_status,
    )
