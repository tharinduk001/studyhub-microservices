import os
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "rooms.db")  # set BEFORE importing app

import jwt
import pytest
from fastapi.testclient import TestClient

import app as room_app

client = TestClient(room_app.app)


@pytest.fixture(autouse=True)
def no_activity_calls(monkeypatch):
    """room-service tells activity-service about new rooms; skip the network in unit tests."""
    monkeypatch.setattr(room_app, "publish_event", lambda *a, **k: None)


def token_for(user_id, username):
    return jwt.encode({"sub": str(user_id), "username": username}, room_app.SECRET, algorithm="HS256")


def auth(user_id=1, username="alice"):
    return {"Authorization": f"Bearer {token_for(user_id, username)}"}


def make_room(name="Python Help", topic="python", **kw):
    return client.post("/rooms", headers=auth(**kw), json={"name": name, "topic": topic, "description": "d"})


def test_health():
    assert client.get("/health").json()["service"] == "room-service"


def test_create_room_requires_token():
    assert client.post("/rooms", json={"name": "x", "topic": "t"}).status_code == 401
    assert client.post("/rooms", headers={"Authorization": "Bearer bad"}, json={"name": "x", "topic": "t"}).status_code == 401


def test_create_and_get_room():
    r = make_room("Create Me")
    assert r.status_code == 201
    room = r.json()
    assert room["host_id"] == 1 and room["host_name"] == "alice"
    assert client.get(f"/rooms/{room['id']}").json()["name"] == "Create Me"


def test_get_missing_room_404():
    assert client.get("/rooms/999999").status_code == 404


def test_create_room_validation():
    assert client.post("/rooms", headers=auth(), json={"name": "", "topic": "t"}).status_code == 422


def test_search_rooms_and_topics():
    make_room("Searchable Algebra", "maths")
    names = [r["name"] for r in client.get("/rooms", params={"q": "Algebra"}).json()]
    assert "Searchable Algebra" in names
    assert any(t["name"] == "maths" for t in client.get("/topics").json())


def test_host_can_update_and_delete():
    rid = make_room("Edit Me").json()["id"]
    upd = client.put(f"/rooms/{rid}", headers=auth(), json={"name": "Edited", "topic": "python"})
    assert upd.status_code == 200 and upd.json()["name"] == "Edited"
    assert client.delete(f"/rooms/{rid}", headers=auth()).status_code == 204
    assert client.get(f"/rooms/{rid}").status_code == 404


def test_non_host_cannot_update_or_delete():
    rid = make_room("Protected").json()["id"]
    other = auth(user_id=2, username="bob")
    assert client.put(f"/rooms/{rid}", headers=other, json={"name": "Hack", "topic": "t"}).status_code == 403
    assert client.delete(f"/rooms/{rid}", headers=other).status_code == 403
    assert client.get(f"/rooms/{rid}").json()["name"] == "Protected"
