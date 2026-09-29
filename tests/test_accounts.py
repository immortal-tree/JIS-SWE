"""Accounts, login and role checks (S3 account management)."""

from conftest import PASSWORD, login


def test_login_and_me(client, lawyer):
    r = client.get("/users/me", headers=lawyer)
    assert r.status_code == 200
    assert r.json()["role"] == "LAWYER"
    assert "password_hash" not in r.json()


def test_wrong_password_and_unknown_user(client):
    assert client.post("/auth/login", json={"username": "judge", "password": "nope-nope"}
                       ).status_code == 401
    assert client.post("/auth/login", json={"username": "ghost", "password": PASSWORD}
                       ).status_code == 401


def test_no_token_or_bad_token(client):
    assert client.get("/users/me").status_code == 401
    assert client.get("/users/me", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_registrar_creates_accounts_and_usernames_are_unique(client, registrar):
    body = {"role": "JUDGE", "name": "Justice Rao", "username": "rao", "password": "Secret123!"}
    r = client.post("/users", json=body, headers=registrar)
    assert r.status_code == 201
    assert r.json()["role"] == "JUDGE"
    assert client.post("/users", json=body, headers=registrar).status_code == 409
    login(client, "rao", "Secret123!")


def test_short_password_rejected(client, registrar):
    r = client.post("/users", json={"role": "LAWYER", "name": "X", "username": "xx1",
                                    "password": "short"}, headers=registrar)
    assert r.status_code == 422


def test_only_registrar_manages_accounts(client, judge, lawyer):
    body = {"role": "LAWYER", "name": "Y", "username": "yy1", "password": "Secret123!"}
    assert client.post("/users", json=body, headers=judge).status_code == 403
    assert client.post("/users", json=body, headers=lawyer).status_code == 403
    assert client.get("/users", headers=lawyer).status_code == 403


def test_deleting_account_blocks_login_and_existing_tokens(client, registrar, lawyer):
    users = {u["username"]: u for u in client.get("/users", headers=registrar).json()}
    lawyer_id = users["lawyer"]["user_id"]

    r = client.delete(f"/users/{lawyer_id}", headers=registrar)
    assert r.status_code == 200 and r.json()["active"] is False

    # the token issued before deletion stops working immediately
    assert client.get("/users/me", headers=lawyer).status_code == 401
    # and they can no longer log in
    r = client.post("/auth/login", json={"username": "lawyer", "password": PASSWORD})
    assert r.status_code == 403

    # soft delete: the account is still listed and can be restored
    assert lawyer_id in [u["user_id"] for u in client.get("/users", headers=registrar).json()]
    assert client.patch(f"/users/{lawyer_id}/restore", headers=registrar).status_code == 200
    login(client, "lawyer")


def test_registrar_cannot_delete_self(client, registrar):
    me = client.get("/users/me", headers=registrar).json()
    assert client.delete(f"/users/{me['user_id']}", headers=registrar).status_code == 400


def test_only_registrar_deletes_accounts(client, registrar, judge):
    users = {u["username"]: u for u in client.get("/users", headers=registrar).json()}
    assert client.delete(f"/users/{users['lawyer']['user_id']}", headers=judge
                         ).status_code == 403


def test_users_can_never_be_deleted_from_the_database():
    import psycopg
    import pytest

    from conftest import TEST_DB
    from jis.db import connect

    with connect(TEST_DB) as conn, pytest.raises(psycopg.errors.RestrictViolation):
        conn.execute("DELETE FROM users WHERE username = 'lawyer'")
