from pathlib import Path

source = Path(
    "app/services/job_matching.py"
).read_text(encoding="utf-8")

assert "regions=sorted(regions) or None" in source
assert "for address in addresses_to_match:" in source
assert "address.kind == \"pickup\"" in source
assert "if not address_regions:" in source
assert "MatchingReason.REGION_NOT_DETERMINED" in source

request_constraints = (
    "min_payload_kg=job.estimated_payload_kg",
    "min_volume_m3=job.estimated_volume_m3",
    "min_loaders=job.required_loaders",
    "needs_tail_lift=job.needs_tail_lift",
    "needs_crane=job.needs_crane",
    "needs_mobile_lift=job.needs_mobile_lift",
    "needs_assembly=job.needs_assembly",
    "needs_packing=job.needs_packing",
)

for constraint in request_constraints:
    assert constraint not in source, constraint

print("JOB_MATCHING_USES_REGIONS_ONLY_SMOKE_OK")
