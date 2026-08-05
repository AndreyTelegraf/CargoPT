from collections.abc import AsyncIterator
from datetime import UTC
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import secrets

from aiogram import Bot
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic
from fastapi.security import HTTPBasicCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import async_session_maker
from app.models.meta_operations import MetaInboundEvent
from app.repositories.meta_operations import MetaOperationsRepository
from app.services.meta_operations.classifier import build_draft_reply
from app.services.meta_operations.classifier import classify_lead
from app.services.meta_operations.email_parser import ParsedInboundEmail
from app.services.meta_operations.email_parser import parse_rfc822
from app.services.meta_operations.telegram_alerts import send_event_alert


router = APIRouter()
security = HTTPBasic(auto_error=False)
FACEBOOK_GROUP_RE = re.compile(
    r"https?://(?:www\.)?facebook\.com/groups/([^/?#]+)",
    re.IGNORECASE,
)
CONSOLE_FILE = Path(__file__).resolve().parents[1] / "static" / "meta-operations" / "index.html"


class JsonInboundPayload(BaseModel):
    message_id: str | None = None
    sender: str | None = None
    subject: str | None = None
    text: str
    source_url: str | None = None
    received_at: datetime | None = None


class StatusPayload(BaseModel):
    status: str


class EnabledPayload(BaseModel):
    enabled: bool


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def require_enabled() -> None:
    if not settings.meta_operations_enabled:
        raise HTTPException(status_code=404, detail="not found")


