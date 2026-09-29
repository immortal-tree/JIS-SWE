"""The single source of "today" for the whole app.

Every rule that depends on the date (no booking in the past, no outcome
before the hearing has happened, CIN year) calls clock.today(). Tests
replace this function to simulate time passing.
"""

from datetime import date


def today() -> date:
    return date.today()
