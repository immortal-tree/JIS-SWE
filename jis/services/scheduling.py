"""Scheduling service: the CourtCalendar, vacant slots and booking a slot
for a hearing (S1, S2), plus the registrar's upkeep of the calendar (S5).

A booked slot IS a SCHEDULED hearing row, so a slot is vacant when no
SCHEDULED hearing holds it. A date is a working day when its weekday is a working weekday AND it is
not a holiday. The registrar maintains all three settings. Changes that
would strand an already-booked hearing are refused, with the list of
hearings to reschedule first.
"""

from datetime import date, time

import psycopg

from .. import clock
from ..errors import BadRequest, Conflict, NotFound
from .cases import HEARING_COLUMNS

_CLASH_COLUMNS = "h.hearing_id, h.cin, h.hearing_date, h.slot"


def get_calendar(conn: psycopg.Connection) -> dict:
    weekdays = [r["weekday"] for r in conn.execute(
        "SELECT weekday FROM working_weekdays ORDER BY weekday")]
    slots = [r["slot"] for r in conn.execute("SELECT slot FROM daily_slots ORDER BY slot")]
    holidays = conn.execute(
        "SELECT holiday_date, description FROM holidays ORDER BY holiday_date").fetchall()
    return {"working_weekdays": weekdays, "daily_slots": slots, "holidays": holidays}


def is_working_day(conn: psycopg.Connection, d: date) -> bool:
    row = conn.execute(
        """SELECT EXISTS (SELECT 1 FROM working_weekdays WHERE weekday = %s)
                  AND NOT EXISTS (SELECT 1 FROM holidays WHERE holiday_date = %s) AS ok""",
        (d.isoweekday(), d),
    ).fetchone()
    return row["ok"]


def get_vacant_slots(conn: psycopg.Connection, d: date) -> dict:
    if d < clock.today():
        raise BadRequest("That date is in the past")
    if not is_working_day(conn, d):
        return {"date": d, "working_day": False, "vacant_slots": []}
    rows = conn.execute(
        """SELECT s.slot FROM daily_slots s
           WHERE NOT EXISTS (SELECT 1 FROM hearings h
                             WHERE h.hearing_date = %s AND h.slot = s.slot
                               AND h.status = 'SCHEDULED')
           ORDER BY s.slot""",
        (d,),
    ).fetchall()
    return {"date": d, "working_day": True, "vacant_slots": [r["slot"] for r in rows]}


def schedule_hearing(conn: psycopg.Connection, cin: str, hearing_date: date, slot: time) -> dict:
    """Books a vacant slot on a working day and saves it as the case's next
    SCHEDULED hearing (bookSlot + saveHearing in S1 and S2)."""
    if hearing_date < clock.today():
        raise BadRequest("Hearings cannot be booked in the past")
    try:
        with conn.transaction():
            # Lock the case row so its status can't change while we book.
            case = conn.execute("SELECT cin, status FROM cases WHERE cin = %s FOR UPDATE",
                                (cin,)).fetchone()
            if case is None:
                raise NotFound(f"No case with CIN {cin}")
            if case["status"] == "CLOSED":
                raise Conflict(f"Case {cin} is closed; no further hearings can be booked")
            if not is_working_day(conn, hearing_date):
                raise BadRequest(f"{hearing_date} is not a working day")
            if conn.execute("SELECT 1 FROM daily_slots WHERE slot = %s", (slot,)).fetchone() is None:
                raise BadRequest(f"{slot.strftime('%H:%M')} is not one of the court's daily slots")
            existing = conn.execute(
                "SELECT hearing_date, slot FROM hearings WHERE cin = %s AND status = 'SCHEDULED'",
                (cin,),
            ).fetchone()
            if existing:
                raise Conflict(
                    f"Case {cin} already has a hearing on {existing['hearing_date']} at "
                    f"{existing['slot'].strftime('%H:%M')}. Record its outcome first.")
            return conn.execute(
                f"""INSERT INTO hearings (cin, hearing_date, slot) VALUES (%s, %s, %s)
                    RETURNING {HEARING_COLUMNS}""",
                (cin, hearing_date, slot),
            ).fetchone()
    except psycopg.errors.UniqueViolation as e:
        # The partial unique index caught a race the checks above could not see.
        if e.diag.constraint_name == "one_scheduled_hearing_per_case":
            raise Conflict(f"Case {cin} already has a scheduled hearing") from None
        raise Conflict("That slot was just booked for another case. "
                       "Refresh the vacant slots and pick another.") from None


def set_working_weekdays(conn: psycopg.Connection, weekdays: list[int]) -> dict:
    weekdays = sorted(set(weekdays))
    with conn.transaction():
        clashes = conn.execute(
            f"""SELECT {_CLASH_COLUMNS} FROM hearings h
                WHERE h.status = 'SCHEDULED' AND h.hearing_date >= %s
                  AND NOT (EXTRACT(ISODOW FROM h.hearing_date)::int = ANY(%s::int[]))
                ORDER BY h.hearing_date, h.slot""",
            (clock.today(), weekdays),
        ).fetchall()
        if clashes:
            raise Conflict("Hearings are booked on weekdays you are removing. "
                           "Reschedule them first.", data=clashes)
        conn.execute("DELETE FROM working_weekdays")
        conn.execute("INSERT INTO working_weekdays (weekday) SELECT unnest(%s::smallint[])",
                     (weekdays,))
    return get_calendar(conn)


def set_daily_slots(conn: psycopg.Connection, slots: list[time]) -> dict:
    slots = sorted(set(slots))
    with conn.transaction():
        clashes = conn.execute(
            f"""SELECT {_CLASH_COLUMNS} FROM hearings h
                WHERE h.status = 'SCHEDULED' AND h.hearing_date >= %s
                  AND NOT (h.slot = ANY(%s::time[]))
                ORDER BY h.hearing_date, h.slot""",
            (clock.today(), slots),
        ).fetchall()
        if clashes:
            raise Conflict("Hearings are booked in slots you are removing. "
                           "Reschedule them first.", data=clashes)
        conn.execute("DELETE FROM daily_slots")
        conn.execute("INSERT INTO daily_slots (slot) SELECT unnest(%s::time[])", (slots,))
    return get_calendar(conn)


def add_holiday(conn: psycopg.Connection, d: date, description: str) -> dict:
    if d < clock.today():
        raise BadRequest("Holidays can only be added for today or later")
    with conn.transaction():
        clashes = conn.execute(
            f"""SELECT {_CLASH_COLUMNS} FROM hearings h
                WHERE h.status = 'SCHEDULED' AND h.hearing_date = %s
                ORDER BY h.slot""",
            (d,),
        ).fetchall()
        if clashes:
            raise Conflict(f"{len(clashes)} hearing(s) are booked on {d}. "
                           "Reschedule them before declaring a holiday.", data=clashes)
        return conn.execute(
            """INSERT INTO holidays (holiday_date, description) VALUES (%s, %s)
               ON CONFLICT (holiday_date) DO UPDATE SET description = EXCLUDED.description
               RETURNING holiday_date, description""",
            (d, description.strip()),
        ).fetchone()


def remove_holiday(conn: psycopg.Connection, d: date) -> None:
    with conn.transaction():
        row = conn.execute("DELETE FROM holidays WHERE holiday_date = %s RETURNING holiday_date",
                           (d,)).fetchone()
    if row is None:
        raise NotFound(f"{d} is not a holiday")
