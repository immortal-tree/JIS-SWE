"""Court calendar and vacant slots (Scheduling service), and the viewing fee
(Billing service)."""

from datetime import date

import psycopg
from fastapi import APIRouter, Depends, Query, status

from ..db import get_db
from ..deps import any_user, registrar_only
from ..schemas import FeeIn, FeeOut, HolidayIn, SlotsIn, VacantSlotsOut, WeekdaysIn
from ..services import billing, scheduling

router = APIRouter(tags=["Calendar and fee"])


@router.get("/calendar", summary="Working weekdays, daily slots and holidays (registrar)")
def get_calendar(conn: psycopg.Connection = Depends(get_db), _: dict = Depends(registrar_only)):
    return scheduling.get_calendar(conn)


@router.put("/calendar/weekdays", summary="Set working weekdays, 1 = Mon … 7 = Sun (registrar)")
def set_weekdays(body: WeekdaysIn, conn: psycopg.Connection = Depends(get_db),
                 _: dict = Depends(registrar_only)):
    return scheduling.set_working_weekdays(conn, body.weekdays)


@router.put("/calendar/slots", summary="Set the daily hearing slots (registrar)")
def set_slots(body: SlotsIn, conn: psycopg.Connection = Depends(get_db),
              _: dict = Depends(registrar_only)):
    return scheduling.set_daily_slots(conn, body.slots)


@router.post("/calendar/holidays", status_code=status.HTTP_201_CREATED,
             summary="Declare a holiday; refused if hearings are booked that day (registrar)")
def add_holiday(body: HolidayIn, conn: psycopg.Connection = Depends(get_db),
                _: dict = Depends(registrar_only)):
    return scheduling.add_holiday(conn, body.holiday_date, body.description)


@router.delete("/calendar/holidays/{holiday_date}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Remove a holiday (registrar)")
def remove_holiday(holiday_date: date, conn: psycopg.Connection = Depends(get_db),
                   _: dict = Depends(registrar_only)):
    scheduling.remove_holiday(conn, holiday_date)


@router.get("/slots", response_model=VacantSlotsOut,
            summary="Vacant hearing slots on a date (registrar)")
def vacant_slots(on: date = Query(description="Date to check, YYYY-MM-DD"),
                 conn: psycopg.Connection = Depends(get_db), _: dict = Depends(registrar_only)):
    return scheduling.get_vacant_slots(conn, on)


@router.get("/fee", response_model=FeeOut, summary="Current per-view fee (all users)")
def get_fee(conn: psycopg.Connection = Depends(get_db), _: dict = Depends(any_user)):
    return billing.get_fee(conn)


@router.put("/fee", response_model=FeeOut,
            summary="Change the per-view fee; applies to future views only (registrar)")
def set_fee(body: FeeIn, conn: psycopg.Connection = Depends(get_db),
            _: dict = Depends(registrar_only)):
    return billing.set_fee(conn, body.fee_per_view)
