from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from admin_service import turkish
from admin_service.config import settings
from admin_service.security import csrf_token

SESSION_COOKIE = "admin_session"

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def csrf(request: Request) -> str:
    """CSRF token of the current session for forms; empty before login."""
    token = request.cookies.get(SESSION_COOKIE)
    return csrf_token(token) if token else ""


templates.env.globals["csrf"] = csrf
templates.env.globals["audit_events"] = turkish.AUDIT_EVENTS
templates.env.globals["ab_groups"] = turkish.AB_GROUPS
templates.env.filters["long_date"] = turkish.long_date
templates.env.filters["decimal"] = turkish.decimal
templates.env.filters["percent"] = turkish.percent
templates.env.filters["clinic_time"] = lambda moment: turkish.date_time(
    moment, settings.clinic_timezone
)
