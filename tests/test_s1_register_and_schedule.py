"""S1: register a case (CIN) and schedule its first hearing."""

from datetime import date

from conftest import book, case_payload, register

TUESDAY, SATURDAY = date(2026, 10, 6), date(2026, 10, 10)


def test_register_generates_sequential_cins(client, registrar):
    r = client.post("/cases", json=case_payload(), headers=registrar)
    assert r.status_code == 201
    assert r.json()["cin"] == "2026-000001"
    assert r.json()["status"] == "PENDING"
    assert register(client, registrar) == "2026-000002"


def test_cin_restarts_each_year(client, registrar, today):
    register(client, registrar)
    today.set(date(2027, 1, 4))
    assert register(client, registrar) == "2027-000001"


def test_incomplete_case_is_rejected_and_nothing_is_saved(client, registrar):
    data = case_payload()
    del data["arresting_officer"]
    data["defendant_name"] = "   "
    r = client.post("/cases", json=data, headers=registrar)
    assert r.status_code == 422
    bad_fields = {e["loc"][-1] for e in r.json()["detail"]}
    assert {"arresting_officer", "defendant_name"} <= bad_fields
    assert client.get("/reports/pending", headers=registrar).json() == []
    # the failed attempt did not use up a CIN
    assert register(client, registrar) == "2026-000001"


def test_inconsistent_dates_rejected(client, registrar):
    r = client.post("/cases", json=case_payload(arrest_date="2026-07-01"), headers=registrar)
    assert r.status_code == 422


def test_only_registrar_registers(client, judge):
    assert client.post("/cases", json=case_payload(), headers=judge).status_code == 403


def test_vacant_slots_and_first_booking(client, registrar):
    cin = register(client, registrar)
    r = client.get("/slots", params={"on": str(TUESDAY)}, headers=registrar)
    assert r.json() == {"date": "2026-10-06", "working_day": True,
                        "vacant_slots": ["10:00:00", "11:30:00", "14:00:00", "15:30:00"]}

    hearing = book(client, registrar, cin, TUESDAY, "11:30")
    assert hearing["status"] == "SCHEDULED"

    r = client.get("/slots", params={"on": str(TUESDAY)}, headers=registrar)
    assert "11:30:00" not in r.json()["vacant_slots"]


def test_weekend_is_not_a_working_day(client, registrar):
    cin = register(client, registrar)
    r = client.get("/slots", params={"on": str(SATURDAY)}, headers=registrar)
    assert r.json()["working_day"] is False and r.json()["vacant_slots"] == []
    r = client.post(f"/cases/{cin}/hearings",
                    json={"hearing_date": str(SATURDAY), "slot": "10:00"}, headers=registrar)
    assert r.status_code == 400


def test_no_double_booking(client, registrar):
    cin1, cin2 = register(client, registrar), register(client, registrar)
    book(client, registrar, cin1, TUESDAY, "10:00")
    r = client.post(f"/cases/{cin2}/hearings",
                    json={"hearing_date": str(TUESDAY), "slot": "10:00"}, headers=registrar)
    assert r.status_code == 409


def test_one_scheduled_hearing_per_case(client, registrar):
    cin = register(client, registrar)
    book(client, registrar, cin, TUESDAY, "10:00")
    r = client.post(f"/cases/{cin}/hearings",
                    json={"hearing_date": "2026-10-07", "slot": "10:00"}, headers=registrar)
    assert r.status_code == 409


def test_cannot_book_past_dates_or_invalid_slots(client, registrar):
    cin = register(client, registrar)
    r = client.post(f"/cases/{cin}/hearings",
                    json={"hearing_date": "2026-10-01", "slot": "10:00"}, headers=registrar)
    assert r.status_code == 400
    r = client.post(f"/cases/{cin}/hearings",
                    json={"hearing_date": str(TUESDAY), "slot": "09:15"}, headers=registrar)
    assert r.status_code == 400
