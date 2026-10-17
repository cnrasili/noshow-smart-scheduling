from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select

from admin_service.dependencies import AppSettings, CurrentAdmin, DbSession, Now, get_overbooking
from admin_service.overbooking import OverbookingClient, OverbookingUnavailable
from admin_service.templating import templates
from noshow_db.models.admin import AdminAuditLog
from noshow_db.models.core import Doctor, Patient
from noshow_db.models.service import Message

router = APIRouter()

AUDIT_ROWS = 100
SMS_ROWS = 100


@router.get("/")
def home(admin: CurrentAdmin) -> Response:
    return RedirectResponse("/kpi", status_code=303)


@router.get("/kpi", response_class=HTMLResponse)
def kpi_page(
    request: Request,
    admin: CurrentAdmin,
    session: DbSession,
    now: Now,
    app_settings: AppSettings,
    overbooking: Annotated[OverbookingClient, Depends(get_overbooking)],
    doctor_id: Annotated[int | None, Query(gt=0)] = None,
    day: Annotated[date | None, Query(alias="date")] = None,
) -> Response:
    doctors = list(session.scalars(select(Doctor).order_by(Doctor.full_name)))
    selected = next((d for d in doctors if d.id == doctor_id), doctors[0] if doctors else None)
    day = day or now.astimezone(app_settings.clinic_timezone).date()

    days, ab, error = [], None, None
    try:
        # Daily KPIs for the period ending on the selected date
        if selected is not None:
            for offset in range(app_settings.dashboard_days - 1, -1, -1):
                current = day - timedelta(days=offset)
                days.append({"date": current, "kpis": overbooking.kpi(selected.id, current)})
        ab = overbooking.ab_summary()
    except OverbookingUnavailable:
        days, error = [], "Randevu karar servisine ulaşılamıyor; göstergeler gösterilemiyor."

    return templates.TemplateResponse(
        request,
        "kpi.html",
        {
            "admin": admin,
            "doctors": doctors,
            "selected": selected,
            "day": day,
            "today": days[-1]["kpis"] if days else None,
            "days": days,
            "ab": ab,
            "error": error,
            "chart": [
                {
                    "date": d["date"].strftime("%d.%m"),
                    "utilization": round(d["kpis"]["utilization"] * 100, 1),
                    "idle": round(d["kpis"]["idle_minutes"], 1),
                    "overtime": round(d["kpis"]["overtime_minutes"], 1),
                }
                for d in days
                if d["kpis"] is not None
            ],
        },
    )


@router.get("/audit", response_class=HTMLResponse)
def audit_page(request: Request, admin: CurrentAdmin, session: DbSession) -> Response:
    rows = session.scalars(
        select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(AUDIT_ROWS)
    ).all()
    return templates.TemplateResponse(request, "audit.html", {"admin": admin, "rows": rows})


@router.get("/sms", response_class=HTMLResponse)
def sms_page(
    request: Request,
    admin: CurrentAdmin,
    session: DbSession,
    q: Annotated[str, Query(max_length=20)] = "",
) -> Response:
    # Demo SMS of the overbooking service, addressed by the dataset patient number
    query = (
        select(Message, Patient.patient_number)
        .outerjoin(Patient, Patient.id == Message.patient_id)
        .order_by(Message.send_at.desc(), Message.id.desc())
        .limit(SMS_ROWS)
    )
    if q := q.strip():
        # Wildcards in the search text match only themselves
        query = query.where(Patient.patient_number.startswith(q, autoescape=True))
    rows = session.execute(query).all()
    return templates.TemplateResponse(
        request, "sms.html", {"admin": admin, "rows": rows, "q": q, "limit": SMS_ROWS}
    )
