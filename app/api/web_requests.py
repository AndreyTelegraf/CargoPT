from collections.abc import AsyncIterator
from datetime import UTC
from datetime import datetime

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.web_request_schemas import AcquisitionEventPayload
from app.api.web_request_schemas import WebRequestPayload
from app.api.web_request_schemas import WebRequestResponse
from app.api.web_request_schemas import LocationSuggestionResponse
from app.api.web_request_schemas import TrackingOfferSelectResponse
from app.api.web_request_schemas import TrackingOfferResponse
from app.api.web_request_schemas import TrackingJobResponse
from app.api.web_request_schemas import TrackingAssignmentActionResponse
from app.api.web_request_schemas import TrackingCompletionActionResponse
from app.services.assignment_notifications import send_assignment_confirmation_requests
from app.services.assignment_notifications import send_assignment_final_notifications
from app.config import settings
from app.db.session import async_session_maker
from app.domain.job_status import JobStatus
from app.domain.carrier_status import CarrierStatus
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.repositories.job_email_notification import (
    JobEmailNotificationRepository,
)
from app.services.acquisition_funnel import record_acquisition_event
from app.services.assignment_confirmation import build_assignment_status_from_action
from app.services.assignment_confirmation import process_assignment_failure_redispatch
from app.services.assignment_confirmation import record_assignment_confirmation
from app.services.client_offer_presentation import ClientOfferPresentationService
from app.services.carrier_public_profile import carrier_logo_path
from app.services.email.notification_service import EmailNotificationService
from app.services.job_lifecycle import InvalidJobStatusTransitionError
from app.services.job_completion import COMPLETION_CONFIRMED
from app.services.job_completion import COMPLETION_PROBLEM
from app.services.job_completion import notify_job_control_about_completion_problem
from app.services.job_completion import record_completion_response
from app.services.job_completion import send_completion_result_notifications
from app.services.job_offer import ClientOfferSelectionError
from app.services.job_offer import JobOfferService
from app.services.request_intake import RequestIntakeAddress
from app.services.request_intake import RequestIntakeInput
from app.services.request_intake import RequestIntakeItem
from app.services.request_intake import RequestIntakeService
from app.services.request_intake import WebRequestRateLimitError
from app.services.short_lead_time_warning import has_short_lead_time
from app.services.location_normalization import search_location_suggestions
from app.services.tracking_url import build_tracking_path


router = APIRouter()


@router.get(
    "/locations/search",
    response_model=list[LocationSuggestionResponse],
)
async def search_locations(
    q: str = Query(min_length=3, max_length=120),
    locale: str = Query(default="pt", pattern="^(pt|en|ru)$"),
    limit: int = Query(default=5, ge=1, le=5),
) -> list[LocationSuggestionResponse]:
    suggestions = await search_location_suggestions(
        q,
        locale=locale,
        limit=limit,
        provider_url=settings.location_search_provider_url,
    )
    return [
        LocationSuggestionResponse(
            display_name=item.display_name,
            latitude=item.latitude,
            longitude=item.longitude,
            map_url=item.map_url,
            country_code=item.country_code,
            postal_code=item.postal_code,
            address_details_hint=item.address_details_hint,
        )
        for item in suggestions
    ]


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@router.post("/acquisition-events", status_code=204)
async def acquisition_event(
    payload: AcquisitionEventPayload,
    session: AsyncSession = Depends(get_session),
) -> Response:
    await record_acquisition_event(session, payload)
    return Response(status_code=204)


