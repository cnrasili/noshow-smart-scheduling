import hmac
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Form, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from admin_service.accounts_client import AccountsClient
from admin_service.config import Settings, settings
from admin_service.overbooking import OverbookingClient
from admin_service.security import csrf_token, hash_token
from admin_service.templating import SESSION_COOKIE
from noshow_db import SessionLocal
from noshow_db.models.admin import AdminSession, AdminUser


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def get_settings() -> Settings:
    return settings


def get_now() -> datetime:
    return datetime.now(UTC)


def get_overbooking(app_settings: Annotated[Settings, Depends(get_settings)]) -> OverbookingClient:
    return OverbookingClient(app_settings.overbooking_service_url)


def get_accounts(app_settings: Annotated[Settings, Depends(get_settings)]) -> AccountsClient:
    return AccountsClient(app_settings.web_backend_url, app_settings.internal_api_token)


def verify_csrf(
    request: Request, token: Annotated[str, Form(alias="csrf_token", max_length=128)] = ""
) -> None:
    """Reject a form that was not rendered for the current session."""
    session_token = request.cookies.get(SESSION_COOKIE, "")
    if not session_token or not hmac.compare_digest(token, csrf_token(session_token)):
        raise HTTPException(403, "Invalid form token; reload the page and try again")


def as_utc(value: datetime) -> datetime:
    # SQLite returns naive datetimes; they are stored in UTC
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class NotLoggedIn(Exception):
    """Raised when a page needs a logged-in administrator."""


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def current_admin(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    now: Annotated[datetime, Depends(get_now)],
) -> AdminUser:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise NotLoggedIn
    row = session.execute(
        select(AdminSession, AdminUser)
        .join(AdminUser, AdminUser.id == AdminSession.admin_id)
        .where(AdminSession.token_hash == hash_token(token))
    ).first()
    if row is None or as_utc(row[0].expires_at) <= now:
        raise NotLoggedIn
    return row[1]


CurrentAdmin = Annotated[AdminUser, Depends(current_admin)]
DbSession = Annotated[Session, Depends(get_session)]
Now = Annotated[datetime, Depends(get_now)]
AppSettings = Annotated[Settings, Depends(get_settings)]
Accounts = Annotated[AccountsClient, Depends(get_accounts)]
