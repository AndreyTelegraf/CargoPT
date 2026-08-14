from pydantic import Field
from pydantic import SecretStr
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    database_url: str
    environment: str = "local"
    log_level: str = "INFO"
    self_ad_enabled: bool = True
    self_ad_chat_username: str = "baraholka_pt"
    self_ad_topic_id: int = 429
    self_ad_every_n: int = 9
    self_ad_state_path: str = "data/self_ad_counter.json"

    web_request_rate_limit_count: int = Field(default=20, gt=0)
    web_request_rate_limit_window_seconds: int = Field(default=3600, gt=0)
    web_request_max_body_bytes: int = Field(default=65536, gt=0)
    web_request_contact_daily_limit: int = Field(default=3, gt=0)
    location_search_rate_limit_count: int = Field(default=120, gt=0)
    location_search_rate_limit_window_seconds: int = Field(default=3600, gt=0)
    location_search_provider_url: str = (
        "https://nominatim.openstreetmap.org/search"
    )

    email_enabled: bool = False
    email_transport: str = "smtp"
    email_public_base_url: str = "https://cargopt.pt"
    email_from_name: str = "CargoPT"
    email_from_address: str = ""
    email_reply_to: str = ""
    email_smtp_host: str = ""
    email_smtp_port: int = Field(default=587, gt=0, le=65535)
    email_smtp_username: str = ""
    email_smtp_password: SecretStr = SecretStr("")
    email_smtp_starttls: bool = True
    email_smtp_use_tls: bool = False
    email_timeout_seconds: int = Field(default=15, gt=0)
    email_max_attempts: int = Field(default=5, gt=0)
    email_retry_base_seconds: int = Field(default=60, gt=0)

    meta_operations_enabled: bool = False
    meta_operations_inbound_token: SecretStr = SecretStr("")
    meta_operations_admin_username: str = ""
    meta_operations_admin_password: SecretStr = SecretStr("")
    meta_operations_telegram_chat_ids: str = ""
    meta_operations_alert_threshold: float = Field(default=0.6, ge=0, le=1)

    partner_outreach_enabled: bool = False
    partner_outreach_send_enabled: bool = False
    partner_outreach_daily_limit: int = Field(default=5, gt=0, le=25)
    partner_outreach_min_interval_minutes: int = Field(
        default=20,
        ge=5,
        le=1440,
    )
    partner_outreach_compliance_max_age_days: int = Field(
        default=35,
        gt=0,
        le=62,
    )
    partner_outreach_source_max_age_days: int = Field(
        default=90,
        gt=0,
        le=365,
    )
    partner_outreach_sender_signature: str = "Equipa CargoPT"
    partner_outreach_legal_identity: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_email_configuration(self) -> "Settings":
        if self.email_smtp_starttls and self.email_smtp_use_tls:
            raise ValueError(
                "EMAIL_SMTP_STARTTLS and EMAIL_SMTP_USE_TLS "
                "cannot both be enabled"
            )

        if not self.email_enabled:
            if self.partner_outreach_send_enabled:
                raise ValueError(
                    "PARTNER_OUTREACH_SEND_ENABLED requires EMAIL_ENABLED"
                )
            return self

        if self.email_transport != "smtp":
            raise ValueError("EMAIL_TRANSPORT must be smtp")

        required = {
            "EMAIL_FROM_ADDRESS": self.email_from_address,
            "EMAIL_SMTP_HOST": self.email_smtp_host,
            "EMAIL_SMTP_USERNAME": self.email_smtp_username,
            "EMAIL_SMTP_PASSWORD": (
                self.email_smtp_password.get_secret_value()
            ),
        }
        if self.partner_outreach_send_enabled:
            required["EMAIL_REPLY_TO"] = self.email_reply_to
            required["PARTNER_OUTREACH_LEGAL_IDENTITY"] = (
                self.partner_outreach_legal_identity
            )
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise ValueError(
                "email is enabled but required settings are missing: "
                + ", ".join(missing)
            )

        if self.partner_outreach_send_enabled and not self.partner_outreach_enabled:
            raise ValueError(
                "PARTNER_OUTREACH_SEND_ENABLED requires "
                "PARTNER_OUTREACH_ENABLED"
            )

        return self

    @property
    def meta_operations_chat_ids(self) -> tuple[int, ...]:
        result: list[int] = []
        for raw_item in self.meta_operations_telegram_chat_ids.split(","):
            item = raw_item.strip()
            if not item:
                continue
            if not item.lstrip("-").isdigit():
                raise ValueError(
                    "META_OPERATIONS_TELEGRAM_CHAT_IDS must contain integers"
                )
            result.append(int(item))
        return tuple(dict.fromkeys(result))


settings = Settings()
