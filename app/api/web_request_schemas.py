from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator

from app.services.web_intake import WebIntakeAddress
from app.services.web_intake import WebIntakeItem
from app.services.web_intake import WebIntakeRequest


class WebRequestAddressPayload(BaseModel):
    kind: Literal["pickup", "dropoff"]
    raw_text: str = Field(min_length=1, max_length=500)
    floor: int | None = Field(default=None, ge=-1, le=24)
    has_elevator: bool | None = None

    def to_service_address(self) -> WebIntakeAddress:
        return WebIntakeAddress(
            kind=self.kind,
            raw_text=self.raw_text,
            floor=self.floor,
            has_elevator=self.has_elevator,
        )


class WebRequestItemPayload(BaseModel):
    description: str = Field(min_length=1, max_length=1000)
    quantity: int | None = Field(default=None, ge=0)

    def to_service_item(self) -> WebIntakeItem:
        return WebIntakeItem(
            description=self.description,
            quantity=self.quantity,
        )


class WebRequestPayload(BaseModel):
    source_locale: Literal["ru", "en", "pt"] | None = None
    customer_name: str | None = Field(default=None, max_length=255)
    customer_email: str | None = Field(default=None, max_length=255)
    preferred_contact: Literal["telegram", "whatsapp", "phone", "email"] | None = None
    client_phone: str | None = Field(default=None, max_length=64)
    client_whatsapp: str | None = Field(default=None, max_length=64)
    utm_source: str | None = Field(default=None, max_length=255)
    utm_medium: str | None = Field(default=None, max_length=255)
    utm_campaign: str | None = Field(default=None, max_length=255)
    utm_content: str | None = Field(default=None, max_length=255)
    landing_version: str | None = Field(default=None, max_length=64)
    requested_date: datetime | None = None
    addresses: list[WebRequestAddressPayload] = Field(min_length=2)
    items: list[WebRequestItemPayload] = Field(min_length=1)
    needs_assembly: bool = False
    needs_packing: bool = False
    needs_tail_lift: bool = False
    needs_crane: bool = False
    needs_mobile_lift: bool = False
    required_loaders: int | None = Field(default=None, ge=0)
    estimated_payload_kg: int | None = Field(default=None, ge=0)
    estimated_volume_m3: float | None = Field(default=None, ge=0)
    comment: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_web_request(self) -> "WebRequestPayload":
        if not (self.customer_email or self.client_phone or self.client_whatsapp):
            raise ValueError("at least one contact is required")

        address_kinds = {address.kind for address in self.addresses}
        if "pickup" not in address_kinds or "dropoff" not in address_kinds:
            raise ValueError("pickup and dropoff addresses are required")

        return self

    def to_service_request(self) -> WebIntakeRequest:
        return WebIntakeRequest(
            source_locale=self.source_locale,
            customer_name=self.customer_name,
            customer_email=self.customer_email,
            preferred_contact=self.preferred_contact,
            client_phone=self.client_phone,
            client_whatsapp=self.client_whatsapp,
            utm_source=self.utm_source,
            utm_medium=self.utm_medium,
            utm_campaign=self.utm_campaign,
            utm_content=self.utm_content,
            landing_version=self.landing_version,
            requested_date=self.requested_date,
            addresses=tuple(address.to_service_address() for address in self.addresses),
            items=tuple(item.to_service_item() for item in self.items),
            needs_assembly=self.needs_assembly,
            needs_packing=self.needs_packing,
            needs_tail_lift=self.needs_tail_lift,
            needs_crane=self.needs_crane,
            needs_mobile_lift=self.needs_mobile_lift,
            required_loaders=self.required_loaders,
            estimated_payload_kg=self.estimated_payload_kg,
            estimated_volume_m3=self.estimated_volume_m3,
            comment=self.comment,
        )


class WebRequestResponse(BaseModel):
    job_id: int
    status: str
    tracking_token: str
    tracking_url: str
    offers_count: int
    sent_count: int


class TrackingOfferResponse(BaseModel):
    offer_id: int
    company_name: str
    contact_name: str | None
    phone: str | None
    telegram_username: str | None
    vehicle_type: str
    payload_kg: int | None
    volume_m3: float | None
    max_loaders: int | None
    has_tail_lift: bool
    has_crane: bool
    has_mobile_lift: bool
    carrier_note: str | None
    price_cents: int | None


class TrackingJobResponse(BaseModel):
    job_id: int
    status: str
    cancelled_from_status: str | None = None
    tracking_token: str
    route_summary: str | None
    client_confirmation_status: str | None
    carrier_confirmation_status: str | None
    accepted_offers: list[TrackingOfferResponse]


class TrackingOfferSelectResponse(BaseModel):
    job_id: int
    status: str
    selected_offer_id: int


class TrackingAssignmentActionResponse(BaseModel):
    job_id: int
    status: str
    client_confirmation_status: str | None
    carrier_confirmation_status: str | None
