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
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise ValueError(
                "email is enabled but required settings are missing: "
                + ", ".join(missing)
            )

        return self


settings = Settings()
