"""Account management screens: patient and doctor lists, account creation, password reset.

Lists are read from the database; creating accounts and resetting passwords go through the
web backend's internal account API, which owns the account rules.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import func, or_, select
from starlette.datastructures import FormData

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
from admin_service.turkish import SHORT_WEEKDAYS, WEEKDAYS
from noshow_db.models.admin import AdminUser
from noshow_db.models.core import Doctor, DoctorSchedule, Patient, UserAccount

router = APIRouter()

LIST_LIMIT = 50
PATIENT_FLAGS = {
    "scholarship": "Sosyal yardım alıyor",
    "hipertension": "Hipertansiyon",
    "diabetes": "Diyabet",
    "alcoholism": "Alkol bağımlılığı",
}
DISABLED = "Hesap yönetimi kapalı: INTERNAL_API_TOKEN ayarlanmamış ya da kabul edilmiyor."
NATIONAL_ID = "T.C. kimlik numarası"
EMAIL = "E-posta"

PATIENT_CREATED = "patient_created"
DOCTOR_CREATED = "doctor_created"
PASSWORD_RESET = "password_reset"
ACCOUNT_REJECTED = "account_rejected"


async def form_data(request: Request) -> FormData:
    return await request.form()


Form = Annotated[FormData, Depends(form_data)]


def render(request: Request, name: str, context: dict, status_code: int = 200) -> Response:
    return templates.TemplateResponse(request, name, context, status_code=status_code)


def text(form: FormData, name: str) -> str:
    return str(form.get(name, "")).strip()


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
        query = query.where(
            or_(
                Patient.national_id.startswith(q), func.lower(Patient.full_name).contains(q.lower())
            )
        )
    rows = session.execute(query).all()
    return render(
        request,
        "patients.html",
        {"admin": admin, "rows": rows, "q": q, "limit": LIST_LIMIT, "enabled": accounts.enabled},
    )


@router.get("/doctors", response_class=HTMLResponse)
def doctors_page(
    request: Request, admin: CurrentAdmin, session: DbSession, accounts: Accounts
) -> Response:
    rows = session.execute(
        select(Doctor, UserAccount.id, UserAccount.email)
        .outerjoin(UserAccount, UserAccount.doctor_id == Doctor.id)
        .order_by(Doctor.specialty, Doctor.full_name)
    ).all()
    hours: dict[int, list[str]] = {}
    for schedule in session.scalars(
        select(DoctorSchedule).order_by(DoctorSchedule.doctor_id, DoctorSchedule.weekday)
    ):
        day = SHORT_WEEKDAYS[schedule.weekday]
        hours.setdefault(schedule.doctor_id, []).append(
            f"{day} {schedule.start_time:%H:%M}–{schedule.end_time:%H:%M}"
        )
    return render(
        request,
        "doctors.html",
        {"admin": admin, "rows": rows, "hours": hours, "enabled": accounts.enabled},
    )


def patient_form(request: Request, admin: AdminUser, values: dict, error: str | None = None):
    return render(
        request,
        "patient_new.html",
        {"admin": admin, "values": values, "flags": PATIENT_FLAGS, "error": error},
        status_code=400 if error else 200,
    )


@router.get("/patients/new", response_class=HTMLResponse)
def new_patient_page(request: Request, admin: CurrentAdmin, accounts: Accounts) -> Response:
    return patient_form(request, admin, {}, None if accounts.enabled else DISABLED)


@router.post("/patients/new", dependencies=[Depends(verify_csrf)])
def create_patient(
    request: Request,
    admin: CurrentAdmin,
    session: DbSession,
    accounts: Accounts,
    now: Now,
    form: Form,
) -> Response:
    values = {name: text(form, name) for name in ["national_id", "full_name", "email", "age"]}
    values |= {"gender": text(form, "gender"), "handcap": text(form, "handcap") or "0"}
    values |= {flag: form.get(flag) == "on" for flag in PATIENT_FLAGS}
    try:
        age, handcap = int(values["age"]), int(values["handcap"])
    except ValueError:
        return patient_form(request, admin, values, "Yaş ve engellilik düzeyi tam sayı olmalıdır.")

    password = generate_password()
    patient = {**values, "age": age, "handcap": handcap, "password": password}
    try:
        created = accounts.create_patient(patient)
    except AccountsUnavailable:
        return patient_form(request, admin, values, DISABLED)
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
        return patient_form(request, admin, values, str(exc))

    detail = f"hesap {created['account_id']}, hasta {created['patient_id']}"
    audit.record(session, PATIENT_CREATED, admin.email, client_ip(request), now, admin.id, detail)
    session.commit()
    return render(
        request,
        "credentials.html",
        {
            "admin": admin,
            "title": "Hasta hesabı açıldı",
            "name": created["full_name"],
            "login": created["national_id"],
            "login_label": NATIONAL_ID,
            "password": password,
        },
    )


def doctor_form(
    request: Request, admin: AdminUser, session, values: dict, error: str | None = None
) -> Response:
    specialties = session.scalars(
        select(Doctor.specialty).where(Doctor.specialty.is_not(None)).distinct()
    ).all()
    return render(
        request,
        "doctor_new.html",
        {
            "admin": admin,
            "values": values,
            "weekdays": list(enumerate(WEEKDAYS)),
            "specialties": sorted(specialties),
            "error": error,
        },
        status_code=400 if error else 200,
    )


@router.get("/doctors/new", response_class=HTMLResponse)
def new_doctor_page(
    request: Request, admin: CurrentAdmin, session: DbSession, accounts: Accounts
) -> Response:
    return doctor_form(request, admin, session, {}, None if accounts.enabled else DISABLED)


@router.post("/doctors/new", dependencies=[Depends(verify_csrf)])
def create_doctor(
    request: Request,
    admin: CurrentAdmin,
    session: DbSession,
    accounts: Accounts,
    now: Now,
    form: Form,
) -> Response:
    values = {name: text(form, name) for name in ["full_name", "specialty", "email"]}
    working_hours, missing = [], []
    for weekday, day in enumerate(WEEKDAYS):
        start, end = text(form, f"start_{weekday}"), text(form, f"end_{weekday}")
        values[f"start_{weekday}"], values[f"end_{weekday}"] = start, end
        if start and end:
            working_hours.append({"weekday": weekday, "start_time": start, "end_time": end})
        elif start or end:
            missing.append(day)
    if missing:
        error = f"{', '.join(missing)} için başlangıç ve bitiş saatini birlikte girin."
        return doctor_form(request, admin, session, values, error)
    if not working_hours:
        return doctor_form(request, admin, session, values, "En az bir çalışma günü girin.")

    password = generate_password()
    doctor = {
        "full_name": values["full_name"],
        "specialty": values["specialty"],
        "email": values["email"],
        "password": password,
        "working_hours": working_hours,
    }
    try:
        created = accounts.create_doctor(doctor)
    except AccountsUnavailable:
        return doctor_form(request, admin, session, values, DISABLED)
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
        return doctor_form(request, admin, session, values, str(exc))

    detail = f"hesap {created['account_id']}, hekim {created['doctor_id']}"
    audit.record(session, DOCTOR_CREATED, admin.email, client_ip(request), now, admin.id, detail)
    session.commit()
    return render(
        request,
        "credentials.html",
        {
            "admin": admin,
            "title": "Hekim hesabı açıldı",
            "name": created["full_name"],
            "login": created["email"],
            "login_label": EMAIL,
            "password": password,
            "note": f"Önümüzdeki iki hafta için {created['slots_created']} slot açıldı.",
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
        select(UserAccount, Patient, Doctor)
        .outerjoin(Patient, Patient.id == UserAccount.patient_id)
        .outerjoin(Doctor, Doctor.id == UserAccount.doctor_id)
        .where(UserAccount.id == account_id)
    ).first()
    if row is None:
        return render(request, "message.html", {"admin": admin, "error": "Hesap bulunamadı."}, 404)
    account, patient, doctor = row

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
            "name": patient.full_name if patient else doctor.full_name,
            "login": patient.national_id if patient else account.email,
            "login_label": NATIONAL_ID if patient else EMAIL,
            "password": password,
            "note": "Hesabın açık oturumları kapatıldı.",
        },
    )
