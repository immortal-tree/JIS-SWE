"""S4: registrar queries (a)–(d)."""

from datetime import date

from conftest import book, register

TUESDAY, WEDNESDAY = date(2026, 10, 6), date(2026, 10, 7)


def _close(client, registrar, today, cin, on, summary):
    h = book(client, registrar, cin, on)
    today.set(on)
    r = client.post(f"/hearings/{h['hearing_id']}/judgment",
                    json={"proceedings_summary": "Heard", "judgment_summary": summary},
                    headers=registrar)
    assert r.status_code == 200, r.text


def test_a_pending_cases_sorted_by_cin(client, registrar, today):
    c1 = register(client, registrar, defendant_name="A")
    c2 = register(client, registrar, defendant_name="B")
    c3 = register(client, registrar, defendant_name="C")
    _close(client, registrar, today, c2, TUESDAY, "done")

    rows = client.get("/reports/pending", headers=registrar).json()
    assert [r["cin"] for r in rows] == [c1, c3]
    assert set(rows[0]) == {"cin", "start_date", "defendant_name", "defendant_address",
                            "crime_type", "crime_date", "crime_location", "defense_lawyer", "public_prosecutor",
                            "presiding_judge"}


def test_b_resolved_in_period_chronological(client, registrar, today):
    late = register(client, registrar, start_date="2026-10-01")
    early = register(client, registrar, start_date="2026-09-01")
    outside = register(client, registrar)
    _close(client, registrar, today, late, TUESDAY, "Guilty")
    _close(client, registrar, today, early, WEDNESDAY, "Not guilty")
    today.set(date(2026, 10, 12))
    _close(client, registrar, today, outside, date(2026, 10, 12), "Later")

    rows = client.get("/reports/resolved", params={"from": "2026-10-06", "to": "2026-10-07"},
                      headers=registrar).json()
    assert [r["cin"] for r in rows] == [early, late]     # ordered by start date
    assert rows[0]["judgment_summary"] == "Not guilty"
    assert set(rows[0]) == {"cin", "start_date", "judgment_date", "presiding_judge",
                            "judgment_summary"}

    assert client.get("/reports/resolved", params={"from": "2026-10-07", "to": "2026-10-06"},
                      headers=registrar).status_code == 400


def test_c_hearings_on_a_date(client, registrar):
    c1, c2, c3 = (register(client, registrar) for _ in range(3))
    book(client, registrar, c1, TUESDAY, "14:00")
    book(client, registrar, c2, TUESDAY, "10:00")
    book(client, registrar, c3, WEDNESDAY, "10:00")
    rows = client.get("/reports/hearings", params={"on": str(TUESDAY)},
                      headers=registrar).json()
    assert [(r["cin"], r["slot"]) for r in rows] == [(c2, "10:00:00"), (c1, "14:00:00")]


def test_d_case_status(client, registrar, today):
    cin = register(client, registrar)
    s = client.get(f"/cases/{cin}/status", headers=registrar).json()
    assert s["status"] == "PENDING" and s["last_hearing"] is None and s["next_hearing"] is None

    h = book(client, registrar, cin, TUESDAY)
    today.set(TUESDAY)
    client.post(f"/hearings/{h['hearing_id']}/adjourn", json={"reason": "Judge on leave"},
                headers=registrar)
    book(client, registrar, cin, WEDNESDAY, "11:30")

    s = client.get(f"/cases/{cin}/status", headers=registrar).json()
    assert s["last_hearing"]["status"] == "ADJOURNED"
    assert s["last_hearing"]["adjournment_reason"] == "Judge on leave"
    assert s["next_hearing"]["hearing_date"] == str(WEDNESDAY)


def test_reports_are_registrar_only(client, judge, lawyer):
    for headers in (judge, lawyer):
        assert client.get("/reports/pending", headers=headers).status_code == 403
        assert client.get("/cases/2026-000001/status", headers=headers).status_code == 403
