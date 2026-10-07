from ipaddress import IPv4Network, IPv6Network, ip_network
from typing import Annotated
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Network = IPv4Network | IPv6Network


class Settings(BaseSettings):
    """Admin service settings read from ADMIN_* environment variables."""

    model_config = SettingsConfigDict(env_prefix="ADMIN_")

    # Clients outside these networks get 403 before any page, including the login page
    allowed_networks: Annotated[list[Network], NoDecode] = Field(
        default_factory=lambda: [ip_network("127.0.0.0/8"), ip_network("::1/128")]
    )
    overbooking_service_url: str = "http://localhost:8001"
    session_minutes: int = Field(60, ge=5, le=24 * 60)
    # Only sent over HTTPS; browsers also accept it on http://localhost
    cookie_secure: bool = True
    # Failed logins of one email or one client address within the window lock the login
    max_failed_logins: int = Field(5, ge=1)
    lockout_minutes: int = Field(15, ge=1)
    clinic_timezone: ZoneInfo = ZoneInfo("Europe/Istanbul")
    dashboard_days: int = Field(7, ge=1, le=31)

    @field_validator("allowed_networks", mode="before")
    @classmethod
    def parse_networks(cls, value: object) -> object:
        # Comma-separated CIDR list, e.g. "127.0.0.0/8,10.0.0.0/8"
        if isinstance(value, str):
            return [ip_network(part.strip()) for part in value.split(",") if part.strip()]
        return value


settings = Settings()
