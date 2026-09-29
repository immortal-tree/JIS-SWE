# JIS Backend — Judiciary Information System

This is the backend for the JIS, built with Python, FastAPI and PostgreSQL. It implements every feature in the architecture document: accounts and roles, case registration with CINs, hearing scheduling, the three hearing outcomes, registrar queries (a)–(d), keyword search, lawyer billing, and upkeep of the court calendar and viewing fee.

---

## Part 1 — What you need to set up yourself

You need to do these steps once, in this order. Allow about 20 minutes.

### Step 1. Install the software

| Software | Version | Where to get it |
|---|---|---|
| **Python** | 3.11 or newer | https://www.python.org/downloads/ (on Windows, tick **"Add python.exe to PATH"** in the installer) |
| **PostgreSQL** | 14 or newer (16 recommended) | https://www.postgresql.org/download/ |

PostgreSQL install notes:
- **Windows:** use the EDB installer. Remember the password you set for the `postgres` user. Keep port **5432**. You can skip Stack Builder.
- **macOS:** `brew install postgresql@16`, then `brew services start postgresql@16`
- **Ubuntu/Debian:** `sudo apt install postgresql`. The server starts automatically.

To check that both are installed, open a new terminal and run:
```bash
python --version     # use python3 on macOS/Linux if python isn't found
psql --version
```
On Windows, if `psql` isn't found, open **SQL Shell (psql)** from the Start menu instead.

### Step 2. Create the database user and the two databases

Open psql as the admin user:
- **Windows:** open SQL Shell (psql) and press Enter at each prompt. Type your `postgres` password when asked.
- **macOS:** `psql postgres`
- **Linux:** `sudo -u postgres psql`

Then paste these three lines. You can choose a different password; if you do, use it in Step 4.
```sql
CREATE ROLE jis WITH LOGIN PASSWORD 'jis_password';
CREATE DATABASE jis OWNER jis;
CREATE DATABASE jis_test OWNER jis;
```
Type `\q` to exit.

`jis` is the real database. `jis_test` is used only by the automated tests, which **wipe it on every run**, so never put real data in it.

### Step 3. Install the Python packages

Unzip the project, then open a terminal **inside the `jis-backend` folder** and run:

```bash
python -m venv .venv
```
Activate the virtual environment. You need to do this every time you open a new terminal:

| System | Command |
|---|---|
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Windows (cmd) | `.venv\Scripts\activate.bat` |
| macOS / Linux | `source .venv/bin/activate` |

On Windows, if PowerShell says *"running scripts is disabled"*, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.

Then install the packages:
```bash
pip install -r requirements.txt
```

### Step 4. Create your `.env` file

Copy the example file:
```bash
cp .env.example .env        # Windows: copy .env.example .env
```
Open `.env` in any editor and fill in these values:

| Setting | What to put |
|---|---|
| `JWT_SECRET` | A long random string. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"` and paste the output. The app refuses to start without it. |
| `REGISTRAR_PASSWORD` | The password for the first registrar login (8+ characters). |
| `DATABASE_URL`, `TEST_DATABASE_URL` | Change them only if you used a different password, user or port in Step 2. |

### Step 5. Create the tables and the first registrar

```bash
python -m scripts.init_db
```
You should see `Schema is up to date.` and `Registrar account 'registrar' created.` It's safe to run this again later, because it never deletes or overwrites data.

The command also sets these defaults, which the registrar can change later from the API:
- working days Monday to Friday
- daily slots at 10:00, 11:30, 14:00 and 15:30
- a viewing fee of ₹100.00

### Step 6. Start the server

```bash
uvicorn jis.main:app --reload
```
Then open **http://127.0.0.1:8000/docs** in your browser. It shows an interactive page listing every endpoint.

### Step 7. Run the tests (optional, recommended)

```bash
pytest
```
This runs 49 tests covering every scenario (S1–S5), the role checks, and simultaneous bookings and registrations. They should all pass.

