from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from noshow_db.models.admin import AdminAuditLog

LOGIN = "login"
LOGIN_FAILED = "login_failed"
LOGIN_LOCKED = "login_locked"
LOGOUT = "logout"


def record(
    session: Session,
    action: str,
    email: str,
    client_ip: str,
    at: datetime,
    admin_id: int | None = None,
    detail: str | None = None,
) -> None:
    session.add(
        AdminAuditLog(
            admin_id=admin_id,
            email=email,
            action=action,
            detail=detail,
            client_ip=client_ip,
            created_at=at,
        )
    )


def recent_failures(session: Session, email: str, client_ip: str, since: datetime) -> int:
    """Failed logins of the email or from the client address since a moment."""
    return session.scalar(
        select(func.count())
        .select_from(AdminAuditLog)
        .where(
            AdminAuditLog.action == LOGIN_FAILED,
            AdminAuditLog.created_at >= since,
            or_(AdminAuditLog.email == email, AdminAuditLog.client_ip == client_ip),
        )
    )


def is_locked(
    session: Session, email: str, client_ip: str, now: datetime, limit: int, minutes: int
) -> bool:
    return recent_failures(session, email, client_ip, now - timedelta(minutes=minutes)) >= limit
