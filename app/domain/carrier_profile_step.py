from enum import StrEnum


class CarrierProfileStep(StrEnum):
    PUBLIC_NAME = "public_name"
    EXPERIENCE_SINCE_YEAR = "experience_since_year"
    LOGO = "logo"
    PUBLICATION_CONSENT = "publication_consent"
    ASSEMBLY_REQUIRED = "assembly_required"
    PACKING_REQUIRED = "packing_required"
    OPERATING_REGIONS = "operating_regions"
    VEHICLES = "vehicles"
    COMPLETED = "completed"
