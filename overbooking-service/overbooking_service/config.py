from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from overbooking_service.rules import OverbookingRule

SERVICE_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Service settings read from environment variables and config.yaml."""

    model_config = SettingsConfigDict(
        yaml_file=SERVICE_ROOT / "config.yaml",
        env_nested_delimiter="__",
    )

    model_dir: Path = SERVICE_ROOT / "models"
    overbooking: OverbookingRule

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