---

### Step 8. Open the frontend (optional)

The browser UI lives in `../jis-frontend`. With the server from Step 6 running, open a second terminal:
```bash
cd ../jis-frontend
python -m http.server 5500
```
Then open **http://localhost:5500/** and sign in. `CORS_ORIGINS` in `.env` must include `http://localhost:5500`, as `.env.example` does.

---

## Part 2 — Try it out (a 5-minute demo in the /docs page)

1. **Log in:** open `POST /auth/login` → *Try it out* and send `{"username": "registrar", "password": "<your REGISTRAR_PASSWORD>"}`. Copy the `access_token` from the response.
2. Click **Authorize** (top right), paste the token and click *Authorize*. Your requests now run as the registrar.
3. **Create a judge and a lawyer:** use `POST /users` with `{"role": "LAWYER", "name": "Asha Advocate", "username": "asha", "password": "Password123!"}`, then again with `"role": "JUDGE"`.
4. **Register a case:** use `POST /cases` and fill in every field. The response contains the new CIN, e.g. `2026-000001`.
5. **Find a slot:** use `GET /slots?on=<a future weekday>`.
6. **Book a hearing:** use `POST /cases/{cin}/hearings` with `{"hearing_date": "...", "slot": "10:00"}`.
7. **Record the outcome** on or after the hearing date. Use `POST /hearings/{id}/adjourn`, `/proceedings` or `/judgment`. Judgment closes the case.
8. **Run the reports:** `GET /reports/pending`, `/reports/resolved?from=&to=`, `/reports/hearings?on=` and `/cases/{cin}/status`.
9. **Try the lawyer side:** once a case is closed, log in as `asha`, click *Authorize* again with that token, then use `GET /search?q=robbery` (free) and `GET /cases/{cin}` (charged). Check the balance with `GET /users/me`.

---

## Part 3 — Reference

### Endpoints and who can use them

| Method | Path | Does | Roles |
|---|---|---|---|
| POST | `/auth/login` | Log in, get a token | everyone |
| GET | `/users/me` | Own account (lawyers: balance due) | everyone |
| GET | `/users/me/views` | Own view records and the fee charged for each | Lawyer |
| POST | `/users` | Create account | Registrar |
| GET | `/users` | All accounts with lawyers' balances and view counts | Registrar |
| DELETE | `/users/{id}` | Delete account (login stops, history kept) | Registrar |
| PATCH | `/users/{id}/restore` | Restore a deleted account | Registrar |
| POST | `/cases` | Register case, returns CIN | Registrar |
| GET | `/cases/{cin}` | Full details and hearings. Judges and lawyers: closed cases only (**lawyers charged**) | everyone |
| POST | `/cases/{cin}/hearings` | Book next hearing | Registrar |
| POST | `/hearings/{id}/adjourn` | Outcome: adjourned + reason | Registrar |
| POST | `/hearings/{id}/proceedings` | Outcome: held, no judgment | Registrar |
| POST | `/hearings/{id}/judgment` | Outcome: judgment, closes case | Registrar |
| GET | `/reports/pending` | Query (a) | Registrar |
| GET | `/reports/resolved?from=&to=` | Query (b) | Registrar |
| GET | `/reports/hearings?on=` | Query (c) | Registrar |
| GET | `/cases/{cin}/status` | Query (d) | Registrar |
| GET | `/search?q=` | Keyword search of closed cases (free) | Judge, Lawyer |
| GET | `/slots?on=` | Vacant slots on a date | Registrar |
| GET | `/calendar` | Weekdays, slots, holidays | Registrar |
| PUT | `/calendar/weekdays`, `/calendar/slots` | Change the calendar | Registrar |
| POST / DELETE | `/calendar/holidays` | Add / remove a holiday | Registrar |
| GET / PUT | `/fee` | View / change the per-view fee | all / Registrar |

### How the code maps to the architecture document

