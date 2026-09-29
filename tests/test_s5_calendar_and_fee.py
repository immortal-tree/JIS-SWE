"""S5: registrar maintains the court calendar and the viewing fee."""

from datetime import date

from conftest import book, register

TUESDAY, WEDNESDAY, SATURDAY = date(2026, 10, 6), date(2026, 10, 7), date(2026, 10, 10)


def test_holiday_makes_day_non_working(client, registrar):
    r = client.post("/calendar/holidays",
                    json={"holiday_date": str(WEDNESDAY), "description": "Local holiday"},
                    headers=registrar)
    assert r.status_code == 201
    slots = client.get("/slots", params={"on": str(WEDNESDAY)}, headers=registrar).json()
    assert slots["working_day"] is False

    assert client.delete(f"/calendar/holidays/{WEDNESDAY}", headers=registrar
                         ).status_code == 204
    slots = client.get("/slots", params={"on": str(WEDNESDAY)}, headers=registrar).json()
    assert slots["working_day"] is True


def test_holiday_refused_when_hearings_are_booked(client, registrar):
    cin = register(client, registrar)
    book(client, registrar, cin, TUESDAY)
    r = client.post("/calendar/holidays", json={"holiday_date": str(TUESDAY)},
                    headers=registrar)
    assert r.status_code == 409
    assert r.json()["conflicts"][0]["cin"] == cin


def test_change_working_weekdays(client, registrar):
    r = client.put("/calendar/weekdays", json={"weekdays": [1, 2, 3, 4, 5, 6]},
                   headers=registrar)
    assert r.json()["working_weekdays"] == [1, 2, 3, 4, 5, 6]
    assert client.get("/slots", params={"on": str(SATURDAY)}, headers=registrar
                      ).json()["working_day"] is True


def test_cannot_remove_weekday_or_slot_that_has_bookings(client, registrar):
    cin = register(client, registrar)
    book(client, registrar, cin, TUESDAY, "14:00")
    r = client.put("/calendar/weekdays", json={"weekdays": [1, 3, 4, 5]}, headers=registrar)
    assert r.status_code == 409
    r = client.put("/calendar/slots", json={"slots": ["10:00", "11:30"]}, headers=registrar)
    assert r.status_code == 409
    # adding slots is always fine
    r = client.put("/calendar/slots", json={"slots": ["10:00", "12:00", "14:00"]},
                   headers=registrar)
    assert r.json()["daily_slots"] == ["10:00:00", "12:00:00", "14:00:00"]


def test_fee_is_visible_to_all_but_set_by_registrar_only(client, registrar, judge, lawyer):
    assert client.get("/fee", headers=lawyer).json()["fee_per_view"] == "100.00"
    assert client.put("/fee", json={"fee_per_view": "5"}, headers=judge).status_code == 403
    assert client.put("/fee", json={"fee_per_view": "-1"}, headers=registrar).status_code == 422
    assert client.put("/fee", json={"fee_per_view": "75"}, headers=registrar).status_code == 200
    assert client.get("/fee", headers=judge).json()["fee_per_view"] == "75.00"
