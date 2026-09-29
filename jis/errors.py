"""Domain errors raised by the service layer.

Services never import FastAPI; they raise these, and main.py turns them
into HTTP responses. That keeps the business rules testable on their own.
"""

from typing import Any


class JISError(Exception):
    status_code = 400

    def __init__(self, detail: str, data: Any = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.data = data


class BadRequest(JISError):
    status_code = 400


class Unauthorized(JISError):
    status_code = 401


class Forbidden(JISError):
    status_code = 403


class NotFound(JISError):
    status_code = 404


class Conflict(JISError):
    status_code = 409
