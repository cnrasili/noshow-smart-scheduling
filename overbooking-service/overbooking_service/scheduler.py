from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from noshow_db import SessionLocal
from overbooking_service.config import settings
from overbooking_service.dispatcher import dispatch_due
from overbooking_service.recovery import recover_lost_bookings
from overbooking_service.sender import make_sender


def run_dispatch() -> None:
    with SessionLocal() as session:
        dispatch_due(
            session, make_sender(settings), datetime.now(UTC), settings.reminders.max_attempts
        )


def run_recovery() -> None:
    with SessionLocal() as session:
        recover_lost_bookings(
            session,
            datetime.now(UTC),
            timedelta(hours=settings.message_recovery.lookback_hours),
            settings.clinic_timezone,
            settings.reminders,
            settings.ab_test,
        )


def start_scheduler() -> BackgroundScheduler:
    """Start the periodic message dispatcher and the recovery of lost bookings."""
    scheduler = BackgroundScheduler(timezone=UTC)
    scheduler.add_job(
        run_dispatch,
        "interval",
        seconds=settings.reminders.dispatch_interval_seconds,
        max_instances=1,
        coalesce=True,
    )
    if settings.message_recovery.enabled:
        # The first run at startup covers bookings made while the service was down
        scheduler.add_job(
            run_recovery,
            "interval",
            seconds=settings.message_recovery.interval_seconds,
            next_run_time=datetime.now(UTC),
            max_instances=1,
            coalesce=True,
        )
    scheduler.start()
    return scheduler
