import argparse
import asyncio
import csv
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.db.session import async_session_maker
from app.models.partner_outreach import PartnerProspect
from app.repositories.partner_outreach import PartnerOutreachRepository
from app.services.partner_outreach.models import ProspectStatus
from app.services.partner_outreach.policy import ALLOWED_CATEGORIES
from app.services.partner_outreach.policy import normalize_locale
from app.services.partner_outreach.policy import normalize_municipality
from app.services.partner_outreach.policy import normalize_nif
from app.services.partner_outreach.policy import validate_prospect_contact


REQUIRED_COLUMNS = {
    "company_name",
    "website_url",
    "contact_email",
    "category",
    "municipality",
    "language",
    "source_url",
    "source_checked_at",
}


@dataclass(frozen=True)
class Candidate:
    company_name: str
    legal_entity_name: str | None
    nif: str | None
    company_domain: str
    website_url: str
    contact_email: str
    category: str
    municipality: str
    language: str
    source_url: str
    source_checked_at: datetime
    qualification_note: str | None


def _parse_datetime(value: str, *, row_number: int) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            f"row {row_number}: source_checked_at must be ISO-8601"
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def load_candidates(path: Path) -> list[Candidate]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                "missing CSV columns: " + ", ".join(sorted(missing))
            )
        candidates: list[Candidate] = []
        seen_domains: set[str] = set()
        seen_emails: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            company_name = (row.get("company_name") or "").strip()
            if not company_name:
                raise ValueError(f"row {row_number}: company_name is required")
            website_url = (row.get("website_url") or "").strip()
            source_url = (row.get("source_url") or "").strip()
            email, domain = validate_prospect_contact(
                email=row.get("contact_email") or "",
                website_url=website_url,
                source_url=source_url,
            )
            if domain in seen_domains or email in seen_emails:
                raise ValueError(f"row {row_number}: duplicate domain or email")
            seen_domains.add(domain)
            seen_emails.add(email)

            category = (row.get("category") or "").strip().lower()
            if category not in ALLOWED_CATEGORIES:
                raise ValueError(f"row {row_number}: unsupported category")
            nif = normalize_nif(row.get("nif"))
            if nif and len(nif) != 9:
                raise ValueError(f"row {row_number}: NIF must contain 9 digits")
            candidates.append(
                Candidate(
                    company_name=company_name,
                    legal_entity_name=(
                        (row.get("legal_entity_name") or "").strip() or None
                    ),
                    nif=nif or None,
                    company_domain=domain,
                    website_url=website_url,
                    contact_email=email,
                    category=category,
                    municipality=normalize_municipality(
                        row.get("municipality") or ""
                    ),
                    language=normalize_locale(row.get("language") or ""),
                    source_url=source_url,
                    source_checked_at=_parse_datetime(
                        row.get("source_checked_at") or "",
                        row_number=row_number,
                    ),
                    qualification_note=(
                        (row.get("qualification_note") or "").strip() or None
                    ),
                )
            )
    return candidates


async def apply_candidates(candidates: list[Candidate]) -> None:
    now = datetime.now(UTC)
    async with async_session_maker() as session:
        repository = PartnerOutreachRepository(session)
        for candidate in candidates:
            await repository.add_prospect(
                PartnerProspect(
                    company_name=candidate.company_name,
                    legal_entity_name=candidate.legal_entity_name,
                    nif=candidate.nif,
                    company_domain=candidate.company_domain,
                    website_url=candidate.website_url,
                    contact_email=candidate.contact_email,
                    contact_kind="role",
                    category=candidate.category,
                    municipality=candidate.municipality,
                    region="lisbon_metro",
                    language=candidate.language,
                    source_url=candidate.source_url,
                    source_checked_at=candidate.source_checked_at,
                    qualification_note=candidate.qualification_note,
                    status=ProspectStatus.CANDIDATE.value,
                    approved_at=None,
                    approved_by=None,
                    do_not_contact=False,
                    do_not_contact_reason=None,
                    created_at=now,
                    updated_at=now,
                )
            )
        await session.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    candidates = load_candidates(args.csv_path)
    print(f"PARTNER_PROSPECTS_VALID={len(candidates)}")
    for candidate in candidates:
        print(
            " | ".join(
                (
                    candidate.company_name,
                    candidate.category,
                    candidate.municipality,
                    candidate.contact_email,
                )
            )
        )
    if not args.apply:
        print("PARTNER_PROSPECTS_DRY_RUN")
        return
    if not settings.partner_outreach_enabled:
        raise SystemExit("PARTNER_OUTREACH_DISABLED")
    asyncio.run(apply_candidates(candidates))
    print(f"PARTNER_PROSPECTS_IMPORTED={len(candidates)}")


if __name__ == "__main__":
    main()
