"""S3: keyword search of past cases (free) and viewing case details
(lawyers charged)."""

from datetime import date

from conftest import book, login, register

TUESDAY = date(2026, 10, 6)


def _closed_case(client, registrar, today, slot="10:00", **fields) -> str:
    cin = register(client, registrar, **fields)
    h = book(client, registrar, cin, TUESDAY, slot)
    today.set(TUESDAY)
    r = client.post(f"/hearings/{h['hearing_id']}/judgment",
                    json={"proceedings_summary": "CCTV footage from the jewellery shop examined",
                          "judgment_summary": "Acquitted for lack of evidence"}, headers=registrar)
    assert r.status_code == 200, r.text
    return cin


def test_search_covers_closed_cases_only(client, registrar, judge, today):
    closed = _closed_case(client, registrar, today, crime_type="Robbery")
    register(client, registrar, crime_type="Armed robbery")                 # still pending
    register(client, registrar, crime_type="Forgery", crime_location="Salt Lake")

    rows = client.get("/search", params={"q": "robbery"}, headers=judge).json()
    assert rows == [{"cin": closed, "crime_type": "Robbery", "judgment_date": str(TUESDAY)}]


def test_search_finds_words_in_proceedings_and_by_cin(client, registrar, lawyer, today):
    cin = _closed_case(client, registrar, today)
    assert [r["cin"] for r in
            client.get("/search", params={"q": "jewellery"}, headers=lawyer).json()] == [cin]
    assert [r["cin"] for r in
            client.get("/search", params={"q": cin}, headers=lawyer).json()] == [cin]


def test_searching_is_free(client, registrar, lawyer, today):
    _closed_case(client, registrar, today)
    assert client.get("/search", params={"q": "robbery"}, headers=lawyer).json()
    assert client.get("/users/me", headers=lawyer).json()["balance_due"] == "0.00"


def test_registrar_does_not_use_search(client, registrar):
    assert client.get("/search", params={"q": "x"}, headers=registrar).status_code == 403


def test_lawyer_is_charged_per_view_judge_is_not(client, registrar, judge, lawyer, today):
    cin = _closed_case(client, registrar, today)

    r = client.get(f"/cases/{cin}", headers=judge)
    assert r.status_code == 200 and r.json()["fee_charged"] is None

    r1 = client.get(f"/cases/{cin}", headers=lawyer).json()
    r2 = client.get(f"/cases/{cin}", headers=lawyer).json()
    assert r1["fee_charged"] == "100.00" and r1["balance_due"] == "100.00"
    assert r2["balance_due"] == "200.00"
    assert r1["case"]["cin"] == cin

    users = {u["username"]: u for u in client.get("/users", headers=registrar).json()}
    assert users["lawyer"]["views_count"] == 2
    assert users["judge"]["views_count"] == 0


def test_pending_case_cannot_be_viewed_by_judge_or_lawyer(client, registrar, judge, lawyer):
    cin = register(client, registrar)
    assert client.get(f"/cases/{cin}", headers=judge).status_code == 403
    assert client.get(f"/cases/{cin}", headers=lawyer).status_code == 403
    assert client.get("/users/me", headers=lawyer).json()["balance_due"] == "0.00"


def test_registrar_views_any_case_free(client, registrar):
    cin = register(client, registrar)
    r = client.get(f"/cases/{cin}", headers=registrar)
    assert r.status_code == 200
    assert r.json()["case"]["status"] == "PENDING" and r.json()["fee_charged"] is None


def test_fee_change_applies_to_future_views_only(client, registrar, lawyer, today):
    cin = _closed_case(client, registrar, today)
    client.get(f"/cases/{cin}", headers=lawyer)                       # charged 100
    assert client.put("/fee", json={"fee_per_view": "250.50"}, headers=registrar
                      ).status_code == 200
    r = client.get(f"/cases/{cin}", headers=lawyer).json()             # charged 250.50
    assert r["fee_charged"] == "250.50"
    assert r["balance_due"] == "350.50"                                # 100 kept, not repriced


def test_unknown_case_is_not_charged(client, lawyer):
    assert client.get("/cases/2026-999999", headers=lawyer).status_code == 404
    assert client.get("/users/me", headers=lawyer).json()["balance_due"] == "0.00"


def test_billing_is_per_lawyer(client, registrar, lawyer, today):
    cin = _closed_case(client, registrar, today)
    other = login(client, "lawyer2")
    client.get(f"/cases/{cin}", headers=lawyer)
    assert client.get("/users/me", headers=other).json()["balance_due"] == "0.00"


def test_lawyer_sees_own_view_history(client, registrar, judge, lawyer, today):
    cin = _closed_case(client, registrar, today)
    client.get(f"/cases/{cin}", headers=lawyer)
    views = client.get("/users/me/views", headers=lawyer).json()
    assert [(v["cin"], v["fee"]) for v in views] == [(cin, "100.00")]
    assert client.get("/users/me/views", headers=login(client, "lawyer2")).json() == []
    assert client.get("/users/me/views", headers=judge).status_code == 403
