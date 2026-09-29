"""Request and response shapes. Pydantic rejects incomplete or malformed
input with a 422 response that lists every missing/invalid field — this is
the "highlight missing fields" step of S1; nothing is saved in that case."""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Role = Literal["REGISTRAR", "JUDGE", "LAWYER"]
CaseStatus = Literal["PENDING", "CLOSED"]
HearingStatus = Literal["SCHEDULED", "ADJOURNED", "HELD"]

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]
CIN_PATTERN = r"^[0-9]{4}-[0-9]{6}$"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ----------------------------------------------------------------- auth / users
class LoginIn(Strict):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: Role
    name: str


class UserCreate(Strict):
    role: Role
    name: ShortText
    username: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=3, max_length=50,
                               pattern=r"^[A-Za-z0-9_.-]+$")
    ]
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]


class UserOut(BaseModel):
    user_id: int
    name: str
    username: str
    role: Role
    active: bool
    balance_due: Decimal
    views_count: int | None = None


class ViewRecordOut(BaseModel):
    record_id: int
    cin: str
    viewed_at: datetime
    fee: Decimal


# ----------------------------------------------------------------- calendar / fee
class WeekdaysIn(Strict):
    weekdays: list[Annotated[int, Field(ge=1, le=7)]] = Field(
        min_length=1, description="ISO weekdays: 1 = Monday … 7 = Sunday"
    )


class SlotsIn(Strict):
    slots: list[time] = Field(min_length=1, description="Daily hearing start times, e.g. 10:00")


class HolidayIn(Strict):
    holiday_date: date
    description: str = ""


class FeeIn(Strict):
    fee_per_view: Decimal = Field(ge=0, max_digits=10, decimal_places=2)


class FeeOut(BaseModel):
    fee_per_view: Decimal
    updated_at: datetime


class VacantSlotsOut(BaseModel):
    date: date
    working_day: bool
    vacant_slots: list[time]


# ----------------------------------------------------------------- cases
class CaseCreate(Strict):
    defendant_name: ShortText
    defendant_address: LongText
    crime_type: ShortText
    crime_date: date
    crime_location: LongText
    arresting_officer: ShortText
    arrest_date: date
    presiding_judge: ShortText
    public_prosecutor: ShortText
    defense_lawyer: ShortText
    start_date: date
    expected_completion_date: date

    @model_validator(mode="after")
    def check_dates(self) -> "CaseCreate":
        if self.arrest_date < self.crime_date:
            raise ValueError("arrest_date cannot be before crime_date")
        if self.expected_completion_date < self.start_date:
            raise ValueError("expected_completion_date cannot be before start_date")
        return self


class CaseOut(BaseModel):
    cin: str
    defendant_name: str
    defendant_address: str
    crime_type: str
    crime_date: date
    crime_location: str
    arresting_officer: str
    arrest_date: date
    presiding_judge: str
    public_prosecutor: str
    defense_lawyer: str
    start_date: date
    expected_completion_date: date
    status: CaseStatus
    judgment_date: date | None
    judgment_summary: str | None


class HearingOut(BaseModel):
    hearing_id: int
    cin: str
    hearing_date: date
    slot: time
    status: HearingStatus
    adjournment_reason: str | None
    proceeding_summary: str | None


class CaseDetailOut(BaseModel):
    case: CaseOut
    hearings: list[HearingOut]
    fee_charged: Decimal | None = Field(
        description="Fee added to your balance for this view (lawyers only)")
    balance_due: Decimal | None = Field(description="Your balance after this view (lawyers only)")


# ----------------------------------------------------------------- hearings
class BookHearingIn(Strict):
    hearing_date: date
    slot: time


class AdjournIn(Strict):
    reason: LongText


class ProceedingsIn(Strict):
    summary: LongText


class JudgmentIn(Strict):
    proceedings_summary: LongText
    judgment_summary: LongText
    judgment_date: date | None = Field(
        default=None, description="Defaults to the hearing date")


# ----------------------------------------------------------------- queries / search
class PendingCaseRow(BaseModel):
    cin: str
    start_date: date
    defendant_name: str
    defendant_address: str
    crime_type: str
    crime_date: date
    crime_location: str
    defense_lawyer: str
    public_prosecutor: str
    presiding_judge: str


class ResolvedCaseRow(BaseModel):
    cin: str
    start_date: date
    judgment_date: date
    presiding_judge: str
    judgment_summary: str


class HearingOnDateRow(BaseModel):
    hearing_id: int
    slot: time
    cin: str
    defendant_name: str
    crime_type: str
    presiding_judge: str
    public_prosecutor: str
    defense_lawyer: str


class CaseStatusOut(BaseModel):
    cin: str
    status: CaseStatus
    judgment_date: date | None
    last_hearing: dict | None
    next_hearing: dict | None


class SearchResultRow(BaseModel):
    cin: str
    crime_type: str
    judgment_date: date
