"""room-service (port 8002) - chat rooms and topics.
Owns its own database: data/rooms.db
Publishes "room_created" events to activity-service.
"""
import os
import sqlite3
import time

import httpx
import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
INTERNAL_KEY = os.getenv("INTERNAL_KEY", "internal-dev-key")
DB_PATH = os.getenv("DB_PATH", "data/rooms.db")
ACTIVITY_URL = os.getenv("ACTIVITY_URL", "http://127.0.0.1:8005")
os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

app = FastAPI(title="Room Service", description="Chat rooms and topics")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


with db() as c:
    c.execute(
        """CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        topic TEXT NOT NULL,
        host_id INTEGER NOT NULL,
        host_name TEXT NOT NULL,
        created REAL NOT NULL)"""
    )


def current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    try:
        return jwt.decode(authorization[7:], SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")


def publish_event(type_: str, user: dict, detail: str):
    """Best-effort: a broken activity-service must never break room-service."""
    try:
        httpx.post(
            f"{ACTIVITY_URL}/events",
            json={"type": type_, "user_id": int(user["sub"]), "username": user["username"], "detail": detail},
            headers={"X-Internal-Key": INTERNAL_KEY},
            timeout=2,
        )
    except httpx.HTTPError:
        pass


class RoomIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    topic: str = Field(min_length=1, max_length=50)
    description: str = ""


def row_to_dict(r) -> dict:
    return dict(r)


@app.get("/health")
def health():
    return {"service": "room-service", "status": "ok"}


@app.get("/rooms")
def list_rooms(q: str = ""):
    with db() as c:
        rows = c.execute(
            "SELECT * FROM rooms WHERE name LIKE ? OR topic LIKE ? ORDER BY id DESC", (f"%{q}%", f"%{q}%")
        ).fetchall()
    return [row_to_dict(r) for r in rows]


@app.get("/topics")
def list_topics():
    with db() as c:
        rows = c.execute("SELECT topic AS name, COUNT(*) AS rooms FROM rooms GROUP BY topic ORDER BY rooms DESC").fetchall()
    return [row_to_dict(r) for r in rows]


@app.post("/rooms", status_code=201)
def create_room(body: RoomIn, user=Depends(current_user)):
    with db() as c:
        cur = c.execute(
            "INSERT INTO rooms (name, description, topic, host_id, host_name, created) VALUES (?,?,?,?,?,?)",
            (body.name, body.description, body.topic, int(user["sub"]), user["username"], time.time()),
        )
        row = c.execute("SELECT * FROM rooms WHERE id=?", (cur.lastrowid,)).fetchone()
    publish_event("room_created", user, f"created room '{body.name}'")
    return row_to_dict(row)


@app.get("/rooms/{room_id}")
def get_room(room_id: int):
    with db() as c:
        row = c.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Room not found")
    return row_to_dict(row)


@app.put("/rooms/{room_id}")
def update_room(room_id: int, body: RoomIn, user=Depends(current_user)):
    room = get_room(room_id)
    if room["host_id"] != int(user["sub"]):
        raise HTTPException(403, "Only the host can edit this room")
    with db() as c:
        c.execute(
            "UPDATE rooms SET name=?, description=?, topic=? WHERE id=?",
            (body.name, body.description, body.topic, room_id),
        )
    return get_room(room_id)


@app.delete("/rooms/{room_id}", status_code=204)
def delete_room(room_id: int, user=Depends(current_user)):
    room = get_room(room_id)
    if room["host_id"] != int(user["sub"]):
        raise HTTPException(403, "Only the host can delete this room")
    with db() as c:
        c.execute("DELETE FROM rooms WHERE id=?", (room_id,))
