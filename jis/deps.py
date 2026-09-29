"""Authentication and role checks, used as FastAPI dependencies.

Every protected endpoint re-loads the user from the database, so a
deleted account is locked out immediately, not when its token expires.
Roles are checked on the server for every request — hiding buttons in a
frontend is never enough.
"""

import jwt
import psycopg
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .db import get_db
from .errors import Forbidden, Unauthorized
from .security import decode_access_token
from .services import accounts

bearer = HTTPBearer(auto_error=False, description="Paste the access_token from POST /auth/login")


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    conn: psycopg.Connection = Depends(get_db),
) -> dict:
    if creds is None:
        raise Unauthorized("Not logged in")
    try:
        user_id = decode_access_token(creds.credentials)
    except jwt.PyJWTError:
        raise Unauthorized("Invalid or expired token; log in again") from None
    user = accounts.get_user(conn, user_id)
    if user is None or not user["active"]:
        raise Unauthorized("Account has been deleted or no longer exists")
    return user


def require_role(*roles: str):
    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise Forbidden(f"This action is only for: {', '.join(r.title() for r in roles)}")
        return user
    return checker


registrar_only = require_role("REGISTRAR")
judge_or_lawyer = require_role("JUDGE", "LAWYER")
any_user = get_current_user
