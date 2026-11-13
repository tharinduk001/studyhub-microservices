import os
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "users.db")  # set BEFORE importing app

from fastapi.testclient import TestClient

import app as user_app

client = TestClient(user_app.app)


def register(name="alice", password="secret123"):
    return client.post("/auth/register", json={"username": name, "email": f"{name}@x.com", "password": password})


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_health():
    assert client.get("/health").json()["service"] == "user-service"


def test_register_returns_token_and_user():
    r = register("reg1")
    assert r.status_code == 201
    assert r.json()["user"]["username"] == "reg1"
    assert "password" not in str(r.json()["user"]).lower()
    assert r.json()["token"]


def test_register_duplicate_username_rejected():
    register("dup")
    assert register("dup").status_code == 409
    assert register("DUP").status_code == 409  # usernames are case-insensitive


def test_register_validation():
    assert register("ab").status_code == 422  # username too short
    assert register("shortpw", password="123").status_code == 422


def test_login_ok_and_wrong_password():
    register("bob")
    ok = client.post("/auth/login", json={"username": "bob", "password": "secret123"})
    assert ok.status_code == 200 and ok.json()["token"]
    assert client.post("/auth/login", json={"username": "bob", "password": "wrong"}).status_code == 401
    assert client.post("/auth/login", json={"username": "nobody", "password": "secret123"}).status_code == 401


def test_me_requires_valid_token():
    assert client.get("/users/me").status_code == 401
    assert client.get("/users/me", headers=auth("garbage")).status_code == 401
    token = register("carol").json()["token"]
    assert client.get("/users/me", headers=auth(token)).json()["username"] == "carol"


def test_update_profile():
    token = register("dave").json()["token"]
    r = client.put("/users/me", headers=auth(token), json={"bio": "Hello"})
    assert r.status_code == 200 and r.json()["bio"] == "Hello"


def test_get_user_by_id_and_404():
    uid = register("erin").json()["user"]["id"]
    assert client.get(f"/users/{uid}").json()["username"] == "erin"
    assert client.get("/users/999999").status_code == 404
