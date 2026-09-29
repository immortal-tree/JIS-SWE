"""Search service: keyword search of past (CLOSED) cases, and viewing one
case's full details (S3). Searching is free; when a lawyer opens a case,
the Billing service charges them."""

import psycopg

from ..errors import BadRequest, Forbidden
from . import billing
from .cases import get_case, get_hearings


def search_past_cases(conn: psycopg.Connection, keywords: str, limit: int = 50) -> list[dict]:
    """Closed cases matching the keywords anywhere in the case (defendant,
    crime, location, people, judgment) or in any hearing's proceedings /
    adjournment reason. Supports web-style queries: "exact phrase",
    -excluded, OR. A full CIN also matches."""
    keywords = keywords.strip()
    if not keywords:
        raise BadRequest("Enter at least one keyword")
    return conn.execute(
        """SELECT c.cin, c.crime_type, c.judgment_date
           FROM cases c, websearch_to_tsquery('english', %(q)s) query
           WHERE c.status = 'CLOSED'
             AND (c.search_vector @@ query
                  OR c.cin = %(q)s
                  OR EXISTS (SELECT 1 FROM hearings h
                             WHERE h.cin = c.cin AND h.search_vector @@ query))
           ORDER BY ts_rank(c.search_vector, query) DESC, c.cin DESC
           LIMIT %(limit)s""",
        {"q": keywords, "limit": limit},
    ).fetchall()


def view_case(conn: psycopg.Connection, cin: str, viewer: dict) -> dict:
    """Full case details with its hearings. Judges and lawyers may open only
    closed cases; the registrar may open any case, to record hearing outcomes.
    A lawyer's view is charged in the same transaction. Judges and the
    registrar are never charged."""
    with conn.transaction():
        case = get_case(conn, cin)
        if viewer["role"] != "REGISTRAR" and case["status"] != "CLOSED":
            raise Forbidden(f"Case {cin} is still pending; only closed cases can be viewed")
        hearings = get_hearings(conn, cin)
        fee_charged = balance_due = None
        if viewer["role"] == "LAWYER":
            fee_charged, balance_due = billing.charge_view(conn, viewer["user_id"], cin)
    return {"case": case, "hearings": hearings,
            "fee_charged": fee_charged, "balance_due": balance_due}
