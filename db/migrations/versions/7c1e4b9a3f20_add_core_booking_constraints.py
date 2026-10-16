"""Add core booking constraints

Revision ID: 7c1e4b9a3f20
Revises: d9027540a2c6
Create Date: 2026-10-03 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7c1e4b9a3f20"
down_revision: str | Sequence[str] | None = "d9027540a2c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Slot dates are calendar days in the clinic's local time
CLINIC_TIMEZONE = "Europe/Istanbul"

CHECK_CONSTRAINTS = [
    ("ck_patients_age_non_negative", "patients", "age >= 0"),
    ("ck_patients_handcap_non_negative", "patients", "handcap >= 0"),
    ("ck_slots_end_after_start", "slots", "end_at > start_at"),
    ("ck_slots_max_patients_positive", "slots", "max_patients >= 1"),
    ("ck_appointments_booked_before_date", "appointments", "booking_date <= appointment_date"),
]

SERVER_DEFAULTS = [
    ("patients", "scholarship", sa.Boolean(), sa.false()),
    ("patients", "hipertension", sa.Boolean(), sa.false()),
    ("patients", "diabetes", sa.Boolean(), sa.false()),
    ("patients", "alcoholism", sa.Boolean(), sa.false()),
    ("patients", "handcap", sa.Integer(), sa.text("0")),
    ("slots", "max_patients", sa.Integer(), sa.text("2")),
]

# Locks the slot row so concurrent bookings of one slot are checked one after another
CHECK_APPOINTMENT_SLOT = f"""
CREATE FUNCTION check_appointment_slot() RETURNS trigger AS $$
DECLARE
    slot_capacity integer;
    slot_day date;
    booked integer;
BEGIN
    SELECT max_patients, (start_at AT TIME ZONE '{CLINIC_TIMEZONE}')::date
      INTO slot_capacity, slot_day
      FROM slots
     WHERE id = NEW.slot_id
       FOR UPDATE;
    IF NOT FOUND THEN
        -- The foreign key reports the missing slot
        RETURN NEW;
    END IF;

    IF NEW.appointment_date <> slot_day THEN
        RAISE EXCEPTION 'appointment_date % does not match date % of slot %',
            NEW.appointment_date, slot_day, NEW.slot_id
            USING ERRCODE = 'check_violation';
    END IF;

    IF TG_OP = 'INSERT' OR NEW.slot_id <> OLD.slot_id THEN
        SELECT count(*) INTO booked FROM appointments WHERE slot_id = NEW.slot_id;
        IF booked >= slot_capacity THEN
            RAISE EXCEPTION 'slot % is full (% of % patients)',
                NEW.slot_id, booked, slot_capacity
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

# Keeps existing appointments valid when their slot is moved or shrunk
CHECK_SLOT_APPOINTMENTS = f"""
CREATE FUNCTION check_slot_appointments() RETURNS trigger AS $$
DECLARE
    booked integer;
BEGIN
    SELECT count(*) INTO booked FROM appointments WHERE slot_id = NEW.id;
    IF booked = 0 THEN
        RETURN NEW;
    END IF;

    IF (NEW.start_at AT TIME ZONE '{CLINIC_TIMEZONE}')::date
       <> (OLD.start_at AT TIME ZONE '{CLINIC_TIMEZONE}')::date THEN
        RAISE EXCEPTION 'slot % has appointments and cannot move to another date', NEW.id
            USING ERRCODE = 'check_violation';
    END IF;

    IF booked > NEW.max_patients THEN
        RAISE EXCEPTION 'slot % has % patients, more than max_patients %',
            NEW.id, booked, NEW.max_patients
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    for table, column, type_, default in SERVER_DEFAULTS:
        op.alter_column(table, column, existing_type=type_, server_default=default)

    for name, table, condition in CHECK_CONSTRAINTS:
        op.create_check_constraint(name, table, condition)

    op.execute(CHECK_APPOINTMENT_SLOT)
    op.execute(
        "CREATE TRIGGER appointments_check_slot "
        "BEFORE INSERT OR UPDATE OF slot_id, appointment_date ON appointments "
        "FOR EACH ROW EXECUTE FUNCTION check_appointment_slot()"
    )
    op.execute(CHECK_SLOT_APPOINTMENTS)
    op.execute(
        "CREATE TRIGGER slots_check_appointments "
        "BEFORE UPDATE OF start_at, max_patients ON slots "
        "FOR EACH ROW EXECUTE FUNCTION check_slot_appointments()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER slots_check_appointments ON slots")
    op.execute("DROP FUNCTION check_slot_appointments()")
    op.execute("DROP TRIGGER appointments_check_slot ON appointments")
    op.execute("DROP FUNCTION check_appointment_slot()")

    for name, table, _ in reversed(CHECK_CONSTRAINTS):
        op.drop_constraint(name, table, type_="check")

    for table, column, type_, _ in reversed(SERVER_DEFAULTS):
        op.alter_column(table, column, existing_type=type_, server_default=None)
