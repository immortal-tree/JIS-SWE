"""Password hashing and login tokens.

Passwords are hashed with scrypt from Python's standard library (a
memory-hard algorithm, like bcrypt/argon2), with a random salt per user.
Plain-text passwords are never stored or logged.
"""

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from .config import settings

_N, _R, _P, _DKLEN = 2**14, 8, 1, 32


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN)
    return "$".join(
        ["scrypt", str(_N), str(_R), str(_P),
         base64.b64encode(salt).decode(), base64.b64encode(dk).decode()]
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt_b64, dk_b64 = stored.split("$")
        if algo != "scrypt":
            return False
        salt, expected = base64.b64decode(salt_b64), base64.b64decode(dk_b64)
        dk = hashlib.scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p),
                            dklen=len(expected))
        return hmac.compare_digest(dk, expected)
    except (ValueError, TypeError):
        return False


# Used to spend the same time on unknown usernames as on wrong passwords,
# so response timing doesn't reveal which usernames exist.
DUMMY_HASH = hash_password("dummy-password-for-timing")


def _secret() -> str:
    if len(settings.jwt_secret) < 32:
        raise RuntimeError(
            "JWT_SECRET is missing or shorter than 32 characters. Set it in your .env file."
        )
    return settings.jwt_secret


def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def decode_access_token(token: str) -> int:
    """Returns the user id. Raises jwt.PyJWTError if invalid or expired."""
    payload = jwt.decode(token, _secret(), algorithms=["HS256"])
    return int(payload["sub"])
