"""Cases, hearings, registrar queries, search and viewing a case."""

from datetime import date
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, Path, Query, status

from ..db import get_db
from ..deps import any_user, judge_or_lawyer, registrar_only
from ..schemas import (CIN_PATTERN, AdjournIn, BookHearingIn, CaseCreate, CaseDetailOut,
                       CaseOut, CaseStatusOut, HearingOnDateRow, HearingOut,
                       JudgmentIn, PendingCaseRow, ProceedingsIn, ResolvedCaseRow,
                       SearchResultRow)
from ..services import cases, queries, scheduling, search

router = APIRouter()
CIN = Annotated[str, Path(pattern=CIN_PATTERN, examples=["2026-000001"])]


# ---------------------------------------------------------------- S1: register
@router.post("/cases", response_model=CaseOut, status_code=status.HTTP_201_CREATED,
             tags=["Cases"], summary="Register a case; returns its new CIN (registrar)")
def register_case(body: CaseCreate, conn: psycopg.Connection = Depends(get_db),
                  _: dict = Depends(registrar_only)):
    return cases.register_case(conn, body)


# ---------------------------------------------------------------- S3: view (billing)
@router.get("/cases/{cin}", response_model=CaseDetailOut, tags=["Search"],
            summary="Full case details and hearings. Judges and lawyers: closed cases only; "
                    "lawyers are charged the current fee.")
def view_case(cin: CIN, conn: psycopg.Connection = Depends(get_db),
              user: dict = Depends(any_user)):
    return search.view_case(conn, cin, user)


# ---------------------------------------------------------------- S1/S2: scheduling
@router.post("/cases/{cin}/hearings", response_model=HearingOut,
             status_code=status.HTTP_201_CREATED, tags=["Hearings"],
             summary="Book the next hearing in a vacant slot (registrar)")
def schedule_hearing(cin: CIN, body: BookHearingIn, conn: psycopg.Connection = Depends(get_db),
                     _: dict = Depends(registrar_only)):
    return scheduling.schedule_hearing(conn, cin, body.hearing_date, body.slot)


# ---------------------------------------------------------------- S2: outcomes
@router.post("/hearings/{hearing_id}/adjourn", response_model=HearingOut, tags=["Hearings"],
             summary="Record that the hearing was adjourned, with the reason (registrar)")
def record_adjournment(hearing_id: int, body: AdjournIn,
                       conn: psycopg.Connection = Depends(get_db),
                       _: dict = Depends(registrar_only)):
    return cases.record_adjournment(conn, hearing_id, body.reason)


@router.post("/hearings/{hearing_id}/proceedings", response_model=HearingOut,
             tags=["Hearings"],
             summary="Record that the hearing was held, without judgment (registrar)")
def record_proceedings(hearing_id: int, body: ProceedingsIn,
                       conn: psycopg.Connection = Depends(get_db),
                       _: dict = Depends(registrar_only)):
    return cases.record_proceedings(conn, hearing_id, body.summary)


@router.post("/hearings/{hearing_id}/judgment", tags=["Hearings"],
             summary="Record proceedings and judgment, closing the case (registrar)")
def close_case(hearing_id: int, body: JudgmentIn, conn: psycopg.Connection = Depends(get_db),
               _: dict = Depends(registrar_only)):
    return cases.close_case(conn, hearing_id, body.proceedings_summary,
                            body.judgment_summary, body.judgment_date)


# ---------------------------------------------------------------- S4: queries (a)–(d)
@router.get("/reports/pending", response_model=list[PendingCaseRow], tags=["Reports"],
            summary="(a) Pending cases, sorted by CIN (registrar)")
def report_pending(conn: psycopg.Connection = Depends(get_db), _: dict = Depends(registrar_only)):
    return queries.get_pending_cases(conn)


@router.get("/reports/resolved", response_model=list[ResolvedCaseRow], tags=["Reports"],
            summary="(b) Cases resolved in a period, chronological (registrar)")
def report_resolved(date_from: date = Query(alias="from"), date_to: date = Query(alias="to"),
                    conn: psycopg.Connection = Depends(get_db),
                    _: dict = Depends(registrar_only)):
    return queries.get_resolved_cases(conn, date_from, date_to)


@router.get("/reports/hearings", response_model=list[HearingOnDateRow], tags=["Reports"],
            summary="(c) Cases coming up for hearing on a date (registrar)")
def report_hearings(on: date, conn: psycopg.Connection = Depends(get_db),
                    _: dict = Depends(registrar_only)):
    return queries.get_hearings_on(conn, on)


@router.get("/cases/{cin}/status", response_model=CaseStatusOut, tags=["Reports"],
            summary="(d) Status, last hearing outcome and next hearing of a case (registrar)")
def report_status(cin: CIN, conn: psycopg.Connection = Depends(get_db),
                  _: dict = Depends(registrar_only)):
    return queries.get_case_status(conn, cin)


# ---------------------------------------------------------------- S3: search
@router.get("/search", response_model=list[SearchResultRow], tags=["Search"],
            summary="Keyword search of past (closed) cases; free (judge, lawyer)")
def search_past_cases(q: str = Query(min_length=1, max_length=200,
                                     description='Keywords, e.g. robbery "Park Street" -bail'),
                      limit: int = Query(default=50, ge=1, le=200),
                      conn: psycopg.Connection = Depends(get_db),
                      _: dict = Depends(judge_or_lawyer)):
    return search.search_past_cases(conn, q, limit)
