import re
from datetime import datetime
from datetime import date
from datetime import time
from datetime import UTC
from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from app.domain.contact_identity import normalize_email_identity
from app.domain.contact_identity import normalize_phone_identity
from app.domain.requested_date import RequestedDateInPastError
from app.domain.requested_date import PORTUGAL_TIMEZONE
from app.domain.requested_date import validate_requested_date_not_in_past
from app.services.web_intake import WebIntakeAddress
from app.services.web_intake import WebIntakeItem
from app.services.web_intake import WebIntakeRequest


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def portugal_local_datetime_to_utc(
    local_date: date,
    local_time: time,
) -> datetime:
    if local_time.tzinfo is not None:
        raise ValueError("requested_time_local must not include a timezone")

    naive = datetime.combine(local_date, local_time)
    candidates = set()
    for fold in (0, 1):
        local_value = naive.replace(tzinfo=PORTUGAL_TIMEZONE, fold=fold)
        utc_value = local_value.astimezone(UTC)
        round_trip = utc_value.astimezone(PORTUGAL_TIMEZONE).replace(tzinfo=None)
        if round_trip == naive:
            candidates.add(utc_value)

    if not candidates:
        raise ValueError("requested local time does not exist in Portugal")
    if len(candidates) > 1:
        raise ValueError("requested local time is ambiguous in Portugal")
    return candidates.pop()


