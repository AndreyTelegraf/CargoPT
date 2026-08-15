from aiogram.fsm.state import State
from aiogram.fsm.state import StatesGroup


class CarrierOnboardingStates(StatesGroup):
    language = State()
    welcome = State()
    public_name = State()
    experience_since_year = State()
    logo = State()
    publication_consent = State()
    assembly_required = State()
    packing_required = State()
    operating_regions = State()
    vehicle_count = State()
    vehicle_type = State()
    payload_kg = State()
    volume_m3 = State()
    has_tail_lift = State()
    has_crane = State()
    has_mobile_lift = State()
    mobile_lift_max_floor = State()
    mobile_lift_max_weight_kg = State()
    crane_max_weight_kg = State()
    crane_reach_meters = State()
    max_loaders = State()
    company_phone = State()
    company_email = State()
    moderation_review = State()