@router.get(
    "/carriers/{carrier_id}/logo",
    response_class=FileResponse,
    include_in_schema=False,
)
async def get_carrier_logo(
    carrier_id: int,
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    carrier = await CarrierRepository(session).get_carrier_by_id(carrier_id)
    if (
        carrier is None
        or carrier.status != CarrierStatus.ACTIVE
        or carrier.publication_consent_at is None
    ):
        raise HTTPException(status_code=404, detail="carrier logo not found")
    path = carrier_logo_path(carrier.logo_file_name)
    if path is None:
        raise HTTPException(status_code=404, detail="carrier logo not found")
    return FileResponse(
        path,
        headers={"Cache-Control": "public, max-age=3600"},
    )



def _format_tracking_route_summary(job) -> str | None:
    addresses = list(getattr(job, "addresses", []) or [])
    pickup = next((a for a in addresses if a.kind == "pickup"), None)
    delivery = next((a for a in addresses if a.kind == "delivery"), None)

    def label(address) -> str | None:
        if address is None:
            return None
        return address.city or address.normalized_address or address.raw_text

    pickup_label = label(pickup)
    delivery_label = label(delivery)

    if pickup_label and delivery_label:
        return f"{pickup_label} → {delivery_label}"
    if pickup_label:
        return pickup_label
    if delivery_label:
        return delivery_label
    return None


async def get_api_bot() -> AsyncIterator[object]:
    from aiogram import Bot

    bot = Bot(token=settings.bot_token)
    try:
        yield bot
    finally:
        await bot.session.close()


@router.post("/requests", response_model=WebRequestResponse)
async def submit_web_request(
    payload: WebRequestPayload,
    session: AsyncSession = Depends(get_session),
    bot=Depends(get_api_bot),
) -> WebRequestResponse:
    service_request = payload.to_service_request()
    service = RequestIntakeService(
        job_repository=JobRepository(session),
        carrier_repository=CarrierRepository(session),
        bot=bot,
        email_notification_service=EmailNotificationService(
            JobEmailNotificationRepository(session),
            enabled=settings.email_enabled,
        ),
    )
    try:
        result = await service.submit_web_intake(
            RequestIntakeInput(
                source_locale=service_request.source_locale,
                customer_name=service_request.customer_name,
                customer_email=service_request.customer_email,
                preferred_contact=service_request.preferred_contact,
                client_phone=service_request.client_phone,
                client_whatsapp=service_request.client_whatsapp,
                utm_source=service_request.utm_source,
                utm_medium=service_request.utm_medium,
                utm_campaign=service_request.utm_campaign,
                utm_content=service_request.utm_content,
                referrer_host=service_request.referrer_host,
                fbclid=service_request.fbclid,
                landing_version=service_request.landing_version,
                requested_date=service_request.requested_date,
                addresses=tuple(
                    RequestIntakeAddress(
                        kind=address.kind,
                        raw_text=address.raw_text,
                        normalized_address=address.normalized_address,
                        latitude=address.latitude,
                        longitude=address.longitude,
                        country_code=address.country_code,
                        address_details=address.address_details,
                        postal_code=address.postal_code,
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
    except WebRequestRateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail="too many requests for this contact",
            headers={"Retry-After": "86400"},
        ) from exc

    if result.job.id is None:
        raise RuntimeError("web request job id missing")

    if result.job.tracking_token is None:
        raise RuntimeError("web request tracking token missing")

    return WebRequestResponse(
        job_id=result.job.id,
        status=str(result.job.status),
        tracking_token=result.job.tracking_token,
        tracking_url=build_tracking_path(
            result.job.source_locale,
            result.job.tracking_token,
        ),
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

    cancelled_from_status = None

    if str(job.status) == "cancelled":
        cancelled_from_status = (
            await job_repository.get_cancelled_from_status(
                job.id
            )
        )

    return TrackingJobResponse(
        job_id=job.id,
        status=str(job.status),
        cancelled_from_status=cancelled_from_status,
        short_lead_time_warning=has_short_lead_time(job.requested_date),
        tracking_token=job.tracking_token,
        route_summary=_format_tracking_route_summary(job),
        client_confirmation_status=job.client_confirmation_status,
        carrier_confirmation_status=job.carrier_confirmation_status,
        completion_prompted_at=job.completion_prompted_at,
        client_completion_status=job.client_completion_status,
        carrier_completion_status=job.carrier_completion_status,
        accepted_offers=[
            TrackingOfferResponse(
                offer_id=view.offer_id,
                company_name=view.company_name,
                operating_regions=view.operating_regions,
                experience_since_year=view.experience_since_year,
                logo_url=(
                    f"/api/v1/carriers/{view.carrier_id}/logo"
                    if view.logo_file_name
                    else None
                ),
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
    bot=Depends(get_api_bot),
) -> TrackingOfferSelectResponse:
    job_repository = JobRepository(session)
    carrier_repository = CarrierRepository(session)

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

    selected_carrier = await carrier_repository.get_carrier_by_id(
        selected_offer.carrier_id
    )
    carrier_telegram_user_id = (
        selected_carrier.telegram_user_id
        if selected_carrier is not None
        else None
    )

    await send_assignment_confirmation_requests(
        bot=bot,
        job=updated_job,
        carrier_telegram_user_id=carrier_telegram_user_id,
    )

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
    bot=Depends(get_api_bot),
) -> TrackingAssignmentActionResponse:
    if action not in {"confirm", "fail"}:
        raise HTTPException(status_code=400, detail="invalid assignment action")

    job_repository = JobRepository(session)
    carrier_repository = CarrierRepository(session)

    job = await job_repository.get_job_by_tracking_token(tracking_token)
    if job is None:
        raise HTTPException(status_code=404, detail="tracking job not found")

    accepted_offer = await job_repository.get_accepted_offer_by_job_id(job.id)

    if action == "fail" and job.status == JobStatus.ASSIGNED:
        now = datetime.now(UTC)
        accepted_offer = await job_repository.cancel_accepted_offer_by_job(
            job_id=job.id,
            cancelled_at=now,
        )
        await job_repository.clear_assignment_confirmation_statuses(
            job_id=job.id,
            updated_at=now,
        )
        updated_job = await job_repository.update_job_status(
            job_id=job.id,
            status=JobStatus.READY_FOR_MATCHING,
            updated_at=now,
        )
    else:
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

    await send_assignment_final_notifications(
        bot=bot,
        job=updated_job,
        accepted_offer=accepted_offer,
        carrier_repository=carrier_repository,
    )

    return TrackingAssignmentActionResponse(
        job_id=updated_job.id,
        status=str(updated_job.status),
        client_confirmation_status=updated_job.client_confirmation_status,
        carrier_confirmation_status=updated_job.carrier_confirmation_status,
    )


@router.post(
    "/track/{tracking_token}/completion/{action}",
    response_model=TrackingCompletionActionResponse,
)
async def confirm_tracking_completion(
    tracking_token: str,
    action: str,
    session: AsyncSession = Depends(get_session),
    bot=Depends(get_api_bot),
) -> TrackingCompletionActionResponse:
    if action not in {"confirm", "problem"}:
        raise HTTPException(status_code=400, detail="invalid completion action")

    job_repository = JobRepository(session)
    carrier_repository = CarrierRepository(session)
    job = await job_repository.get_job_by_tracking_token(tracking_token)
    if job is None:
        raise HTTPException(status_code=404, detail="tracking job not found")

    accepted_offer = await job_repository.get_accepted_offer_by_job_id(job.id)
    completion_status = (
        COMPLETION_CONFIRMED if action == "confirm" else COMPLETION_PROBLEM
    )
    try:
        updated_job = await record_completion_response(
            job_repository,
            job_id=job.id,
            actor="client",
            status=completion_status,
        )
    except InvalidJobStatusTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if completion_status == COMPLETION_PROBLEM:
        await notify_job_control_about_completion_problem(
            bot=bot,
            job=updated_job,
            actor="client",
        )

    await send_completion_result_notifications(
        bot=bot,
        job=updated_job,
        accepted_offer=accepted_offer,
        carrier_repository=carrier_repository,
    )

    return TrackingCompletionActionResponse(
        job_id=updated_job.id,
        status=str(updated_job.status),
        client_completion_status=updated_job.client_completion_status,
        carrier_completion_status=updated_job.carrier_completion_status,
    )
