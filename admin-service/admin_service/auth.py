from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import delete, select

from admin_service import audit
from admin_service.dependencies import (
    SESSION_COOKIE,
    AppSettings,
    CurrentAdmin,
    DbSession,
    Now,
    client_ip,
    verify_csrf,
)
from admin_service.security import DUMMY_HASH, hash_token, new_token, verify_password
from admin_service.templating import templates
from noshow_db.models.admin import AdminSession, AdminUser

router = APIRouter()

WRONG_CREDENTIALS = "Wrong email or password."
LOCKED = "Too many failed logins. Try again later."


def login_page(request: Request, error: str | None = None, status_code: int = 200) -> Response:
    return templates.TemplateResponse(
        request, "login.html", {"error": error}, status_code=status_code
    )


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request) -> Response:
    return login_page(request)


@router.post("/login")
def login(
    request: Request,
    email: Annotated[str, Form(max_length=255)],
    password: Annotated[str, Form(max_length=255)],
    session: DbSession,
    now: Now,
    app_settings: AppSettings,
) -> Response:
    email = email.strip().lower()
    ip = client_ip(request)
    if audit.is_locked(
        session, email, ip, now, app_settings.max_failed_logins, app_settings.lockout_minutes
    ):
        audit.record(session, audit.LOGIN_LOCKED, email, ip, now)
        session.commit()
        return login_page(request, LOCKED, status_code=429)

    admin = session.scalar(select(AdminUser).where(AdminUser.email == email))
    if not verify_password(password, admin.password_hash if admin else DUMMY_HASH) or not admin:
        audit.record(session, audit.LOGIN_FAILED, email, ip, now, admin.id if admin else None)
        session.commit()
        return login_page(request, WRONG_CREDENTIALS, status_code=401)

    token = new_token()
    expires_at = now + timedelta(minutes=app_settings.session_minutes)
    # Expired sessions of this administrator are removed at each login
    session.execute(
        delete(AdminSession).where(
            AdminSession.admin_id == admin.id, AdminSession.expires_at <= now
        )
    )
    session.add(
        AdminSession(admin_id=admin.id, token_hash=hash_token(token), expires_at=expires_at)
    )
    admin.last_login_at = now
    audit.record(session, audit.LOGIN, email, ip, now, admin.id)
    session.commit()

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=app_settings.session_minutes * 60,
        httponly=True,
        secure=app_settings.cookie_secure,
        samesite="strict",
        path="/",
    )
    return response


@router.post("/logout", dependencies=[Depends(verify_csrf)])
def logout(request: Request, admin: CurrentAdmin, session: DbSession, now: Now) -> Response:
    token = request.cookies.get(SESSION_COOKIE, "")
    session.execute(delete(AdminSession).where(AdminSession.token_hash == hash_token(token)))
    audit.record(session, audit.LOGOUT, admin.email, client_ip(request), now, admin.id)
    session.commit()
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response
