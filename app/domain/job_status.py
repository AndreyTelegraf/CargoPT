from enum import StrEnum


class JobStatus(StrEnum):
    DRAFT = "draft"
    DRAFT_EXPIRED = "draft_expired"
    READY_FOR_MATCHING = "ready_for_matching"
    MATCHING = "matching"
    OFFERED = "offered"
    UNMATCHED = "unmatched"
    NO_CARRIERS_FOUND = "no_carriers_found"
    OFFERS_EXHAUSTED = "offers_exhausted"
    EXPIRED_WITHOUT_RESPONSE = "expired_without_response"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    ASSIGNED_PENDING_CONFIRMATION = "assigned_pending_confirmation"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
