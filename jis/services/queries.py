"""Query service: registrar queries (a)–(d) from the problem statement (S4).
Read-only: nothing here changes stored data."""

from datetime import date

import psycopg

from ..errors import BadRequest, NotFound


def get_pending_cases(conn: psycopg.Connection) -> list[dict]:
    """(a) All pending cases, sorted by CIN."""
    return conn.execute(
        """SELECT cin, start_date, defendant_name, defendant_address, crime_type,
                  crime_date, crime_location, defense_lawyer, public_prosecutor,
                  presiding_judge
           FROM cases WHERE status = 'PENDING'
           ORDER BY cin"""
    ).fetchall()


def get_resolved_cases(conn: psycopg.Connection, date_from: date, date_to: date) -> list[dict]:
    """(b) Cases whose judgment falls in the period, in chronological order."""
    if date_to < date_from:
        raise BadRequest("'to' must not be before 'from'")
    return conn.execute(
        """SELECT cin, start_date, judgment_date, presiding_judge, judgment_summary
           FROM cases
           WHERE status = 'CLOSED' AND judgment_date BETWEEN %s AND %s
           ORDER BY start_date, cin""",
        (date_from, date_to),
    ).fetchall()


def get_hearings_on(conn: psycopg.Connection, d: date) -> list[dict]:
    """(c) Cases scheduled for hearing on a given date."""
    return conn.execute(
        """SELECT h.hearing_id, h.slot, c.cin, c.defendant_name, c.crime_type,
                  c.presiding_judge, c.public_prosecutor, c.defense_lawyer
           FROM hearings h JOIN cases c ON c.cin = h.cin
           WHERE h.hearing_date = %s AND h.status = 'SCHEDULED'
           ORDER BY h.slot""",
        (d,),
    ).fetchall()


def get_case_status(conn: psycopg.Connection, cin: str) -> dict:
    """(d) Status of one case: status, last hearing outcome, next hearing."""
    row = conn.execute(
        """SELECT c.cin, c.status, c.judgment_date,
                  (SELECT row_to_json(x) FROM (
                       SELECT hearing_id, hearing_date, slot, status,
                              adjournment_reason, proceeding_summary
                       FROM hearings
                       WHERE cin = c.cin AND status <> 'SCHEDULED'
                       ORDER BY hearing_date DESC, slot DESC LIMIT 1) x) AS last_hearing,
                  (SELECT row_to_json(x) FROM (
                       SELECT hearing_id, hearing_date, slot
                       FROM hearings
                       WHERE cin = c.cin AND status = 'SCHEDULED') x) AS next_hearing
           FROM cases c WHERE c.cin = %s""",
        (cin,),
    ).fetchone()
    if row is None:
        raise NotFound(f"No case with CIN {cin}")
    return row
