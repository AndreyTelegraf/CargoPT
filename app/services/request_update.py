from datetime import UTC
from datetime import datetime

from app.models.job import Job
from app.models.job import JobAddress
from app.models.job import JobItem
from app.models.job import JobMedia
from app.domain.requested_date import validate_requested_date_not_in_past
from app.repositories.job import JobRepository
from app.services.location_normalization import build_google_maps_coordinate_url
from app.services.location_normalization import extract_postal_code
from app.services.location_normalization import normalize_text_location_resolved


class RequestUpdateService:
    def __init__(self, *, job_repository: JobRepository) -> None:
        self.job_repository = job_repository

    async def add_address(
        self,
        *,
        job_id: int,
        kind: str,
        raw_text: str,
        normalized_address: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        country_code: str | None = None,
        address_details: str | None = None,
        postal_code: str | None = None,
    ) -> JobAddress:
        if latitude is not None and longitude is not None:
            clean_raw_text = raw_text.strip() or f"{latitude}, {longitude}"
            clean_normalized_address = (
                (normalized_address or "").strip() or clean_raw_text
            )
            normalized_location = {
                "raw_text": clean_raw_text,
                "original_google_maps_url": None,
                "normalized_address": clean_normalized_address,
                "postal_code": extract_postal_code(clean_normalized_address),
                "latitude": latitude,
                "longitude": longitude,
                "map_url": build_google_maps_coordinate_url(latitude, longitude),
            }
        else:
            normalized_location = await normalize_text_location_resolved(raw_text)

        address = JobAddress(
            job_id=job_id,
            kind=kind,
            raw_text=normalized_location["raw_text"],
            original_google_maps_url=normalized_location["original_google_maps_url"],
            normalized_address=normalized_location["normalized_address"],
            city=None,
            postal_code=(postal_code or "").strip() or normalized_location["postal_code"],
            country_code=(country_code or "").strip().lower() or None,
            address_details=(address_details or "").strip() or None,
            floor=None,
            has_elevator=None,
            latitude=normalized_location["latitude"],
            longitude=normalized_location["longitude"],
            map_url=normalized_location["map_url"],
            created_at=datetime.now(UTC),
        )

        return await self.job_repository.add_address(address)

    async def update_address_details(
        self,
        *,
        address_id: int,
        floor: int | None,
        has_elevator: bool | None,
    ) -> JobAddress:
        return await self.job_repository.update_address_details(
            address_id=address_id,
            floor=floor,
            has_elevator=has_elevator,
        )

    async def add_item(
        self,
        *,
        job_id: int,
        description: str,
        quantity: int | None = None,
    ) -> JobItem:
        item = JobItem(
            job_id=job_id,
            description=description,
            quantity=quantity,
            estimated_weight_kg=None,
            estimated_volume_m3=None,
            created_at=datetime.now(UTC),
        )

        return await self.job_repository.add_item(item)

    async def update_estimated_payload(
        self,
        *,
        job_id: int,
        estimated_payload_kg: int | None,
    ) -> Job:
        return await self.job_repository.update_estimated_payload(
            job_id=job_id,
            estimated_payload_kg=estimated_payload_kg,
            updated_at=datetime.now(UTC),
        )

    async def update_estimated_volume(
        self,
        *,
        job_id: int,
        estimated_volume_m3: float | None,
    ) -> Job:
        return await self.job_repository.update_estimated_volume(
            job_id=job_id,
            estimated_volume_m3=estimated_volume_m3,
            updated_at=datetime.now(UTC),
        )

    async def update_required_loaders(
        self,
        *,
        job_id: int,
        required_loaders: int | None,
    ) -> Job:
        return await self.job_repository.update_required_loaders(
            job_id=job_id,
            required_loaders=required_loaders,
            updated_at=datetime.now(UTC),
        )

    async def update_needs_assembly(
        self,
        *,
        job_id: int,
        needs_assembly: bool,
    ) -> Job:
        return await self.job_repository.update_needs_assembly(
            job_id=job_id,
            needs_assembly=needs_assembly,
            updated_at=datetime.now(UTC),
        )

    async def update_needs_packing(
        self,
        *,
        job_id: int,
        needs_packing: bool,
    ) -> Job:
        return await self.job_repository.update_needs_packing(
            job_id=job_id,
            needs_packing=needs_packing,
            updated_at=datetime.now(UTC),
        )

    async def update_needs_tail_lift(
        self,
        *,
        job_id: int,
        needs_tail_lift: bool,
    ) -> Job:
        return await self.job_repository.update_needs_tail_lift(
            job_id=job_id,
            needs_tail_lift=needs_tail_lift,
            updated_at=datetime.now(UTC),
        )

    async def update_needs_crane(
        self,
        *,
        job_id: int,
        needs_crane: bool,
    ) -> Job:
        return await self.job_repository.update_needs_crane(
            job_id=job_id,
            needs_crane=needs_crane,
            updated_at=datetime.now(UTC),
        )

    async def update_needs_mobile_lift(
        self,
        *,
        job_id: int,
        needs_mobile_lift: bool,
    ) -> Job:
        return await self.job_repository.update_needs_mobile_lift(
            job_id=job_id,
            needs_mobile_lift=needs_mobile_lift,
            updated_at=datetime.now(UTC),
        )

    async def update_requested_date(
        self,
        *,
        job_id: int,
        requested_date,
    ) -> Job:
        validate_requested_date_not_in_past(requested_date)
        return await self.job_repository.update_requested_date(
            job_id=job_id,
            requested_date=requested_date,
            updated_at=datetime.now(UTC),
        )

    async def update_client_phone(
        self,
        *,
        job_id: int,
        client_phone: str | None,
    ) -> Job:
        return await self.job_repository.update_client_phone(
            job_id=job_id,
            client_phone=client_phone,
            updated_at=datetime.now(UTC),
        )

    async def update_client_whatsapp(
        self,
        *,
        job_id: int,
        client_whatsapp: str | None,
    ) -> Job:
        return await self.job_repository.update_client_whatsapp(
            job_id=job_id,
            client_whatsapp=client_whatsapp,
            updated_at=datetime.now(UTC),
        )

    async def add_media(
        self,
        *,
        job_id: int,
        telegram_file_id: str,
        media_type: str,
        caption: str | None = None,
    ) -> JobMedia:
        media = JobMedia(
            job_id=job_id,
            media_type=media_type,
            telegram_file_id=telegram_file_id,
            caption=caption,
            created_at=datetime.now(UTC),
        )

        return await self.job_repository.add_media(media)
