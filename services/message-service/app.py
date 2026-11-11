"""message-service (port 8003) - messages posted in rooms.
Owns its own database: data/messages.db
Calls: room-service (validate room), notification-service (alert host), activity-service (event).
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
DB_PATH = os.getenv("DB_PATH", "data/messages.db")
ROOM_URL = os.getenv("ROOM_URL", "http://127.0.0.1:8002")
NOTIFICATION_URL = os.getenv("NOTIFICATION_URL", "http://127.0.0.1:8004")
ACTIVITY_URL = os.getenv("ACTIVITY_URL", "http://127.0.0.1:8005")
os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

app = FastAPI(title="Message Service", description="Messages inside chat rooms")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


with db() as c:
    c.execute(
        """CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        body TEXT NOT NULL,
        created REAL NOT NULL)"""
    )


def current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    try:
        return jwt.decode(authorization[7:], SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")


def fire_and_forget(url: str, payload: dict):
    """Best-effort call to a non-critical service (graceful degradation)."""
    try:
        httpx.post(url, json=payload, headers={"X-Internal-Key": INTERNAL_KEY}, timeout=2)
    except httpx.HTTPError:
        pass


class MessageIn(BaseModel):
    room_id: int
    body: str = Field(min_length=1, max_length=2000)


@app.get("/health")
def health():
    return {"service": "message-service", "status": "ok"}


@app.post("/messages", status_code=201)
def post_message(body: MessageIn, user=Depends(current_user)):
    # 1. Critical dependency: the room must exist (synchronous call to room-service)
    try:
        r = httpx.get(f"{ROOM_URL}/rooms/{body.room_id}", timeout=3)
    except httpx.HTTPError:
        raise HTTPException(503, "room-service unavailable")
    if r.status_code == 404:
        raise HTTPException(404, "Room not found")
    room = r.json()

    with db() as c:
        cur = c.execute(
            "INSERT INTO messages (room_id, user_id, username, body, created) VALUES (?,?,?,?,?)",
            (body.room_id, int(user["sub"]), user["username"], body.body, time.time()),
        )
        row = c.execute("SELECT * FROM messages WHERE id=?", (cur.lastrowid,)).fetchone()

    # 2. Non-critical side effects: notify the host, record activity
    if room["host_id"] != int(user["sub"]):
        fire_and_forget(
            f"{NOTIFICATION_URL}/notifications",
            {"user_id": room["host_id"], "message": f"{user['username']} posted in '{room['name']}'"},
        )
    fire_and_forget(
        f"{ACTIVITY_URL}/events",
        {"type": "message_posted", "user_id": int(user["sub"]), "username": user["username"],
         "detail": f"posted in '{room['name']}'"},
    )
    return dict(row)


@app.get("/messages")
def list_messages(room_id: int | None = None, limit: int = 100):
    query, args = "SELECT * FROM messages", []
    if room_id is not None:
        query += " WHERE room_id=?"
        args.append(room_id)
    query += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with db() as c:
        return [dict(r) for r in c.execute(query, args)]


@app.delete("/messages/{message_id}", status_code=204)
def delete_message(message_id: int, user=Depends(current_user)):
    with db() as c:
        row = c.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Message not found")
        if row["user_id"] != int(user["sub"]):
            raise HTTPException(403, "You can only delete your own messages")
        c.execute("DELETE FROM messages WHERE id=?", (message_id,))
