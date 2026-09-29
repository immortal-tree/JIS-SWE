-- =====================================================================
-- JIS (Judiciary Information System) database schema — PostgreSQL 14+
--
-- Safe to run more than once: every object is created only if missing,
-- and the default calendar / fee rows are inserted only if absent.
--
-- The rules that must never be broken are enforced HERE, not just in
-- the Python code:
--   * one SCHEDULED hearing per (date, slot)       -> no double booking
--   * one SCHEDULED hearing per case at a time
--   * CIN format YYYY-NNNNNN, unique
--   * a CLOSED case always has a judgment date and summary
--   * cases, hearings, users and view records can never be deleted
-- =====================================================================

-- ---------------------------------------------------------------------
-- Users (Registrar / Judge / Lawyer). Accounts are deactivated, never
-- deleted, so a lawyer's view history and balance are always kept.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id        SERIAL PRIMARY KEY,
    name           TEXT        NOT NULL,
    username       TEXT        NOT NULL UNIQUE,
    password_hash  TEXT        NOT NULL,
    role           TEXT        NOT NULL CHECK (role IN ('REGISTRAR', 'JUDGE', 'LAWYER')),
    active         BOOLEAN     NOT NULL DEFAULT TRUE,
    balance_due    NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (balance_due >= 0),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- only lawyers are ever charged
    CONSTRAINT balance_only_for_lawyers CHECK (role = 'LAWYER' OR balance_due = 0)
);

-- ---------------------------------------------------------------------
-- CIN sequence: one row per year. The number restarts at 1 each year.
-- Incremented with an upsert inside the registration transaction, so
-- concurrent registrations can never receive the same CIN.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cin_sequences (
    year         INTEGER PRIMARY KEY CHECK (year BETWEEN 1000 AND 9999),
    last_number  INTEGER NOT NULL CHECK (last_number BETWEEN 1 AND 999999)
);

-- ---------------------------------------------------------------------
-- Cases
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cases (
    cin                       TEXT PRIMARY KEY CHECK (cin ~ '^[0-9]{4}-[0-9]{6}$'),
    defendant_name            TEXT NOT NULL,
    defendant_address         TEXT NOT NULL,
    crime_type                TEXT NOT NULL,
    crime_date                DATE NOT NULL,
    crime_location            TEXT NOT NULL,
    arresting_officer         TEXT NOT NULL,
    arrest_date               DATE NOT NULL,
    presiding_judge           TEXT NOT NULL,
    public_prosecutor         TEXT NOT NULL,
    defense_lawyer            TEXT NOT NULL,
    start_date                DATE NOT NULL,
    expected_completion_date  DATE NOT NULL,
    status                    TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'CLOSED')),
    judgment_date             DATE,
    judgment_summary          TEXT,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- keyword search over every text field of the case
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(crime_type, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(defendant_name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(judgment_summary, '')), 'B') ||
        setweight(to_tsvector('english',
            coalesce(crime_location, '') || ' ' ||
            coalesce(defendant_address, '') || ' ' ||
            coalesce(arresting_officer, '') || ' ' ||
            coalesce(presiding_judge, '') || ' ' ||
            coalesce(public_prosecutor, '') || ' ' ||
            coalesce(defense_lawyer, '')), 'C')
    ) STORED,

    CONSTRAINT arrest_after_crime        CHECK (arrest_date >= crime_date),
    CONSTRAINT completion_after_start    CHECK (expected_completion_date >= start_date),
    -- CLOSED  <=>  judgment recorded
    CONSTRAINT closed_has_judgment CHECK (
        (status = 'CLOSED')  = (judgment_date IS NOT NULL AND judgment_summary IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS cases_status_idx        ON cases (status, cin);
CREATE INDEX IF NOT EXISTS cases_judgment_date_idx ON cases (judgment_date) WHERE status = 'CLOSED';
CREATE INDEX IF NOT EXISTS cases_search_idx        ON cases USING GIN (search_vector);

-- ---------------------------------------------------------------------
-- Hearings: every scheduled date of a case and what happened on it.
-- A booked court slot IS a SCHEDULED hearing row.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hearings (
    hearing_id          SERIAL PRIMARY KEY,
    cin                 TEXT NOT NULL REFERENCES cases (cin),
    hearing_date        DATE NOT NULL,
    slot                TIME NOT NULL,
    status              TEXT NOT NULL DEFAULT 'SCHEDULED'
                        CHECK (status IN ('SCHEDULED', 'ADJOURNED', 'HELD')),
    adjournment_reason  TEXT,
    proceeding_summary  TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english',
            coalesce(proceeding_summary, '') || ' ' || coalesce(adjournment_reason, ''))
    ) STORED,

    CONSTRAINT adjourned_has_reason CHECK (status <> 'ADJOURNED' OR adjournment_reason IS NOT NULL),
    CONSTRAINT held_has_summary     CHECK (status <> 'HELD'      OR proceeding_summary IS NOT NULL)
);

