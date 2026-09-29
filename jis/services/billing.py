"""Billing service: the per-view fee (S5) and charging a lawyer each time
they open a case's details (S3). The only writer of view_records and of
users.balance_due."""

from decimal import Decimal

import psycopg


def get_fee(conn: psycopg.Connection) -> dict:
    return conn.execute("SELECT fee_per_view, updated_at FROM fee_setting").fetchone()


def set_fee(conn: psycopg.Connection, amount: Decimal) -> dict:
    """Applies to future views only: past view records keep the fee they were charged."""
    with conn.transaction():
        return conn.execute(
            """UPDATE fee_setting SET fee_per_view = %s, updated_at = now()
               RETURNING fee_per_view, updated_at""",
            (amount,),
        ).fetchone()


def get_view_records(conn: psycopg.Connection, lawyer_id: int) -> list[dict]:
    """A lawyer's view history, newest first."""
    return conn.execute(
        """SELECT record_id, cin, viewed_at, fee FROM view_records
           WHERE lawyer_id = %s ORDER BY viewed_at DESC, record_id DESC""",
        (lawyer_id,),
    ).fetchall()


def charge_view(conn: psycopg.Connection, lawyer_id: int, cin: str) -> tuple[Decimal, Decimal]:
    """saveViewRecord + addToBalance. Returns (fee charged, new balance due).
    Must be called inside the caller's transaction, so the charge and the
    view succeed or fail together."""
    fee = conn.execute("SELECT fee_per_view FROM fee_setting").fetchone()["fee_per_view"]
    conn.execute("INSERT INTO view_records (lawyer_id, cin, fee) VALUES (%s, %s, %s)",
                 (lawyer_id, cin, fee))
    balance_due = conn.execute(
        """UPDATE users SET balance_due = balance_due + %s WHERE user_id = %s
           RETURNING balance_due""",
        (fee, lawyer_id),
    ).fetchone()["balance_due"]
    return fee, balance_due
