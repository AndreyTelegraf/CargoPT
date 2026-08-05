from datetime import UTC
from datetime import datetime
import json

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meta_operations import MetaEventAction
from app.models.meta_operations import MetaInboundEvent
from app.models.meta_operations import MetaSourceGroup


class MetaOperationsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_group_by_external_id(
        self,
        external_id: str,
        *,
        platform: str = "facebook",
    ) -> MetaSourceGroup | None:
        result = await self.session.execute(
            select(MetaSourceGroup).where(
                MetaSourceGroup.platform == platform,
                MetaSourceGroup.external_id == external_id,
            )
        )
        return result.scalar_one_or_none()

    async def find_group_for_text(
        self,
        text: str,
        external_ids: tuple[str, ...] = (),
    ) -> MetaSourceGroup | None:
        for external_id in external_ids:
            group = await self.get_group_by_external_id(external_id)
            if group is not None:
                return group

        lowered = text.casefold()
        result = await self.session.execute(
            select(MetaSourceGroup)
            .where(MetaSourceGroup.enabled.is_(True))
            .order_by(MetaSourceGroup.priority, MetaSourceGroup.id)
        )
        for group in result.scalars():
            if len(group.name) >= 6 and group.name.casefold() in lowered:
                return group
        return None

    async def upsert_group(self, values: dict) -> tuple[MetaSourceGroup, bool]:
        now = datetime.now(UTC)
        existing = await self.get_group_by_external_id(
            values["external_id"],
            platform=values.get("platform", "facebook"),
        )
        if existing is None:
            group = MetaSourceGroup(**values, created_at=now, updated_at=now)
            self.session.add(group)
            await self.session.flush()
            return group, True

        for key, value in values.items():
            if key not in {"id", "created_at"}:
                setattr(existing, key, value)
        existing.updated_at = now
        await self.session.flush()
        return existing, False

    async def get_event(self, event_id: int) -> MetaInboundEvent | None:
        return await self.session.get(MetaInboundEvent, event_id)

    async def get_event_by_dedupe_key(self, dedupe_key: str) -> MetaInboundEvent | None:
        result = await self.session.execute(
            select(MetaInboundEvent).where(MetaInboundEvent.dedupe_key == dedupe_key)
        )
        return result.scalar_one_or_none()

    async def create_event(self, event: MetaInboundEvent) -> tuple[MetaInboundEvent, bool]:
        existing = await self.get_event_by_dedupe_key(event.dedupe_key)
        if existing is not None:
            return existing, False
        try:
            async with self.session.begin_nested():
                self.session.add(event)
                await self.session.flush()
            return event, True
        except IntegrityError:
            existing = await self.get_event_by_dedupe_key(event.dedupe_key)
            if existing is None:
                raise
            return existing, False

    async def list_events(
        self,
        *,
        status: str | None = None,
        classification: str | None = None,
        limit: int = 100,
    ) -> list[tuple[MetaInboundEvent, MetaSourceGroup | None]]:
        statement = (
            select(MetaInboundEvent, MetaSourceGroup)
            .outerjoin(MetaSourceGroup, MetaInboundEvent.source_group_id == MetaSourceGroup.id)
            .order_by(MetaInboundEvent.created_at.desc(), MetaInboundEvent.id.desc())
            .limit(limit)
        )
        if status:
            statement = statement.where(MetaInboundEvent.status == status)
        if classification:
            statement = statement.where(MetaInboundEvent.classification_label == classification)
        result = await self.session.execute(statement)
        return list(result.all())

    async def list_groups(
        self,
        *,
        enabled: bool | None = None,
        limit: int = 1000,
    ) -> list[MetaSourceGroup]:
        statement = select(MetaSourceGroup).order_by(
            MetaSourceGroup.priority,
            MetaSourceGroup.name,
        ).limit(limit)
        if enabled is not None:
            statement = statement.where(MetaSourceGroup.enabled.is_(enabled))
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update_event_status(
        self,
        *,
        event_id: int,
        status: str,
        actor: str,
        details: dict | None = None,
    ) -> MetaInboundEvent:
        event = await self.get_event(event_id)
        if event is None:
            raise ValueError("event not found")
        now = datetime.now(UTC)
        event.status = status
        event.reviewed_at = now
        event.reviewed_by = actor
        event.updated_at = now
        self.session.add(
            MetaEventAction(
                event_id=event_id,
                action=f"status:{status}",
                actor=actor,
                details_json=json.dumps(details or {}, ensure_ascii=False),
                created_at=now,
            )
        )
        await self.session.flush()
        return event

    async def set_group_enabled(
        self,
        *,
        group_id: int,
        enabled: bool,
    ) -> MetaSourceGroup:
        group = await self.session.get(MetaSourceGroup, group_id)
        if group is None:
            raise ValueError("group not found")
        group.enabled = enabled
        group.updated_at = datetime.now(UTC)
        await self.session.flush()
        return group

    async def dashboard_counts(self) -> dict[str, int]:
        events = await self.session.execute(
            select(MetaInboundEvent.status, func.count(MetaInboundEvent.id)).group_by(
                MetaInboundEvent.status
            )
        )
        groups = await self.session.execute(
            select(MetaSourceGroup.enabled, func.count(MetaSourceGroup.id)).group_by(
                MetaSourceGroup.enabled
            )
        )
        event_counts = {str(status): count for status, count in events.all()}
        group_counts = {bool(enabled): count for enabled, count in groups.all()}
        return {
            "new": event_counts.get("new", 0),
            "target": event_counts.get("target", 0),
            "noise": event_counts.get("noise", 0),
            "handled": event_counts.get("handled", 0),
            "groups_enabled": group_counts.get(True, 0),
            "groups_total": sum(group_counts.values()),
        }
