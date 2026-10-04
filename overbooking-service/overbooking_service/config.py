from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from overbooking_service.rules import OverbookingRule

SERVICE_ROOT = Path(__file__).resolve().parents[1]


class ReminderSettings(BaseModel):
    """Confirmation and reminder message settings."""

    enabled: bool
    hours_before: float = Field(gt=0)
    dispatch_interval_seconds: int = Field(ge=1)
    max_attempts: int = Field(ge=1)


class AbTestSettings(BaseModel):
    """Reminder A/B test settings."""

    enabled: bool
    salt: str = Field(min_length=1)


class Settings(BaseSettings):
    """Service settings read from environment variables and config.yaml."""

    model_config = SettingsConfigDict(
        yaml_file=SERVICE_ROOT / "config.yaml",
        env_nested_delimiter="__",
    )

    model_dir: Path = SERVICE_ROOT / "models"
    # Slot dates follow the clinic's local calendar
    clinic_timezone: ZoneInfo
    overbooking: OverbookingRule
    reminders: ReminderSettings
    ab_test: AbTestSettings
    smtp_host: str | None = None
    smtp_port: int = 1025
    mail_from: str = "clinic@noshow.local"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Environment variables override config.yaml
        return (init_settings, env_settings, YamlConfigSettingsSource(settings_cls))


settings = Settings()
