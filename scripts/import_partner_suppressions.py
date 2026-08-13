import argparse
import asyncio
import csv
import hashlib
from datetime import UTC
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.db.session import async_session_maker
from app.models.partner_outreach import PartnerOutreachComplianceSnapshot
from app.models.partner_outreach import PartnerOutreachSuppression
from app.repositories.partner_outreach import PartnerOutreachRepository
from app.services.partner_outreach.dispatcher import DGC_SOURCE
from app.services.partner_outreach.models import SuppressionKind
from app.services.partner_outreach.policy import normalize_domain
from app.services.partner_outreach.policy import normalize_email
from app.services.partner_outreach.policy import normalize_nif
from app.services.partner_outreach.policy import normalize_organization


def normalize_value(kind: str, value: str) -> str:
    if kind == SuppressionKind.EMAIL.value:
        return normalize_email(value)
    if kind == SuppressionKind.DOMAIN.value:
        return normalize_domain(value)
    if kind == SuppressionKind.NIF.value:
        normalized = normalize_nif(value)
        if len(normalized) != 9:
            raise ValueError("suppression NIF must contain 9 digits")
        return normalized
    if kind == SuppressionKind.ORGANIZATION.value:
        normalized = normalize_organization(value)
        if not normalized:
            raise ValueError("suppression organization is empty")
        return normalized
    raise ValueError("suppression kind must be email, domain, nif, or organization")


def load_rows(path: Path) -> list[tuple[str, str, str | None]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not {"kind", "value"}.issubset(reader.fieldnames or []):
            raise ValueError("suppression CSV requires kind and value columns")
        result = []
        seen: set[tuple[str, str]] = set()
        for row_number, row in enumerate(reader, start=2):
            kind = (row.get("kind") or "").strip().lower()
            try:
                value = normalize_value(kind, row.get("value") or "")
            except ValueError as exc:
                raise ValueError(f"row {row_number}: {exc}") from exc
            key = (kind, value)
            if key in seen:
                continue
            seen.add(key)
            result.append(
                (kind, value, (row.get("reason") or "").strip() or None)
            )
    return result


async def apply_rows(
    *,
    rows: list[tuple[str, str, str | None]],
    source: str,
    checked_at: datetime,
    checksum: str,
) -> None:
    now = datetime.now(UTC)
    async with async_session_maker() as session:
        repository = PartnerOutreachRepository(session)
        for kind, value, reason in rows:
            await repository.upsert_suppression(
                PartnerOutreachSuppression(
                    kind=kind,
                    normalized_value=value,
                    source=source,
                    reason=reason,
                    created_at=now,
                    updated_at=now,
                )
            )
        if source == DGC_SOURCE:
            session.add(
                PartnerOutreachComplianceSnapshot(
                    source=source,
                    checksum_sha256=checksum,
                    row_count=len(rows),
                    checked_at=checked_at,
                    imported_at=now,
                )
            )
        await session.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument(
        "--source",
        choices=(DGC_SOURCE, "internal"),
        required=True,
    )
    parser.add_argument("--checked-at", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    raw = args.csv_path.read_bytes()
    rows = load_rows(args.csv_path)
    checked_at = datetime.fromisoformat(
        args.checked_at.strip().replace("Z", "+00:00")
    )
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=UTC)
    checked_at = checked_at.astimezone(UTC)
    checksum = hashlib.sha256(raw).hexdigest()
    print(f"PARTNER_SUPPRESSIONS_VALID={len(rows)}")
    print(f"PARTNER_SUPPRESSIONS_SHA256={checksum}")
    if not args.apply:
        print("PARTNER_SUPPRESSIONS_DRY_RUN")
        return
    if not settings.partner_outreach_enabled:
        raise SystemExit("PARTNER_OUTREACH_DISABLED")
    asyncio.run(
        apply_rows(
            rows=rows,
            source=args.source,
            checked_at=checked_at,
            checksum=checksum,
        )
    )
    print(f"PARTNER_SUPPRESSIONS_IMPORTED={len(rows)}")


if __name__ == "__main__":
    main()
