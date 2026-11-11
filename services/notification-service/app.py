"""notification-service (port 8004) - per-user notifications.
Owns its own database: data/notifications.db
POST /notifications is internal (needs X-Internal-Key); reading is per authenticated user.
"""
import os
import sqlite3
import time

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
INTERNAL_KEY = os.getenv("INTERNAL_KEY", "internal-dev-key")
DB_PATH = os.getenv("DB_PATH", "data/notifications.db")
os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

app = FastAPI(title="Notification Service", description="In-app notifications for users")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


with db() as c:
    c.execute(
        """CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created REAL NOT NULL)"""
    )


def current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    try:
        return jwt.decode(authorization[7:], SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")


def internal_only(x_internal_key: str = Header(None)):
    if x_internal_key != INTERNAL_KEY:
        raise HTTPException(403, "Internal endpoint")


class NotificationIn(BaseModel):
    user_id: int
    message: str


@app.get("/health")
def health():
    return {"service": "notification-service", "status": "ok"}


@app.post("/notifications", status_code=201, dependencies=[Depends(internal_only)])
def create_notification(body: NotificationIn):
    with db() as c:
        cur = c.execute(
            "INSERT INTO notifications (user_id, message, created) VALUES (?,?,?)",
            (body.user_id, body.message, time.time()),
        )
    return {"id": cur.lastrowid}


@app.get("/notifications")
def my_notifications(unread_only: bool = False, user=Depends(current_user)):
    query = "SELECT * FROM notifications WHERE user_id=?"
    if unread_only:
        query += " AND is_read=0"
    with db() as c:
        return [dict(r) for r in c.execute(query + " ORDER BY id DESC", (int(user["sub"]),))]


@app.post("/notifications/{notification_id}/read")
def mark_read(notification_id: int, user=Depends(current_user)):
    with db() as c:
        cur = c.execute(
            "UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?", (notification_id, int(user["sub"]))
        )
    if cur.rowcount == 0:
        raise HTTPException(404, "Notification not found")
    return {"id": notification_id, "is_read": 1}
