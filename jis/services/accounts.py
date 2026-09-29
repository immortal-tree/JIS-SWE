"""Account service: login, create and delete accounts (S3).

Deleting an account is a soft delete: the user can no longer log in, but
the row stays, so a lawyer's view records and balance due are kept. The
registrar can restore a deleted account."""

import psycopg

from ..errors import BadRequest, Conflict, Forbidden, NotFound, Unauthorized
from ..schemas import UserCreate
from ..security import DUMMY_HASH, hash_password, verify_password

USER_COLUMNS = "user_id, name, username, role, active, balance_due"


def authenticate(conn: psycopg.Connection, username: str, password: str) -> dict:
    user = conn.execute(
        f"SELECT {USER_COLUMNS}, password_hash FROM users WHERE username = %s",
        (username.strip(),),
    ).fetchone()
    if user is None:
        verify_password(password, DUMMY_HASH)  # same timing as a wrong password
        raise Unauthorized("Invalid username or password")
    if not verify_password(password, user["password_hash"]):
        raise Unauthorized("Invalid username or password")
    if not user["active"]:
        raise Forbidden("This account has been deleted")
    user.pop("password_hash")
    return user


def get_user(conn: psycopg.Connection, user_id: int) -> dict | None:
    return conn.execute(
        f"SELECT {USER_COLUMNS} FROM users WHERE user_id = %s", (user_id,)
    ).fetchone()


def create_account(conn: psycopg.Connection, data: UserCreate) -> dict:
    try:
        with conn.transaction():
            return conn.execute(
                f"""INSERT INTO users (name, username, password_hash, role)
                    VALUES (%s, %s, %s, %s)
                    RETURNING {USER_COLUMNS}""",
                (data.name, data.username, hash_password(data.password), data.role),
            ).fetchone()
    except psycopg.errors.UniqueViolation:
        raise Conflict(f"Username '{data.username}' is already taken") from None


def list_users(conn: psycopg.Connection) -> list[dict]:
    return conn.execute(
        f"""SELECT {USER_COLUMNS},
                   (SELECT count(*) FROM view_records v WHERE v.lawyer_id = u.user_id)
                       AS views_count
            FROM users u
            ORDER BY role, name"""
    ).fetchall()


def _set_active(conn: psycopg.Connection, user_id: int, active: bool) -> dict:
    with conn.transaction():
        user = conn.execute(
            f"UPDATE users SET active = %s WHERE user_id = %s RETURNING {USER_COLUMNS}",
            (active, user_id),
        ).fetchone()
    if user is None:
        raise NotFound(f"No user with id {user_id}")
    return user


def delete_account(conn: psycopg.Connection, user_id: int, acting_user_id: int) -> dict:
    if user_id == acting_user_id:
        raise BadRequest("You cannot delete your own account")
    return _set_active(conn, user_id, False)


def restore_account(conn: psycopg.Connection, user_id: int) -> dict:
    return _set_active(conn, user_id, True)
