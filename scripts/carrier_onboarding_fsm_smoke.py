import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.bot.states.carrier_onboarding import CarrierOnboardingStates

assert CarrierOnboardingStates.language
assert CarrierOnboardingStates.assembly_required
assert CarrierOnboardingStates.packing_required
assert CarrierOnboardingStates.operating_regions
assert CarrierOnboardingStates.vehicle_count
assert CarrierOnboardingStates.vehicle_type
assert CarrierOnboardingStates.payload_kg
assert CarrierOnboardingStates.volume_m3
assert CarrierOnboardingStates.has_tail_lift
assert CarrierOnboardingStates.has_crane
assert CarrierOnboardingStates.has_mobile_lift
assert CarrierOnboardingStates.mobile_lift_max_floor
assert CarrierOnboardingStates.mobile_lift_max_weight_kg
assert CarrierOnboardingStates.crane_max_weight_kg
assert CarrierOnboardingStates.crane_reach_meters
assert CarrierOnboardingStates.max_loaders
assert CarrierOnboardingStates.company_phone
assert CarrierOnboardingStates.company_email

print("CARRIER_ONBOARDING_FSM_SMOKE_OK")
