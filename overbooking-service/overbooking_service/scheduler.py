from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler

from noshow_db import SessionLocal
from overbooking_service.config import settings
from overbooking_service.dispatcher import dispatch_due
from overbooking_service.sender import make_sender


def run_dispatch() -> None:
    with SessionLocal() as session:
        dispatch_due(
            session, make_sender(settings), datetime.now(UTC), settings.reminders.max_attempts
        )


def start_scheduler() -> BackgroundScheduler:
    """Start the periodic message dispatcher."""
    scheduler = BackgroundScheduler(timezone=UTC)
    scheduler.add_job(
        run_dispatch,
        "interval",
        seconds=settings.reminders.dispatch_interval_seconds,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    return scheduler
