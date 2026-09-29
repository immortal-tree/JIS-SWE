"""JIS backend entry point.

Run with:   uvicorn jis.main:app --reload
API docs:   http://127.0.0.1:8000/docs
"""

import psycopg
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .errors import JISError
from .routers import accounts, calendar, cases
from .security import _secret

_secret()  # fail at startup, not at first login, if JWT_SECRET is missing

app = FastAPI(
    title="JIS — Judiciary Information System",
    version="1.0.0",
    description=(
        "Backend for the JIS. Log in with **POST /auth/login**, click **Authorize** "
        "and paste the `access_token`. Each endpoint's summary names the roles allowed."
    ),
)

if settings.cors_origins:  # needed only when a browser frontend calls this API
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(JISError)
def handle_jis_error(_: Request, exc: JISError) -> JSONResponse:
    body = {"detail": exc.detail}
    if exc.data is not None:
        body["conflicts"] = jsonable_encoder(exc.data)
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse(status_code=exc.status_code, content=body, headers=headers)


@app.exception_handler(psycopg.errors.CheckViolation)
def handle_check_violation(_: Request, exc: psycopg.errors.CheckViolation) -> JSONResponse:
    # Last line of defence: the database refused data that broke a rule.
    return JSONResponse(status_code=400, content={
        "detail": f"Rejected by database rule '{exc.diag.constraint_name}'"})


app.include_router(accounts.router)
app.include_router(cases.router)
app.include_router(calendar.router)


@app.get("/health", tags=["System"], summary="Is the API up and can it reach the database?")
def health():
    from .db import connect
    with connect() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}
