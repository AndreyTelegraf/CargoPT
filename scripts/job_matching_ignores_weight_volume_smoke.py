from pathlib import Path

source = Path("app/services/job_matching.py").read_text(encoding="utf-8")

assert "min_payload_kg=None" in source
assert "min_volume_m3=None" in source
assert "min_loaders=None" in source
assert "needs_tail_lift=job.needs_tail_lift" in source
assert "needs_assembly=job.needs_assembly" in source
assert "regions=sorted(regions) or None" in source

assert "min_payload_kg=job.estimated_payload_kg" not in source
assert "min_volume_m3=job.estimated_volume_m3" not in source
assert "min_loaders=job.required_loaders" not in source

print("JOB_MATCHING_IGNORES_WEIGHT_VOLUME_SMOKE_OK")

assert "if loaded_addresses and not regions:" in source
assert "return []" in source
