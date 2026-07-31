from datetime import UTC
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.carrier import AdminInviteToken
from app.models.carrier import CarrierCompany
from app.models.carrier import CarrierVehicle
from app.domain.carrier_status import CarrierStatus


class CarrierRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_carrier(self, carrier: CarrierCompany) -> CarrierCompany:
        self.session.add(carrier)
        await self.session.flush()
        return carrier

    async def get_carrier_by_id(self, carrier_id: int) -> CarrierCompany | None:
        stmt = select(CarrierCompany).where(CarrierCompany.id == carrier_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


    async def get_carrier_by_username(
        self,
        username: str,
    ) -> CarrierCompany | None:
        cleaned = username.strip().lstrip("@").lower()

        stmt = (
            select(CarrierCompany)
            .where(CarrierCompany.telegram_username.is_not(None))
            .where(CarrierCompany.telegram_username.ilike(cleaned))
            .where(CarrierCompany.status != CarrierStatus.REJECTED)
            .order_by(CarrierCompany.id.desc())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        carrier = result.scalars().first()

        if carrier is not None:
            return carrier

        company_stmt = (
            select(CarrierCompany)
            .where(CarrierCompany.company_name.ilike(f"@{cleaned}"))
            .where(CarrierCompany.status != CarrierStatus.REJECTED)
            .order_by(CarrierCompany.id.desc())
            .limit(1)
        )

        company_result = await self.session.execute(company_stmt)
        return company_result.scalars().first()

    async def get_latest_carrier_by_company_name(
        self,
        company_name: str,
    ) -> CarrierCompany | None:
        cleaned = company_name.strip().lower()

        stmt = (
            select(CarrierCompany)
            .where(CarrierCompany.company_name.ilike(cleaned))
            .order_by(CarrierCompany.id.desc())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def reset_carrier_for_reinvite(
        self,
        carrier_id: int,
        *,
        updated_at,
    ) -> CarrierCompany:
        carrier = await self.get_carrier_by_id(carrier_id)

        if carrier is None:
            raise ValueError("carrier not found")

        carrier.telegram_user_id = None
        carrier.telegram_username = None
        carrier.status = CarrierStatus.INVITED
        carrier.paid_until = None
        carrier.assembly_required = False
        carrier.packing_required = False
        carrier.operating_regions = None
        carrier.public_name = None
        carrier.experience_since_year = None
        carrier.logo_file_name = None
        carrier.publication_consent_at = None
        carrier.public_profile_requested_at = None
        carrier.profile_completed_at = None
        carrier.current_profile_step = None
        carrier.updated_at = updated_at

        await self.session.flush()
        return carrier

    async def update_public_name(
        self,
        carrier_id: int,
        public_name: str,
    ) -> CarrierCompany:
        carrier = await self.get_carrier_by_id(carrier_id)
        if carrier is None:
            raise ValueError("carrier not found")
        carrier.public_name = public_name
        carrier.updated_at = datetime.now(UTC)
        await self.session.flush()
        return carrier

    async def update_experience_since_year(
        self,
        carrier_id: int,
        experience_since_year: int,
    ) -> CarrierCompany:
        carrier = await self.get_carrier_by_id(carrier_id)
        if carrier is None:
            raise ValueError("carrier not found")
        carrier.experience_since_year = experience_since_year
        carrier.updated_at = datetime.now(UTC)
        await self.session.flush()
        return carrier

    async def update_logo_file_name(
        self,
        carrier_id: int,
        logo_file_name: str,
    ) -> CarrierCompany:
        carrier = await self.get_carrier_by_id(carrier_id)
        if carrier is None:
            raise ValueError("carrier not found")
        carrier.logo_file_name = logo_file_name
        carrier.updated_at = datetime.now(UTC)
        await self.session.flush()
        return carrier

    async def record_publication_consent(
        self,
        carrier_id: int,
        consented_at,
    ) -> CarrierCompany:
        carrier = await self.get_carrier_by_id(carrier_id)
        if carrier is None:
            raise ValueError("carrier not found")
        carrier.publication_consent_at = consented_at
        carrier.updated_at = datetime.now(UTC)
        await self.session.flush()
        return carrier

    async def update_operating_regions(
        self,
        carrier_id: int,
        operating_regions: str,
    ) -> CarrierCompany:
        carrier = await self.get_carrier_by_id(carrier_id)
        if carrier is None:
            raise ValueError("carrier not found")
        carrier.operating_regions = operating_regions
        carrier.updated_at = datetime.now(UTC)
        await self.session.flush()
        return carrier

    async def get_carrier_by_telegram_user_id(
        self,
        telegram_user_id: int,
    ) -> CarrierCompany | None:
        stmt = select(CarrierCompany).where(
            CarrierCompany.telegram_user_id == telegram_user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_carrier_telegram_username(
        self,
        carrier_id: int,
        username: str | None,
    ) -> CarrierCompany:
        carrier = await self.get_carrier_by_id(carrier_id)

        if carrier is None:
            raise ValueError("carrier not found")

        carrier.telegram_username = username
        await self.session.flush()

        return carrier

    async def bind_carrier_telegram_identity(
        self,
        carrier_id: int,
        *,
        telegram_user_id: int,
        telegram_username: str,
    ) -> CarrierCompany:
        carrier = await self.get_carrier_by_id(carrier_id)
        if carrier is None:
            raise ValueError("carrier not found")
        if carrier.telegram_user_id not in (None, telegram_user_id):
            raise ValueError("carrier already bound to another telegram user")
        carrier.telegram_user_id = telegram_user_id
        carrier.telegram_username = telegram_username
        carrier.updated_at = datetime.now(UTC)
        await self.session.flush()
        return carrier

    async def list_subscription_reminder_candidates(
        self,
        *,
        now,
        until,
    ) -> list[CarrierCompany]:
        stmt = (
            select(CarrierCompany)
            .where(CarrierCompany.status == CarrierStatus.ACTIVE)
            .where(CarrierCompany.telegram_user_id.is_not(None))
            .where(CarrierCompany.paid_until.is_not(None))
            .where(CarrierCompany.paid_until <= until)
            .order_by(CarrierCompany.paid_until, CarrierCompany.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_public_profile_request_candidates(self) -> list[CarrierCompany]:
        stmt = (
            select(CarrierCompany)
            .where(CarrierCompany.status == CarrierStatus.ACTIVE)
            .where(CarrierCompany.telegram_user_id.is_not(None))
            .where(CarrierCompany.public_profile_requested_at.is_(None))
            .where(~CarrierCompany.company_name.ilike("TEST %"))
            .where(
                or_(
                    CarrierCompany.public_name.is_(None),
                    CarrierCompany.experience_since_year.is_(None),
                    CarrierCompany.logo_file_name.is_(None),
                    CarrierCompany.publication_consent_at.is_(None),
                    CarrierCompany.operating_regions.is_(None),
                )
            )
            .order_by(CarrierCompany.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_public_profile_requested(
        self,
        carrier_id: int,
        requested_at,
    ) -> CarrierCompany:
        carrier = await self.get_carrier_by_id(carrier_id)
        if carrier is None:
            raise ValueError("carrier not found")
        carrier.public_profile_requested_at = requested_at
        carrier.updated_at = requested_at
        await self.session.flush()
        return carrier

    async def mark_subscription_reminder_sent(
        self,
        *,
        carrier_id: int,
        marker: str,
        updated_at,
    ) -> CarrierCompany:
        carrier = await self.get_carrier_by_id(carrier_id)

        if carrier is None:
            raise ValueError("carrier not found")

        previous_note = carrier.internal_note or ""
        if marker not in previous_note:
            carrier.internal_note = (previous_note + "\n" if previous_note else "") + marker

        carrier.updated_at = updated_at
        await self.session.flush()

        return carrier


    async def create_invite_token(
        self,
        invite: AdminInviteToken,
    ) -> AdminInviteToken:
        self.session.add(invite)
        await self.session.flush()
        return invite

    async def get_invite_token(
        self,
        token: str,
    ) -> AdminInviteToken | None:
        stmt = select(AdminInviteToken).where(
            AdminInviteToken.token == token
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_carrier_status(
        self,
        carrier_id: int,
        status: str,
    ) -> CarrierCompany:
        carrier = await self.get_carrier_by_id(carrier_id)

        if carrier is None:
            raise ValueError("carrier not found")

        carrier.status = status
        await self.session.flush()

        return carrier

    async def claim_invite(
        self,
        token: str,
        telegram_user_id: int,
        used_at,
        telegram_username: str | None = None,
    ) -> AdminInviteToken:
        invite = await self.get_invite_token(token)

        if invite is None:
            raise ValueError("invite not found")

        carrier = await self.get_carrier_by_id(invite.carrier_id)

        if carrier is None:
            raise ValueError("carrier not found")

        invite.used_at = used_at
        invite.used_by_telegram_id = telegram_user_id
        invite.status = "used"

        carrier.telegram_user_id = telegram_user_id
        carrier.telegram_username = telegram_username
        carrier.status = CarrierStatus.INVITED

        await self.session.flush()

        return invite

    async def complete_profile(
        self,
        carrier_id: int,
        assembly_required: bool,
        packing_required: bool,
        operating_regions: str,
        completed_at,
    ) -> CarrierCompany:
        carrier = await self.get_carrier_by_id(carrier_id)

        if carrier is None:
            raise ValueError("carrier not found")

        carrier.assembly_required = assembly_required
        carrier.packing_required = packing_required
        carrier.operating_regions = operating_regions
        carrier.profile_completed_at = completed_at
        carrier.status = CarrierStatus.PENDING_MODERATION
        carrier.current_profile_step = "completed"

        await self.session.flush()

        return carrier


    async def update_profile_step(
        self,
        carrier_id: int,
        step: str,
    ) -> CarrierCompany:
        carrier = await self.get_carrier_by_id(carrier_id)

        if carrier is None:
            raise ValueError("carrier not found")

        carrier.current_profile_step = step

        await self.session.flush()

        
        return carrier

    async def update_assembly_required(
        self,
        carrier_id: int,
        value: bool,
    ) -> CarrierCompany:
        carrier = await self.get_carrier_by_id(carrier_id)
        if carrier is None:
            raise ValueError("carrier not found")
        carrier.assembly_required = value
        await self.session.flush()
        return carrier

    async def update_packing_required(
        self,
        carrier_id: int,
        value: bool,
    ) -> CarrierCompany:
        carrier = await self.get_carrier_by_id(carrier_id)
        if carrier is None:
            raise ValueError("carrier not found")
        carrier.packing_required = value
        await self.session.flush()
        return carrier

    async def suspend_carrier(
        self,
        carrier_id: int,
    ) -> CarrierCompany:
        carrier = await self.get_carrier_by_id(carrier_id)

        if carrier is None:
            raise ValueError("carrier not found")

        carrier.status = CarrierStatus.SUSPENDED
        await self.session.flush()

        return carrier

    async def unsuspend_carrier(
        self,
        carrier_id: int,
    ) -> CarrierCompany:
        carrier = await self.get_carrier_by_id(carrier_id)

        if carrier is None:
            raise ValueError("carrier not found")

        carrier.status = CarrierStatus.ACTIVE
        await self.session.flush()

        return carrier

    async def approve_carrier(
        self,
        carrier_id: int,
    ) -> CarrierCompany:
        carrier = await self.get_carrier_by_id(carrier_id)

        if carrier is None:
            raise ValueError("carrier not found")

        carrier.status = CarrierStatus.ACTIVE

        await self.session.flush()

        return carrier

    async def reject_carrier(
        self,
        carrier_id: int,
    ) -> CarrierCompany:
        carrier = await self.get_carrier_by_id(carrier_id)

        if carrier is None:
            raise ValueError("carrier not found")

        carrier.status = CarrierStatus.REJECTED

        await self.session.flush()

        return carrier

    async def create_vehicle(
        self,
        vehicle: CarrierVehicle,
    ) -> CarrierVehicle:
        self.session.add(vehicle)
        await self.session.flush()
        return vehicle

    async def list_vehicles_by_carrier(
        self,
        carrier_id: int,
    ) -> list[CarrierVehicle]:
        stmt = (
            select(CarrierVehicle)
            .where(CarrierVehicle.carrier_id == carrier_id)
            .order_by(CarrierVehicle.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_vehicle_by_id(
        self,
        vehicle_id: int,
    ) -> CarrierVehicle | None:
        stmt = select(CarrierVehicle).where(CarrierVehicle.id == vehicle_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_available_vehicles(
        self,
        *,
        min_payload_kg: int | None = None,
        min_volume_m3: float | None = None,
        min_loaders: int | None = None,
        needs_tail_lift: bool = False,
        needs_crane: bool = False,
        needs_mobile_lift: bool = False,
        needs_assembly: bool = False,
        needs_packing: bool = False,
        regions: list[str] | None = None,
    ) -> list[CarrierVehicle]:
        now = datetime.now(UTC)

        stmt = (
            select(CarrierVehicle)
            .join(CarrierCompany)
            .where(CarrierVehicle.is_active.is_(True))
            .where(CarrierCompany.status == CarrierStatus.ACTIVE)
            .where(CarrierCompany.paid_until.is_not(None))
            .where(CarrierCompany.paid_until >= now)
        )

        if min_payload_kg is not None:
            stmt = stmt.where(CarrierVehicle.payload_kg >= min_payload_kg)

        if min_volume_m3 is not None:
            stmt = stmt.where(CarrierVehicle.volume_m3 >= min_volume_m3)

        if min_loaders is not None:
            stmt = stmt.where(CarrierVehicle.max_loaders >= min_loaders)

        if needs_assembly:
            stmt = stmt.where(CarrierCompany.assembly_required.is_(True))

        if needs_packing:
            stmt = stmt.where(CarrierCompany.packing_required.is_(True))

        if regions and "all_portugal" not in regions:
            region_conditions = [
                CarrierCompany.operating_regions == "all_portugal",
            ]
            for region in regions:
                region_conditions.append(CarrierCompany.operating_regions.like(f"%{region}%"))
            from sqlalchemy import or_
            stmt = stmt.where(or_(*region_conditions))

        if needs_tail_lift:
            stmt = stmt.where(CarrierVehicle.has_tail_lift.is_(True))

        if needs_crane:
            stmt = stmt.where(CarrierVehicle.has_crane.is_(True))

        if needs_mobile_lift:
            stmt = stmt.where(CarrierVehicle.has_mobile_lift.is_(True))

        stmt = stmt.order_by(
            CarrierVehicle.payload_kg,
            CarrierVehicle.volume_m3,
            CarrierVehicle.id,
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_carrier_by_vehicle_id(
        self,
        vehicle_id: int,
    ) -> CarrierCompany | None:
        stmt = (
            select(CarrierCompany)
            .join(CarrierVehicle)
            .where(CarrierVehicle.id == vehicle_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
