from pathlib import Path

from pydantic_settings import BaseSettings

SERVICE_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Service settings read from environment variables."""

    model_dir: Path = SERVICE_ROOT / "models"


settings = Settings()
