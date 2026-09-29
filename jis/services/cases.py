"""Case service: registration with CIN generation (S1) and the outcome of
each hearing (S2).

Every hearing starts SCHEDULED and ends as exactly one of:
  * ADJOURNED  (reason recorded)              -> registrar books the next date
  * HELD       (proceedings recorded)         -> registrar books the next date
  * HELD + judgment -> the case becomes CLOSED and is kept forever
Booking a date is the Scheduling service's job (services/scheduling.py).
"""

from datetime import date

import psycopg

from .. import clock
from ..errors import BadRequest, Conflict, NotFound
from ..schemas import CaseCreate

CASE_COLUMNS = """cin, defendant_name, defendant_address, crime_type, crime_date,
    crime_location, arresting_officer, arrest_date, presiding_judge, public_prosecutor,
    defense_lawyer, start_date, expected_completion_date, status, judgment_date,
    judgment_summary"""

HEARING_COLUMNS = """hearing_id, cin, hearing_date, slot, status, adjournment_reason,
    proceeding_summary"""


def register_case(conn: psycopg.Connection, data: CaseCreate) -> dict:
    """Generates the next CIN (YYYY-NNNNNN) and stores the case as PENDING.

    The sequence upsert locks this year's counter row until the transaction
    ends, so two registrars can never get the same number, and if the case
    insert fails the counter increment is rolled back too (no gaps).
    """
    year = clock.today().year
    with conn.transaction():
        seq = conn.execute(
            """INSERT INTO cin_sequences (year, last_number) VALUES (%s, 1)
               ON CONFLICT (year) DO UPDATE SET last_number = cin_sequences.last_number + 1
               RETURNING last_number""",
            (year,),
        ).fetchone()
        cin = f"{year}-{seq['last_number']:06d}"
        return conn.execute(
            f"""INSERT INTO cases (
                    cin, defendant_name, defendant_address, crime_type, crime_date,
                    crime_location, arresting_officer, arrest_date, presiding_judge,
                    public_prosecutor, defense_lawyer, start_date, expected_completion_date)
                VALUES (
                    %(cin)s, %(defendant_name)s, %(defendant_address)s, %(crime_type)s,
                    %(crime_date)s, %(crime_location)s, %(arresting_officer)s, %(arrest_date)s,
                    %(presiding_judge)s, %(public_prosecutor)s, %(defense_lawyer)s,
                    %(start_date)s, %(expected_completion_date)s)
                RETURNING {CASE_COLUMNS}""",
            {"cin": cin, **data.model_dump()},
        ).fetchone()


def get_case(conn: psycopg.Connection, cin: str) -> dict:
    case = conn.execute(f"SELECT {CASE_COLUMNS} FROM cases WHERE cin = %s", (cin,)).fetchone()
    if case is None:
        raise NotFound(f"No case with CIN {cin}")
    return case


def get_hearings(conn: psycopg.Connection, cin: str) -> list[dict]:
    return conn.execute(
        f"SELECT {HEARING_COLUMNS} FROM hearings WHERE cin = %s ORDER BY hearing_date, slot",
        (cin,),
    ).fetchall()


def _lock_scheduled_hearing(conn: psycopg.Connection, hearing_id: int) -> dict:
    """Must be called inside a transaction."""
    hearing = conn.execute(
        f"SELECT {HEARING_COLUMNS} FROM hearings WHERE hearing_id = %s FOR UPDATE",
        (hearing_id,),
    ).fetchone()
    if hearing is None:
        raise NotFound(f"No hearing with id {hearing_id}")
    if hearing["status"] != "SCHEDULED":
        raise Conflict(f"The outcome of hearing {hearing_id} is already recorded "
                       f"({hearing['status']})")
    if hearing["hearing_date"] > clock.today():
        raise BadRequest(f"Hearing {hearing_id} is on {hearing['hearing_date']}; "
                         "its outcome can only be recorded on or after that date")
    return hearing


def record_adjournment(conn: psycopg.Connection, hearing_id: int, reason: str) -> dict:
    with conn.transaction():
        _lock_scheduled_hearing(conn, hearing_id)
        return conn.execute(
            f"""UPDATE hearings SET status = 'ADJOURNED', adjournment_reason = %s
                WHERE hearing_id = %s RETURNING {HEARING_COLUMNS}""",
            (reason, hearing_id),
        ).fetchone()


def record_proceedings(conn: psycopg.Connection, hearing_id: int, summary: str) -> dict:
    with conn.transaction():
        _lock_scheduled_hearing(conn, hearing_id)
        return conn.execute(
            f"""UPDATE hearings SET status = 'HELD', proceeding_summary = %s
                WHERE hearing_id = %s RETURNING {HEARING_COLUMNS}""",
            (summary, hearing_id),
        ).fetchone()


def close_case(conn: psycopg.Connection, hearing_id: int, proceedings_summary: str,
               judgment_summary: str, judgment_date: date | None) -> dict:
    """Judgment delivered: marks the hearing HELD and closes the case, in one
    transaction."""
    with conn.transaction():
        hearing = _lock_scheduled_hearing(conn, hearing_id)
        judgment_date = judgment_date or hearing["hearing_date"]
        if not hearing["hearing_date"] <= judgment_date <= clock.today():
            raise BadRequest("judgment_date must be between the hearing date and today")
        conn.execute(
            """UPDATE hearings SET status = 'HELD', proceeding_summary = %s
               WHERE hearing_id = %s""",
            (proceedings_summary, hearing_id),
        )
        return conn.execute(
            """UPDATE cases SET status = 'CLOSED', judgment_summary = %s, judgment_date = %s
               WHERE cin = %s
               RETURNING cin, status, judgment_date, judgment_summary""",
            (judgment_summary, judgment_date, hearing["cin"]),
        ).fetchone()
