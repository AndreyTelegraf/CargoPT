from pathlib import Path

source = Path("app/bot/handlers/carrier_moderation_submit.py").read_text(encoding="utf-8")

assert "redispatch_open_jobs_to_new_carrier" in source
assert "send_job_offers_to_carriers" in source
assert "manual_review_required" in source
assert "offers_exhausted" in source
assert "expired_without_response" in source
assert "no_carriers_found" in source
assert "Job.requested_date.is_not(None)" in source
assert "Job.requested_date >= now" in source
assert "candidate.carrier_id == carrier_id" in source
assert "carrier_id=carrier.id" in source
assert "OfferDistributionService" not in source
assert "redispatch_created, redispatch_sent = await redispatch_open_jobs_to_new_carrier" in source

print("CARRIER_APPROVAL_AUTO_REDISPATCH_SMOKE_OK")
