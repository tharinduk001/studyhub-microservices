"""activity-service (port 8005) - platform-wide activity feed and statistics.
Owns its own database: data/activity.db
POST /events is internal (X-Internal-Key); the feed and stats are public.
"""
import os
import sqlite3
import time

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

INTERNAL_KEY = os.getenv("INTERNAL_KEY", "internal-dev-key")
DB_PATH = os.getenv("DB_PATH", "data/activity.db")
os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

app = FastAPI(title="Activity Service", description="Activity feed and usage statistics")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


with db() as c:
    c.execute(
        """CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        detail TEXT DEFAULT '',
        created REAL NOT NULL)"""
    )


def internal_only(x_internal_key: str = Header(None)):
    if x_internal_key != INTERNAL_KEY:
        raise HTTPException(403, "Internal endpoint")


class EventIn(BaseModel):
    type: str
    user_id: int
    username: str
    detail: str = ""


@app.get("/health")
def health():
    return {"service": "activity-service", "status": "ok"}


@app.post("/events", status_code=201, dependencies=[Depends(internal_only)])
def record_event(body: EventIn):
    with db() as c:
        cur = c.execute(
            "INSERT INTO events (type, user_id, username, detail, created) VALUES (?,?,?,?,?)",
            (body.type, body.user_id, body.username, body.detail, time.time()),
        )
    return {"id": cur.lastrowid}


@app.get("/activity")
def feed(limit: int = 20):
    with db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))]


@app.get("/activity/stats")
def stats():
    with db() as c:
        by_type = {r["type"]: r["n"] for r in c.execute("SELECT type, COUNT(*) AS n FROM events GROUP BY type")}
        top = [dict(r) for r in c.execute(
            "SELECT username, COUNT(*) AS events FROM events GROUP BY username ORDER BY events DESC LIMIT 5")]
    return {"total_events": sum(by_type.values()), "by_type": by_type, "most_active_users": top}