class WebRequestAddressPayload(BaseModel):
    kind: Literal["pickup", "dropoff"]
    raw_text: str = Field(min_length=1, max_length=500)
    normalized_address: str = Field(min_length=1, max_length=500)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    location_confirmed: bool
    country_code: str = Field(default="pt", min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")
    address_details: str | None = Field(default=None, max_length=300)
    postal_code: str | None = Field(default=None, max_length=32)
    floor: int | None = Field(default=None, ge=-1, le=24)
    has_elevator: bool | None = None

    @field_validator("raw_text", "normalized_address", mode="before")
    @classmethod
    def normalize_required_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("country_code", mode="before")
    @classmethod
    def normalize_country_code(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("address_details", "postal_code", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if not isinstance(value, str):
            return value
        return value.strip() or None

    @model_validator(mode="after")
    def validate_location_selection(self) -> "WebRequestAddressPayload":
        if not self.location_confirmed:
            raise ValueError("address location must be selected and confirmed")
        return self

    def to_service_address(self) -> WebIntakeAddress:
        return WebIntakeAddress(
            kind=self.kind,
            raw_text=self.raw_text,
            normalized_address=self.normalized_address,
            latitude=self.latitude,
            longitude=self.longitude,
            country_code=self.country_code.lower(),
            address_details=self.address_details,
            postal_code=self.postal_code,
            floor=self.floor,
            has_elevator=self.has_elevator,
        )


class WebRequestItemPayload(BaseModel):
    description: str = Field(min_length=1, max_length=1000)
    quantity: int | None = Field(default=None, ge=1, le=100000)

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value):
        return value.strip() if isinstance(value, str) else value

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
    referrer_host: str | None = Field(default=None, max_length=255)
    fbclid: str | None = Field(default=None, max_length=1024)
    landing_version: str | None = Field(default=None, max_length=64)
    requested_date: datetime | None = None
    requested_date_local: date | None = None
    requested_time_local: time | None = None
    addresses: list[WebRequestAddressPayload] = Field(min_length=2, max_length=2)
    items: list[WebRequestItemPayload] = Field(min_length=1, max_length=50)
    needs_assembly: bool = False
    needs_packing: bool = False
    needs_tail_lift: bool = False
    needs_crane: bool = False
    needs_mobile_lift: bool = False
    required_loaders: int | None = Field(default=None, ge=0)
    estimated_payload_kg: int | None = Field(default=None, ge=0)
    estimated_volume_m3: float | None = Field(default=None, ge=0)
    comment: str | None = Field(default=None, max_length=2000)

    @field_validator(
        "customer_name",
        "customer_email",
        "client_phone",
        "client_whatsapp",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "referrer_host",
        "fbclid",
        "landing_version",
        "comment",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value):
        if not isinstance(value, str):
            return value
        return value.strip() or None

    @field_validator("customer_email")
    @classmethod
    def validate_customer_email(cls, value: str | None) -> str | None:
        if value is not None and EMAIL_PATTERN.fullmatch(value) is None:
            raise ValueError("customer_email must be a valid email address")
        return normalize_email_identity(value)

    @field_validator("client_phone", "client_whatsapp")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_phone_identity(value)
        if normalized is None:
            raise ValueError("phone must contain a valid international number")
        return normalized

    @model_validator(mode="after")
    def validate_web_request(self) -> "WebRequestPayload":
        has_local_date = self.requested_date_local is not None
        has_local_time = self.requested_time_local is not None
        if has_local_date != has_local_time:
            raise ValueError(
                "requested_date_local and requested_time_local must be provided together"
            )
        if self.requested_date is not None and has_local_date:
            raise ValueError(
                "use either requested_date or local requested date and time"
            )
        if has_local_date and has_local_time:
            self.requested_date = portugal_local_datetime_to_utc(
                self.requested_date_local,
                self.requested_time_local,
            )

        if not (self.customer_email or self.client_phone or self.client_whatsapp):
            raise ValueError("at least one contact is required")

        address_kinds = [address.kind for address in self.addresses]
        if address_kinds.count("pickup") != 1 or address_kinds.count("dropoff") != 1:
            raise ValueError("exactly one pickup and one dropoff address are required")

        has_foreign_address = any(
            address.country_code.lower() != "pt" for address in self.addresses
        )
        has_portugal_endpoint = any(
            address.country_code.lower() == "pt"
            for address in self.addresses
        )
        if has_foreign_address and not has_portugal_endpoint:
            raise ValueError("international routes must include Portugal")

        try:
            validate_requested_date_not_in_past(self.requested_date)
        except RequestedDateInPastError as error:
            raise ValueError("requested_date must not be in the past") from error

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
            referrer_host=self.referrer_host,
            fbclid=self.fbclid,
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


class AcquisitionEventPayload(BaseModel):
    event_type: Literal[
        "landing_view",
        "form_start",
        "step1_complete",
        "submit_attempt",
        "submit_success",
        "submit_error_validation",
        "submit_error_rate_limit",
        "submit_error_server",
        "submit_error_network",
        "submit_error_unexpected",
    ]
    source_locale: Literal["ru", "en", "pt"]
    utm_source: str | None = Field(default=None, max_length=255)
    utm_medium: str | None = Field(default=None, max_length=255)
    utm_campaign: str | None = Field(default=None, max_length=255)
    utm_content: str | None = Field(default=None, max_length=255)
    referrer_host: str | None = Field(default=None, max_length=255)
    landing_version: str | None = Field(default=None, max_length=64)
    error_category: Literal[
        "",
        "request",
        "addresses",
        "pickup",
        "dropoff",
        "items",
        "customer_name",
        "requested_date",
        "contact",
        "client_phone",
        "client_whatsapp",
        "customer_email",
        "pickup_floor",
        "pickup_elevator",
        "dropoff_floor",
        "dropoff_elevator",
        "required_loaders",
        "estimated_volume_m3",
        "comment",
        "unknown",
    ] = ""


class WebRequestResponse(BaseModel):
    job_id: int
    status: str
    tracking_token: str
    tracking_url: str
    offers_count: int
    sent_count: int
    queued_count: int


class LocationSuggestionResponse(BaseModel):
    display_name: str
    latitude: float
    longitude: float
    map_url: str
    country_code: str
    postal_code: str | None = None
    address_details_hint: str | None = None


class TrackingOfferResponse(BaseModel):
    offer_id: int
    company_name: str
    operating_regions: str | None = None
    experience_since_year: int | None = None
    logo_url: str | None = None
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
    included_services: str | None
    possible_surcharges: str | None
    service_window: str | None
    estimate_status: str | None


class TrackingAddressResponse(BaseModel):
    kind: str
    raw_text: str
    normalized_address: str | None
    country_code: str | None
    postal_code: str | None
    address_details: str | None
    floor: int | None
    has_elevator: bool | None


class TrackingItemResponse(BaseModel):
    description: str
    quantity: int | None


class TrackingRequestDetailsResponse(BaseModel):
    customer_name: str | None
    customer_email: str | None
    preferred_contact: str | None
    client_phone: str | None
    client_whatsapp: str | None
    requested_date: datetime | None
    addresses: list[TrackingAddressResponse]
    items: list[TrackingItemResponse]
    needs_assembly: bool
    needs_packing: bool
    needs_tail_lift: bool
    needs_crane: bool
    needs_mobile_lift: bool
    required_loaders: int | None
    estimated_payload_kg: int | None
    estimated_volume_m3: float | None
    comment: str | None


class TrackingJobResponse(BaseModel):
    job_id: int
    status: str
    cancelled_from_status: str | None = None
    short_lead_time_warning: bool = False
    tracking_token: str
    route_summary: str | None
    client_confirmation_status: str | None
    carrier_confirmation_status: str | None
    completion_prompted_at: datetime | None
    client_completion_status: str | None
    carrier_completion_status: str | None
    accepted_offers: list[TrackingOfferResponse]
    request_details: TrackingRequestDetailsResponse


class TrackingTokenRotateResponse(BaseModel):
    job_id: int
    tracking_token: str
    tracking_url: str


class TrackingOfferSelectResponse(BaseModel):
    job_id: int
    status: str
    selected_offer_id: int


class TrackingRequestCancelResponse(BaseModel):
    job_id: int
    status: str
    cancelled_from_status: str


class TrackingRequestedDateChangePayload(BaseModel):
    requested_date_local: date
    requested_time_local: time

    @model_validator(mode="after")
    def validate_portugal_local_datetime(
        self,
    ) -> "TrackingRequestedDateChangePayload":
        requested_date = portugal_local_datetime_to_utc(
            self.requested_date_local,
            self.requested_time_local,
        )
        try:
            validate_requested_date_not_in_past(requested_date)
        except RequestedDateInPastError as error:
            raise ValueError(
                "requested date must not be in the past"
            ) from error
        return self

    def to_requested_date(self) -> datetime:
        return portugal_local_datetime_to_utc(
            self.requested_date_local,
            self.requested_time_local,
        )


class TrackingRequestedDateChangeResponse(BaseModel):
    job_id: int
    status: str
    previous_status: str
    requested_date: datetime
    repricing_required: bool


class TrackingAssignmentActionResponse(BaseModel):
    job_id: int
    status: str
    client_confirmation_status: str | None
    carrier_confirmation_status: str | None


class TrackingCompletionActionResponse(BaseModel):
    job_id: int
    status: str
    client_completion_status: str | None
    carrier_completion_status: str | None
