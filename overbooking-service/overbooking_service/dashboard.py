from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from noshow_db.models.core import Doctor
from overbooking_service.config import KpiSettings, settings
from overbooking_service.dependencies import get_kpi_settings, get_now, get_session
from overbooking_service.kpi import doctor_kpis

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    kpi: Annotated[KpiSettings, Depends(get_kpi_settings)],
    now: Annotated[datetime, Depends(get_now)],
    doctor_id: Annotated[int | None, Query(gt=0)] = None,
    day: Annotated[date | None, Query(alias="date")] = None,
) -> HTMLResponse:
    doctors = list(session.scalars(select(Doctor).order_by(Doctor.full_name)))
    selected = next((d for d in doctors if d.id == doctor_id), doctors[0] if doctors else None)
    day = day or now.astimezone(settings.clinic_timezone).date()

    # Daily KPIs for the period ending on the selected date
    days = []
    if selected is not None:
        for offset in range(kpi.dashboard_days - 1, -1, -1):
            current = day - timedelta(days=offset)
            days.append({"date": current, "kpis": doctor_kpis(session, selected.id, current, kpi)})

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "doctors": doctors,
            "selected": selected,
            "day": day,
            "today": days[-1]["kpis"] if days else None,
            "days": days,
            "chart": [
                {
                    "date": d["date"].isoformat(),
                    "utilization": round(d["kpis"].utilization * 100, 1),
                    "idle": round(d["kpis"].idle_minutes, 1),
                    "overtime": round(d["kpis"].overtime_minutes, 1),
                }
                for d in days
                if d["kpis"] is not None
            ],
            "service_minutes": kpi.service_minutes,
        },
    )
