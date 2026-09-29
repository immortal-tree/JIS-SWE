"""Create the JIS tables and the first registrar account.

    python -m scripts.init_db

Safe to run again: existing tables, data and accounts are left untouched.
Reads DATABASE_URL and REGISTRAR_USERNAME / REGISTRAR_PASSWORD /
REGISTRAR_NAME from the environment or .env.
"""

import os
import sys
from pathlib import Path

from jis.db import connect
from jis.security import hash_password

SCHEMA = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"


def apply_schema(conn) -> None:
    conn.execute("SET client_min_messages TO warning")  # hide "already exists" notices
    conn.execute(SCHEMA.read_text(encoding="utf-8"))


def ensure_registrar(conn, username: str, password: str, name: str) -> bool:
    """Returns True if a new account was created."""
    if conn.execute("SELECT 1 FROM users WHERE username = %s", (username,)).fetchone():
        return False
    conn.execute(
        "INSERT INTO users (name, username, password_hash, role) VALUES (%s, %s, %s, 'REGISTRAR')",
        (name, username, hash_password(password)),
    )
    return True


def main() -> int:
    username = os.environ.get("REGISTRAR_USERNAME", "registrar")
    password = os.environ.get("REGISTRAR_PASSWORD", "")
    name = os.environ.get("REGISTRAR_NAME", "Court Registrar")
    if len(password) < 8:
        print("Set REGISTRAR_PASSWORD (8+ characters) in your .env file first.", file=sys.stderr)
        return 1

    with connect() as conn:
        with conn.transaction():
            apply_schema(conn)
            created = ensure_registrar(conn, username, password, name)

    print("Schema is up to date.")
    print(f"Registrar account '{username}' " + ("created." if created else "already exists."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
