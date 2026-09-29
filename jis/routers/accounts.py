"""Login and account management (Account service)."""

import psycopg
from fastapi import APIRouter, Depends, status

from ..db import get_db
from ..deps import any_user, require_role, registrar_only
from ..schemas import LoginIn, TokenOut, UserCreate, UserOut, ViewRecordOut
from ..security import create_access_token
from ..services import accounts, billing

router = APIRouter(tags=["Accounts"])


@router.post("/auth/login", response_model=TokenOut, summary="Log in (all users)")
def login(body: LoginIn, conn: psycopg.Connection = Depends(get_db)):
    user = accounts.authenticate(conn, body.username, body.password)
    return {"access_token": create_access_token(user["user_id"], user["role"]),
            "user_id": user["user_id"], "role": user["role"], "name": user["name"]}


@router.get("/users/me", response_model=UserOut,
            summary="My account (lawyers see their balance due here)")
def me(user: dict = Depends(any_user)):
    return user


@router.get("/users/me/views", response_model=list[ViewRecordOut],
            summary="My case views and the fee charged for each, newest first (lawyer)")
def my_views(conn: psycopg.Connection = Depends(get_db),
             user: dict = Depends(require_role("LAWYER"))):
    return billing.get_view_records(conn, user["user_id"])


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             summary="Create an account (registrar)")
def create_account(body: UserCreate, conn: psycopg.Connection = Depends(get_db),
                   _: dict = Depends(registrar_only)):
    return accounts.create_account(conn, body)


@router.get("/users", response_model=list[UserOut],
            summary="List all accounts with lawyers' balances and view counts (registrar)")
def list_users(conn: psycopg.Connection = Depends(get_db), _: dict = Depends(registrar_only)):
    return accounts.list_users(conn)


@router.delete("/users/{user_id}", response_model=UserOut,
               summary="Delete an account; login stops, history is kept (registrar)")
def delete_account(user_id: int, conn: psycopg.Connection = Depends(get_db),
                   me: dict = Depends(registrar_only)):
    return accounts.delete_account(conn, user_id, me["user_id"])


@router.patch("/users/{user_id}/restore", response_model=UserOut,
              summary="Restore a deleted account (registrar)")
def restore_account(user_id: int, conn: psycopg.Connection = Depends(get_db),
                    _: dict = Depends(registrar_only)):
    return accounts.restore_account(conn, user_id)