```
jis-backend/
├── sql/schema.sql            Data layer: tables and every rule the database enforces
├── scripts/init_db.py        Applies the schema and creates the first registrar
├── jis/
│   ├── main.py               App setup and error handling
│   ├── deps.py               Login check and role checks (Registrar / Judge / Lawyer)
│   ├── security.py           Password hashing (scrypt) and login tokens (JWT)
│   ├── schemas.py            Input validation: incomplete input is rejected, nothing saved
│   ├── clock.py              "Today" (tests replace it to simulate dates)
│   ├── services/             Business logic, one module per service in the diagram
│   │   ├── accounts.py       Account service: login, create / delete accounts (S3)
│   │   ├── cases.py          Case service: register, CIN, adjourn, proceedings, close (S1, S2)
│   │   ├── scheduling.py     Scheduling service: court calendar, vacant slots, book slot (S1, S2, S5)
│   │   ├── queries.py        Query service: queries (a)–(d) (S4)
│   │   ├── search.py         Search service: keyword search, view a case (S3)
│   │   └── billing.py        Billing service: per-view fee, view records, balance (S3, S5)
│   └── routers/              HTTP endpoints; they only check roles and call services
└── tests/                    One test file per sequence diagram, plus concurrency tests
```

### Rules enforced by the database itself

These hold even if there's a bug in the Python code:
- **No double booking.** A unique index allows one SCHEDULED hearing per (date, slot).
- **One upcoming hearing per case at a time.**
- **CINs** match `YYYY-NNNNNN` and are unique. They come from a per-year counter that is locked during registration, so simultaneous registrations never clash and a failed registration doesn't use up a number.
- **A CLOSED case always has its judgment date and summary.**
- **Only lawyers can have a balance due.**
- **Nothing is ever deleted.** A trigger blocks `DELETE` on users, cases, hearings and view records.

### Behaviour worth knowing

- Booking works only for today or later, on working days, in one of the court's slots.
- A hearing's outcome can be recorded **on or after** its date, and only once.
- Declaring a holiday, or removing a weekday or slot, is refused while hearings are booked there. The error lists the hearings to move first.
- Changing the fee affects **future views only**. Each view record keeps the fee it was charged.
- Deleted users are locked out at once, even with a token they already have. Deletion is soft: their history and balance are kept, and the registrar can restore them.
- Search and viewing cover **closed** cases only for judges and lawyers. The registrar can open any case for free, to record hearing outcomes. Search is for judges and lawyers only.
- Lawyers are charged for every case they open, including their own. If own cases should be free, add a check in `jis/services/search.py → view_case` comparing `case["defense_lawyer"]` with the lawyer's name.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `password authentication failed for user "jis"` | The password in `.env` doesn't match Step 2. Fix it in psql with `ALTER ROLE jis PASSWORD 'new';`. |
| `connection refused` / `could not connect to server` | PostgreSQL isn't running. On Windows, start "postgresql-x64-16" in Services. On macOS: `brew services start postgresql@16`. On Linux: `sudo systemctl start postgresql`. |
| `database "jis" does not exist` | Redo Step 2. |
| `permission denied for schema public` | The databases must be created with `OWNER jis`, as in Step 2. |
| `RuntimeError: JWT_SECRET is missing` | Fill in `JWT_SECRET` in `.env` (Step 4). |
| `ModuleNotFoundError: No module named 'fastapi'` | Activate the virtual environment (Step 3) and run `pip install -r requirements.txt`. |
| `No module named 'jis'` or `'scripts'` | Run the commands from inside the `jis-backend` folder. |
| Port 8000 busy | Run `uvicorn jis.main:app --reload --port 8001`. |

## Before any real deployment (not needed for the course)

- Serve it over HTTPS.
- Use a strong database password and `JWT_SECRET`.
- Set up regular `pg_dump` backups.
- Set `CORS_ORIGINS` to the frontend's exact address.
