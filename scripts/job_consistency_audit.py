import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "cargopt_prod.db"

if not DB_PATH.exists():
    raise SystemExit(f"database not found: {DB_PATH}")


OFFER_COUNTS_QUERY = """
SELECT
    j.id,
    j.client_telegram_username,
    j.status AS job_status,
    SUM(CASE WHEN o.status = 'accepted' THEN 1 ELSE 0 END) AS accepted,
    SUM(CASE WHEN o.status = 'pending' THEN 1 ELSE 0 END) AS pending,
    SUM(CASE WHEN o.status = 'declined' THEN 1 ELSE 0 END) AS declined,
    SUM(CASE WHEN o.status = 'expired' THEN 1 ELSE 0 END) AS expired,
    SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled,
    COUNT(o.id) AS total_offers
FROM job j
LEFT JOIN job_offer o ON o.job_id = j.id
GROUP BY
    j.id,
    j.client_telegram_username,
    j.status
ORDER BY j.id;
"""


DUPLICATE_ACTIVE_OFFERS_QUERY = """
SELECT
    o.job_id,
    o.carrier_id,
    COUNT(*) AS active_offers
FROM job_offer o
WHERE o.status IN ('pending', 'accepted')
GROUP BY
    o.job_id,
    o.carrier_id
HAVING COUNT(*) > 1
ORDER BY
    o.job_id,
    o.carrier_id;
"""


ASSIGNMENT_STATUSES = {
    "assigned_pending_confirmation",
    "assigned",
    "in_progress",
    "completed",
}

PENDING_ALLOWED_STATUSES = {
    "matching",
    "offered",
}

OFFERS_REQUIRED_STATUSES = {
    "offered",
    "assigned_pending_confirmation",
    "assigned",
    "in_progress",
    "completed",
    "offers_exhausted",
    "expired_without_response",
}


def append_issue(
    issues: list[dict],
    *,
    row,
    reason: str,
) -> None:
    issues.append(
        {
            "job_id": row["id"],
            "client": row["client_telegram_username"],
            "job_status": row["job_status"],
            "accepted": int(row["accepted"]),
            "pending": int(row["pending"]),
            "declined": int(row["declined"]),
            "expired": int(row["expired"]),
            "cancelled": int(row["cancelled"]),
            "total_offers": int(row["total_offers"]),
            "reason": reason,
        }
    )


with sqlite3.connect(DB_PATH) as conn:
    conn.row_factory = sqlite3.Row

    rows = conn.execute(OFFER_COUNTS_QUERY).fetchall()
    duplicate_active_rows = conn.execute(
        DUPLICATE_ACTIVE_OFFERS_QUERY
    ).fetchall()


issues: list[dict] = []

for row in rows:
    status = str(row["job_status"])
    accepted = int(row["accepted"])
    pending = int(row["pending"])
    total_offers = int(row["total_offers"])

    if status == "offered":
        # Carrier acceptance is a positive response, not assignment.
        # Several accepted offers may coexist until the client selects one.
        pass
    elif status in ASSIGNMENT_STATUSES:
        if accepted != 1:
            append_issue(
                issues,
                row=row,
                reason=(
                    "assignment lifecycle status must have exactly "
                    "one accepted offer"
                ),
            )
    elif accepted != 0:
        append_issue(
            issues,
            row=row,
            reason=(
                "accepted offers are not allowed for this job status"
            ),
        )

    if pending > 0 and status not in PENDING_ALLOWED_STATUSES:
        append_issue(
            issues,
            row=row,
            reason=(
                "pending offers are allowed only while matching "
                "or offered"
            ),
        )

    if total_offers == 0 and status in OFFERS_REQUIRED_STATUSES:
        append_issue(
            issues,
            row=row,
            reason=(
                "job status requires at least one historical offer"
            ),
        )


for row in duplicate_active_rows:
    issues.append(
        {
            "job_id": int(row["job_id"]),
            "client": None,
            "job_status": None,
            "accepted": None,
            "pending": None,
            "declined": None,
            "expired": None,
            "cancelled": None,
            "total_offers": None,
            "reason": (
                "carrier "
                f"{int(row['carrier_id'])} has "
                f"{int(row['active_offers'])} active offers "
                "for the same job"
            ),
        }
    )


print("JOB_CONSISTENCY_AUDIT")
print(f"db={DB_PATH}")
print(f"issues={len(issues)}")

for issue in issues:
    print(
        "issue "
        f"job_id={issue['job_id']} "
        f"client={issue['client']} "
        f"job_status={issue['job_status']} "
        f"accepted={issue['accepted']} "
        f"pending={issue['pending']} "
        f"declined={issue['declined']} "
        f"expired={issue['expired']} "
        f"cancelled={issue['cancelled']} "
        f"total_offers={issue['total_offers']} "
        f"reason={issue['reason']}"
    )

if issues:
    raise SystemExit(1)

print("JOB_CONSISTENCY_AUDIT_OK")
