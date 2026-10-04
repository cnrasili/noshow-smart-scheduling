import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from overbooking_service import ab, booking, dashboard, events, kpi, predict
from overbooking_service.config import settings
from overbooking_service.predictor import Predictor
from overbooking_service.scheduler import start_scheduler

# Service logs, including messages from the console sender
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")
logging.getLogger("apscheduler").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.predictor = Predictor.load(settings.model_dir)
    scheduler = start_scheduler() if settings.reminders.enabled else None
    yield
    if scheduler is not None:
        scheduler.shutdown()


app = FastAPI(title="Overbooking Service", lifespan=lifespan)
app.include_router(predict.router)
app.include_router(booking.router)
app.include_router(events.router)
app.include_router(ab.router)
app.include_router(kpi.router)
app.include_router(dashboard.router)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
