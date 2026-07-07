from pathlib import Path

source = Path("app/services/job_matching.py").read_text(encoding="utf-8")

assert "regions=sorted(regions) or None" in source

assert "min_payload_kg=" not in source
assert "min_volume_m3=" not in source
assert "min_loaders=" not in source
assert "needs_tail_lift=job.needs_tail_lift" not in source
assert "needs_crane=job.needs_crane" not in source
assert "needs_mobile_lift=job.needs_mobile_lift" not in source
assert "needs_assembly=job.needs_assembly" not in source
assert "needs_packing=job.needs_packing" not in source

assert "if loaded_addresses and not regions:" in source
assert "MatchingReason.REGION_NOT_DETERMINED" in source

print("JOB_MATCHING_IGNORES_WEIGHT_VOLUME_SMOKE_OK")
