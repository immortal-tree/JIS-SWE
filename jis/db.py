"""Database connections.

Each HTTP request gets its own connection in autocommit mode. Service
functions group their statements with `with conn.transaction():`, which
commits when the block ends and rolls back if anything inside raises —
so multi-step operations (closing a case, charging a lawyer) are atomic.
"""

from collections.abc import Iterator

import psycopg
from psycopg.rows import dict_row

from .config import settings


def connect(url: str | None = None) -> psycopg.Connection:
    return psycopg.connect(url or settings.database_url, row_factory=dict_row, autocommit=True)


def get_db() -> Iterator[psycopg.Connection]:
    """FastAPI dependency: one connection per request, always closed."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
