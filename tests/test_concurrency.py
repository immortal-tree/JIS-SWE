"""Two registrars acting at the same moment must not break the rules.

These call the services directly from several threads, each with its own
database connection, so the database constraints are what's being tested.
"""

import threading
from datetime import date, time

from conftest import TEST_DB, case_payload
from jis.db import connect
from jis.errors import Conflict
from jis.schemas import CaseCreate
from jis.services import cases, scheduling

TUESDAY = date(2026, 10, 6)


def _run_in_parallel(fn, n):
    barrier = threading.Barrier(n)
    results, lock = [], threading.Lock()

    def worker(i):
        with connect(TEST_DB) as conn:
            barrier.wait()
            try:
                out = fn(conn, i)
            except Exception as e:  # noqa: BLE001 - collected for the assertion
                out = e
        with lock:
            results.append(out)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def test_parallel_registrations_get_unique_cins(today):
    data = CaseCreate(**case_payload())
    results = _run_in_parallel(lambda conn, i: cases.register_case(conn, data)["cin"], 10)
    assert sorted(results) == [f"2026-{n:06d}" for n in range(1, 11)]


def test_parallel_booking_of_one_slot_has_exactly_one_winner(today):
    data = CaseCreate(**case_payload())
    with connect(TEST_DB) as conn:
        cins = [cases.register_case(conn, data)["cin"] for _ in range(6)]

    results = _run_in_parallel(
        lambda conn, i: scheduling.schedule_hearing(conn, cins[i], TUESDAY, time(10, 0)), 6)

    winners = [r for r in results if isinstance(r, dict)]
    losers = [r for r in results if isinstance(r, Conflict)]
    assert len(winners) == 1 and len(losers) == 5, results
