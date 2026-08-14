from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class WebIntakeAddress:
    kind: str
    raw_text: str
    floor: int | None = None
    has_elevator: bool | None = None
    normalized_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None

@dataclass(frozen=True)
class WebIntakeItem:
    description: str
    quantity: int | None = None

@dataclass(frozen=True)
class WebIntakeRequest:
    source_locale: str | None
    customer_name: str | None
    customer_email: str | None
    preferred_contact: str | None
    client_phone: str | None
    client_whatsapp: str | None
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    utm_content: str | None
    landing_version: str | None
    requested_date: datetime | None
    addresses: tuple[WebIntakeAddress, ...]
    items: tuple[WebIntakeItem, ...]
    needs_assembly: bool = False
    needs_packing: bool = False
    needs_tail_lift: bool = False
    needs_crane: bool = False
    needs_mobile_lift: bool = False
    required_loaders: int | None = None
    estimated_payload_kg: int | None = None
    estimated_volume_m3: float | None = None
    comment: str | None = None
