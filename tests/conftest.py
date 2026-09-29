"""Test setup.

Tests run against a SEPARATE PostgreSQL database (TEST_DATABASE_URL),
which is wiped and rebuilt before every test. Never point it at your
real database.
"""

import os
from datetime import date

import pytest
from dotenv import load_dotenv

load_dotenv()
TEST_DB = os.environ.get("TEST_DATABASE_URL", "")
if not TEST_DB:
    pytest.exit("Set TEST_DATABASE_URL in .env (a separate, empty database).", returncode=2)
if TEST_DB == os.environ.get("DATABASE_URL"):
    pytest.exit("TEST_DATABASE_URL must differ from DATABASE_URL — tests wipe it.", returncode=2)

os.environ["DATABASE_URL"] = TEST_DB  # the app under test talks to the test database
os.environ.setdefault("JWT_SECRET", "test-only-secret-0123456789-abcdefghijklmnop")

from fastapi.testclient import TestClient  # noqa: E402

from jis import clock  # noqa: E402
from jis.config import settings  # noqa: E402
from jis.db import connect  # noqa: E402
from jis.main import app  # noqa: E402
from jis.security import hash_password  # noqa: E402
from scripts.init_db import apply_schema  # noqa: E402

settings.database_url = TEST_DB

# A fixed "today" so tests don't depend on the real date: Monday 5 Oct 2026.
MONDAY = date(2026, 10, 5)
PASSWORD = "Password123!"
USERS = [("REGISTRAR", "registrar", "Ravi Registrar"),
         ("JUDGE", "judge", "Justice Mehra"),
         ("LAWYER", "lawyer", "Asha Advocate"),
         ("LAWYER", "lawyer2", "Vikram Vakil")]
_PASSWORD_HASH = hash_password(PASSWORD)  # hashed once; scrypt is deliberately slow


@pytest.fixture(autouse=True)
def fresh_db():
    with connect(TEST_DB) as conn:
        conn.execute("SET client_min_messages TO warning")
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
        apply_schema(conn)
        for role, username, name in USERS:
            conn.execute("INSERT INTO users (name, username, password_hash, role) "
                         "VALUES (%s, %s, %s, %s)", (name, username, _PASSWORD_HASH, role))
    yield


@pytest.fixture
def today(monkeypatch):
    """today.set(some_date) moves the app's clock. Starts at MONDAY."""
    class _Clock:
        value = MONDAY

        def set(self, d: date) -> None:
            self.value = d

    c = _Clock()
    monkeypatch.setattr(clock, "today", lambda: c.value)
    return c


@pytest.fixture
def client(today):
    with TestClient(app) as c:
        yield c


def login(client: TestClient, username: str, password: str = PASSWORD) -> dict:
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def registrar(client):
    return login(client, "registrar")


@pytest.fixture
def judge(client):
    return login(client, "judge")


@pytest.fixture
def lawyer(client):
    return login(client, "lawyer")


def case_payload(**overrides) -> dict:
    data = {
        "defendant_name": "Ramesh Kumar",
        "defendant_address": "12 MG Road, Bengaluru",
        "crime_type": "Robbery",
        "crime_date": "2026-08-01",
        "crime_location": "Park Street market",
        "arresting_officer": "Inspector Sharma",
        "arrest_date": "2026-08-03",
        "presiding_judge": "Justice Mehra",
        "public_prosecutor": "P. Iyer",
        "defense_lawyer": "Asha Advocate",
        "start_date": "2026-10-05",
        "expected_completion_date": "2027-03-31",
    }
    data.update(overrides)
    return data


def register(client, headers, **overrides) -> str:
    r = client.post("/cases", json=case_payload(**overrides), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["cin"]


def book(client, headers, cin, hearing_date, slot="10:00") -> dict:
    r = client.post(f"/cases/{cin}/hearings",
                    json={"hearing_date": str(hearing_date), "slot": slot}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()
