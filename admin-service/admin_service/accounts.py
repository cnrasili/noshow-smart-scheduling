"""Account management screens: the patient list, the department, patient accounts, passwords.

Lists are read from the database; creating accounts and resetting passwords go through the
web backend's internal account API, which owns the account rules.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import func, or_, select

from admin_service import audit
from admin_service.accounts_client import AccountRejected, AccountsUnavailable
from admin_service.dependencies import (
    Accounts,
    CurrentAdmin,
    DbSession,
    Now,
    client_ip,
    verify_csrf,
)
from admin_service.security import generate_password
from admin_service.templating import templates
from admin_service.turkish import DEPARTMENT_NAME, WEEKDAYS
from noshow_db.models.core import DoctorSchedule, Patient, UserAccount

router = APIRouter()

LIST_LIMIT = 50
DISABLED = "Hesap yönetimi kapalı: INTERNAL_API_TOKEN ayarlanmamış ya da kabul edilmiyor."
NOT_IN_DATASET = "Bu hasta veri setinde yok; giriş hesabı yalnızca veri setindeki hastalara açılır."
PATIENT_NUMBER = "Hasta numarası"
LOGIN_NAME = "Giriş adı"

PATIENT_CREATED = "patient_created"
PASSWORD_RESET = "password_reset"
ACCOUNT_REJECTED = "account_rejected"


def render(request: Request, name: str, context: dict, status_code: int = 200) -> Response:
    return templates.TemplateResponse(request, name, context, status_code=status_code)


@router.get("/patients", response_class=HTMLResponse)
def patients_page(
    request: Request,
    admin: CurrentAdmin,
    session: DbSession,
    accounts: Accounts,
    q: Annotated[str, Query(max_length=100)] = "",
) -> Response:
    query = (
        select(Patient, UserAccount.id)
        .outerjoin(UserAccount, UserAccount.patient_id == Patient.id)
        .order_by(Patient.full_name, Patient.id)
        .limit(LIST_LIMIT)
    )
    if q := q.strip():
        # Wildcards in the search text match only themselves
        query = query.where(
            or_(
                Patient.patient_number.startswith(q, autoescape=True),
                func.lower(Patient.full_name).contains(q.lower(), autoescape=True),
            )
        )
    rows = session.execute(query).all()
    return render(
        request,
        "patients.html",
        {"admin": admin, "rows": rows, "q": q, "limit": LIST_LIMIT, "enabled": accounts.enabled},
    )


@router.get("/department", response_class=HTMLResponse)
def department_page(
    request: Request, admin: CurrentAdmin, session: DbSession, accounts: Accounts
) -> Response:
    # The department's working hours and staff account belong to its record in doctors
    hours = [
        (WEEKDAYS[schedule.weekday], f"{schedule.start_time:%H:%M}–{schedule.end_time:%H:%M}")
        for schedule in session.scalars(
            select(DoctorSchedule).order_by(DoctorSchedule.weekday, DoctorSchedule.start_time)
        )
    ]
    staff = session.execute(
        select(UserAccount.id, UserAccount.email)
        .where(UserAccount.doctor_id.is_not(None))
        .order_by(UserAccount.id)
    ).all()
    return render(
        request,
        "department.html",
        {"admin": admin, "hours": hours, "staff": staff, "enabled": accounts.enabled},
    )


@router.post("/patients/{patient_id}/account", dependencies=[Depends(verify_csrf)])
def open_patient_account(
    request: Request,
    patient_id: int,
    admin: CurrentAdmin,
    session: DbSession,
    accounts: Accounts,
    now: Now,
) -> Response:
    patient = session.get(Patient, patient_id)
    if patient is None or patient.patient_number is None:
        return render(request, "message.html", {"admin": admin, "error": NOT_IN_DATASET}, 404)

    password = generate_password()
    try:
        opened = accounts.open_patient_account(patient.patient_number, password)
    except AccountsUnavailable:
        return render(request, "message.html", {"admin": admin, "error": DISABLED}, 400)
    except AccountRejected as exc:
        audit.record(
            session,
            ACCOUNT_REJECTED,
            admin.email,
            client_ip(request),
            now,
            admin.id,
            str(exc)[:255],
        )
        session.commit()
        return render(request, "message.html", {"admin": admin, "error": str(exc)}, 400)

    detail = f"hesap {opened['account_id']}, hasta {opened['patient_id']}"
    audit.record(session, PATIENT_CREATED, admin.email, client_ip(request), now, admin.id, detail)
    session.commit()
    return render(
        request,
        "credentials.html",
        {
            "admin": admin,
            "title": "Giriş hesabı açıldı",
            "name": opened["full_name"],
            "login": opened["patient_number"],
            "login_label": PATIENT_NUMBER,
            "password": password,
        },
    )


@router.post("/accounts/{account_id}/password", dependencies=[Depends(verify_csrf)])
def reset_password(
    request: Request,
    account_id: int,
    admin: CurrentAdmin,
    session: DbSession,
    accounts: Accounts,
    now: Now,
) -> Response:
    row = session.execute(
        select(UserAccount, Patient)
        .outerjoin(Patient, Patient.id == UserAccount.patient_id)
        .where(UserAccount.id == account_id)
    ).first()
    if row is None:
        return render(request, "message.html", {"admin": admin, "error": "Hesap bulunamadı."}, 404)
    account, patient = row

    password = generate_password()
    try:
        accounts.reset_password(account_id, password)
    except (AccountsUnavailable, AccountRejected) as exc:
        error = DISABLED if isinstance(exc, AccountsUnavailable) else str(exc)
        return render(request, "message.html", {"admin": admin, "error": error}, 400)

    audit.record(
        session,
        PASSWORD_RESET,
        admin.email,
        client_ip(request),
        now,
        admin.id,
        f"hesap {account_id}",
    )
    session.commit()
    return render(
        request,
        "credentials.html",
        {
            "admin": admin,
            "title": "Şifre sıfırlandı",
            "password_label": "Yeni şifre",
            "name": patient.full_name if patient else DEPARTMENT_NAME,
            "login": (patient.patient_number or "—") if patient else account.email,
            "login_label": PATIENT_NUMBER if patient else LOGIN_NAME,
            "password": password,
            "note": "Hesabın açık oturumları kapatıldı.",
        },
    )
