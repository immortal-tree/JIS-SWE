"""S2: record the outcome of a hearing (adjourned / held / judgment)."""

from datetime import date

from conftest import book, register

TUESDAY, WEDNESDAY, THURSDAY = date(2026, 10, 6), date(2026, 10, 7), date(2026, 10, 8)


def test_outcome_cannot_be_recorded_before_the_hearing(client, registrar):
    cin = register(client, registrar)
    h = book(client, registrar, cin, TUESDAY)
    r = client.post(f"/hearings/{h['hearing_id']}/adjourn", json={"reason": "x"},
                    headers=registrar)
    assert r.status_code == 400


def test_adjournment_then_next_hearing(client, registrar, today):
    cin = register(client, registrar)
    h = book(client, registrar, cin, TUESDAY)
    today.set(TUESDAY)
    r = client.post(f"/hearings/{h['hearing_id']}/adjourn",
                    json={"reason": "Defence counsel unwell"}, headers=registrar)
    assert r.status_code == 200
    assert r.json()["status"] == "ADJOURNED"
    assert r.json()["adjournment_reason"] == "Defence counsel unwell"
    # the freed slot can be booked again, and the case needs a new date
    book(client, registrar, cin, WEDNESDAY)


def test_proceedings_without_judgment_then_next_hearing(client, registrar, today):
    cin = register(client, registrar)
    h = book(client, registrar, cin, TUESDAY)
    today.set(TUESDAY)
    r = client.post(f"/hearings/{h['hearing_id']}/proceedings",
                    json={"summary": "Witness examined"}, headers=registrar)
    assert r.json()["status"] == "HELD"
    status = client.get(f"/cases/{cin}/status", headers=registrar).json()
    assert status["status"] == "PENDING"
    assert status["last_hearing"]["status"] == "HELD"
    assert status["next_hearing"] is None
    book(client, registrar, cin, WEDNESDAY)


def test_judgment_closes_case_atomically(client, registrar, today):
    cin = register(client, registrar)
    h = book(client, registrar, cin, TUESDAY)
    today.set(TUESDAY)
    r = client.post(f"/hearings/{h['hearing_id']}/judgment",
                    json={"proceedings_summary": "Final arguments heard",
                          "judgment_summary": "Convicted; 3 years"}, headers=registrar)
    assert r.status_code == 200
    assert r.json()["status"] == "CLOSED"
    assert r.json()["judgment_date"] == str(TUESDAY)

    # closed cases get no more hearings and outcomes can't be recorded twice
    r = client.post(f"/cases/{cin}/hearings",
                    json={"hearing_date": str(THURSDAY), "slot": "10:00"}, headers=registrar)
    assert r.status_code == 409
    r = client.post(f"/hearings/{h['hearing_id']}/proceedings", json={"summary": "again"},
                    headers=registrar)
    assert r.status_code == 409

    # the case is kept, with its full history
    detail = client.get(f"/cases/{cin}", headers=registrar).json()
    assert detail["case"]["judgment_summary"] == "Convicted; 3 years"
    assert detail["hearings"][0]["proceeding_summary"] == "Final arguments heard"


def test_judgment_date_must_be_sensible(client, registrar, today):
    cin = register(client, registrar)
    h = book(client, registrar, cin, TUESDAY)
    today.set(WEDNESDAY)
    r = client.post(f"/hearings/{h['hearing_id']}/judgment",
                    json={"proceedings_summary": "p", "judgment_summary": "j",
                          "judgment_date": str(THURSDAY)}, headers=registrar)
    assert r.status_code == 400
    # nothing changed: the case is still pending
    assert client.get(f"/cases/{cin}/status", headers=registrar).json()["status"] == "PENDING"


def test_missing_reason_rejected(client, registrar, today):
    cin = register(client, registrar)
    h = book(client, registrar, cin, TUESDAY)
    today.set(TUESDAY)
    r = client.post(f"/hearings/{h['hearing_id']}/adjourn", json={"reason": "  "},
                    headers=registrar)
    assert r.status_code == 422