def require_admin(
    credentials: HTTPBasicCredentials | None = Depends(security),
) -> str:
    require_enabled()
    configured_user = settings.meta_operations_admin_username
    configured_password = settings.meta_operations_admin_password.get_secret_value()
    if not configured_user or not configured_password or credentials is None:
        raise HTTPException(
            status_code=401,
            detail="authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )
    valid = secrets.compare_digest(credentials.username, configured_user) and secrets.compare_digest(
        credentials.password,
        configured_password,
    )
    if not valid:
        raise HTTPException(
            status_code=401,
            detail="invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def _external_ids(urls: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    for url in urls:
        match = FACEBOOK_GROUP_RE.search(url)
        if match:
            result.append(match.group(1).strip())
    return tuple(dict.fromkeys(result))


def _event_to_dict(event, group) -> dict:
    return {
        "id": event.id,
        "status": event.status,
        "classification": event.classification_label,
        "score": event.score,
        "confidence": event.confidence,
        "language": event.language,
        "subject": event.subject,
        "text": event.text,
        "source_url": event.source_url,
        "draft_reply": event.draft_reply,
        "received_at": event.received_at.isoformat(),
        "created_at": event.created_at.isoformat(),
        "group": None
        if group is None
        else {
            "id": group.id,
            "name": group.name,
            "region": group.region,
            "canonical_url": group.canonical_url,
        },
    }


@router.get("/meta-operations", include_in_schema=False)
async def meta_operations_console(actor: str = Depends(require_admin)) -> FileResponse:
    del actor
    return FileResponse(CONSOLE_FILE, headers={"Cache-Control": "no-store"})


@router.post("/api/v1/meta-operations/inbound/email")
async def receive_email_notification(
    request: Request,
    x_cargopt_inbound_token: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    require_enabled()
    expected = settings.meta_operations_inbound_token.get_secret_value()
    if not expected or not x_cargopt_inbound_token or not secrets.compare_digest(
        x_cargopt_inbound_token,
        expected,
    ):
        raise HTTPException(status_code=401, detail="invalid inbound token")

    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        payload = JsonInboundPayload.model_validate(await request.json())
        parsed = ParsedInboundEmail(
            message_id=payload.message_id,
            sender=payload.sender,
            subject=payload.subject,
            text=payload.text[:20000],
            urls=tuple(
                dict.fromkeys(
                    re.findall(r"https?://[^\s<>\"']+", " ".join(filter(None, (payload.text, payload.source_url))))
                )
            )[:30],
        )
        received_at = payload.received_at or datetime.now(UTC)
        explicit_source_url = payload.source_url
    else:
        raw = await request.body()
        if not raw or len(raw) > 1_000_000:
            raise HTTPException(status_code=413, detail="invalid email payload size")
        parsed = parse_rfc822(raw)
        received_at = datetime.now(UTC)
        explicit_source_url = None

    combined = "\n".join(filter(None, (parsed.subject, parsed.text))).strip()
    if not combined:
        raise HTTPException(status_code=422, detail="email text is empty")
    source_url = explicit_source_url or next(
        (url for url in parsed.urls if "facebook.com" in url.lower()),
        parsed.urls[0] if parsed.urls else None,
    )
    dedupe_basis = parsed.message_id or "\n".join(
        filter(None, (parsed.sender, parsed.subject, parsed.text, source_url))
    )
    dedupe_key = sha256(dedupe_basis.encode("utf-8")).hexdigest()

    repo = MetaOperationsRepository(session)
    group = await repo.find_group_for_text(combined, _external_ids(parsed.urls))
    classification = classify_lead(combined)
    now = datetime.now(UTC)
    event = MetaInboundEvent(
        source_group_id=group.id if group else None,
        platform="facebook",
        provider_message_id=parsed.message_id,
        event_type="notification",
        sender=parsed.sender,
        subject=parsed.subject,
        text=parsed.text,
        source_url=source_url,
        language=classification.language,
        dedupe_key=dedupe_key,
        classification_label=classification.label,
        confidence=classification.confidence,
        score=classification.score,
        matched_terms_json=json.dumps(classification.matched_terms, ensure_ascii=False),
        draft_reply=build_draft_reply(classification.language, group_id=group.id if group else None),
        status="new" if classification.label in {"target", "review"} else "noise",
        received_at=received_at,
        telegram_message_refs_json="[]",
        created_at=now,
        updated_at=now,
    )
    event, created = await repo.create_event(event)
    alerted = False
    alert_error = None
    if (
        created
        and classification.label in {"target", "review"}
        and classification.score / 100 >= settings.meta_operations_alert_threshold
        and settings.meta_operations_chat_ids
    ):
        bot = Bot(settings.bot_token)
        try:
            alerted = bool(await send_event_alert(bot, event, group))
        except Exception as exc:
            alert_error = type(exc).__name__
        finally:
            await bot.session.close()

    return {
        "event_id": event.id,
        "created": created,
        "classification": event.classification_label,
        "score": event.score,
        "group_id": event.source_group_id,
        "alerted": alerted,
        "alert_error": alert_error,
    }


@router.get("/api/v1/meta-operations/admin/summary")
async def get_summary(
    actor: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    del actor
    return await MetaOperationsRepository(session).dashboard_counts()


@router.get("/api/v1/meta-operations/admin/events")
async def get_events(
    status: str | None = Query(default=None),
    classification: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    actor: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    del actor
    rows = await MetaOperationsRepository(session).list_events(
        status=status,
        classification=classification,
        limit=limit,
    )
    return [_event_to_dict(event, group) for event, group in rows]


@router.patch("/api/v1/meta-operations/admin/events/{event_id}/status")
async def set_event_status(
    event_id: int,
    payload: StatusPayload,
    actor: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if payload.status not in {"new", "target", "noise", "handled"}:
        raise HTTPException(status_code=422, detail="invalid status")
    try:
        event = await MetaOperationsRepository(session).update_event_status(
            event_id=event_id,
            status=payload.status,
            actor=f"console:{actor}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"id": event.id, "status": event.status}


@router.get("/api/v1/meta-operations/admin/groups")
async def get_groups(
    enabled: bool | None = Query(default=None),
    actor: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    del actor
    groups = await MetaOperationsRepository(session).list_groups(enabled=enabled)
    return [
        {
            "id": group.id,
            "name": group.name,
            "region": group.region,
            "category": group.category,
            "priority": group.priority,
            "review_status": group.review_status,
            "canonical_url": group.canonical_url,
            "enabled": group.enabled,
            "rules_checked": group.rules_checked,
            "ads_allowed": group.ads_allowed,
        }
        for group in groups
    ]


@router.patch("/api/v1/meta-operations/admin/groups/{group_id}/enabled")
async def set_group_enabled(
    group_id: int,
    payload: EnabledPayload,
    actor: str = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        group = await MetaOperationsRepository(session).set_group_enabled(
            group_id=group_id,
            enabled=payload.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"id": group.id, "enabled": group.enabled}


@router.post("/api/v1/meta-operations/admin/classify")
async def preview_classification(
    payload: JsonInboundPayload,
    actor: str = Depends(require_admin),
) -> dict:
    del actor
    result = classify_lead("\n".join(filter(None, (payload.subject, payload.text))))
    return {
        "classification": result.label,
        "score": result.score,
        "confidence": result.confidence,
        "language": result.language,
        "matched_terms": result.matched_terms,
        "draft_reply": build_draft_reply(result.language),
    }