-- No double booking: at most one SCHEDULED hearing in a (date, slot).
CREATE UNIQUE INDEX IF NOT EXISTS one_booking_per_slot
    ON hearings (hearing_date, slot) WHERE status = 'SCHEDULED';

-- A case waits for one hearing at a time.
CREATE UNIQUE INDEX IF NOT EXISTS one_scheduled_hearing_per_case
    ON hearings (cin) WHERE status = 'SCHEDULED';

CREATE INDEX IF NOT EXISTS hearings_case_idx   ON hearings (cin, hearing_date);
CREATE INDEX IF NOT EXISTS hearings_date_idx   ON hearings (hearing_date, status);
CREATE INDEX IF NOT EXISTS hearings_search_idx ON hearings USING GIN (search_vector);

-- ---------------------------------------------------------------------
-- View records: one row each time a lawyer opens a case.
-- The fee is copied at view time, so later fee changes never alter it.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS view_records (
    record_id  SERIAL PRIMARY KEY,
    lawyer_id  INTEGER NOT NULL REFERENCES users (user_id),
    cin        TEXT    NOT NULL REFERENCES cases (cin),
    viewed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    fee        NUMERIC(10, 2) NOT NULL CHECK (fee >= 0)
);

CREATE INDEX IF NOT EXISTS view_records_lawyer_idx ON view_records (lawyer_id, viewed_at);

-- ---------------------------------------------------------------------
-- Fee setting: exactly one row, changed by the registrar.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fee_setting (
    id            BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (id),   -- forces a single row
    fee_per_view  NUMERIC(10, 2) NOT NULL CHECK (fee_per_view >= 0),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Court calendar, maintained by the registrar.
-- A date is a working day if its weekday is listed AND it is not a holiday.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS working_weekdays (
    weekday  SMALLINT PRIMARY KEY CHECK (weekday BETWEEN 1 AND 7)   -- ISO: 1 = Monday, 7 = Sunday
);

CREATE TABLE IF NOT EXISTS holidays (
    holiday_date  DATE PRIMARY KEY,
    description   TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS daily_slots (
    slot  TIME PRIMARY KEY
);

-- ---------------------------------------------------------------------
-- Records are kept forever: block DELETE on the core tables.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION jis_forbid_delete() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Rows in % are never deleted (JIS retention rule)', TG_TABLE_NAME
        USING ERRCODE = 'restrict_violation';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS no_delete_users        ON users;
DROP TRIGGER IF EXISTS no_delete_cases        ON cases;
DROP TRIGGER IF EXISTS no_delete_hearings     ON hearings;
DROP TRIGGER IF EXISTS no_delete_view_records ON view_records;

CREATE TRIGGER no_delete_users        BEFORE DELETE ON users        FOR EACH ROW EXECUTE FUNCTION jis_forbid_delete();
CREATE TRIGGER no_delete_cases        BEFORE DELETE ON cases        FOR EACH ROW EXECUTE FUNCTION jis_forbid_delete();
CREATE TRIGGER no_delete_hearings     BEFORE DELETE ON hearings     FOR EACH ROW EXECUTE FUNCTION jis_forbid_delete();
CREATE TRIGGER no_delete_view_records BEFORE DELETE ON view_records FOR EACH ROW EXECUTE FUNCTION jis_forbid_delete();

-- ---------------------------------------------------------------------
-- Defaults (only inserted if missing). The registrar can change all of
-- these from the API afterwards.
-- ---------------------------------------------------------------------
-- Seeded only when the table is empty, so re-running this file never
-- undoes changes the registrar has made.
INSERT INTO working_weekdays (weekday)
    SELECT d FROM (VALUES (1), (2), (3), (4), (5)) AS v (d)            -- Monday to Friday
    WHERE NOT EXISTS (SELECT 1 FROM working_weekdays);

INSERT INTO daily_slots (slot)
    SELECT s::time FROM (VALUES ('10:00'), ('11:30'), ('14:00'), ('15:30')) AS v (s)
    WHERE NOT EXISTS (SELECT 1 FROM daily_slots);

INSERT INTO fee_setting (id, fee_per_view) VALUES (TRUE, 100.00)
    ON CONFLICT DO NOTHING;
