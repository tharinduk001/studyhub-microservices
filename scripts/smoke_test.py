"""End-to-end test through the gateway. Usage: python scripts/smoke_test.py [base_url]
Run after the system is up. Exits non-zero on failure."""
import sys
import time

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
suffix = str(int(time.time()))[-6:]
fails = 0


def check(name, cond, extra=""):
    global fails
    print(("PASS " if cond else "FAIL ") + name, extra if not cond else "")
    fails += 0 if cond else 1


c = httpx.Client(base_url=BASE, timeout=10)
h = c.get("/health").json()
check("gateway health, all services up", all(v == "up" for v in h["services"].values()), h)

alice, bob = f"alice{suffix}", f"bob{suffix}"
ra = c.post("/api/auth/register", json={"username": alice, "email": "a@x.com", "password": "secret123"})
check("register alice", ra.status_code == 201, ra.text)
check("duplicate username rejected", c.post("/api/auth/register", json={"username": alice, "email": "a@x.com", "password": "secret123"}).status_code == 409)
rb = c.post("/api/auth/register", json={"username": bob, "email": "b@x.com", "password": "secret123"})
ta, tb = ra.json()["token"], rb.json()["token"]
A, B = {"Authorization": f"Bearer {ta}"}, {"Authorization": f"Bearer {tb}"}
check("login wrong password -> 401", c.post("/api/auth/login", json={"username": alice, "password": "nope"}).status_code == 401)
check("login ok", c.post("/api/auth/login", json={"username": alice, "password": "secret123"}).status_code == 200)
check("profile /users/me", c.get("/api/users/me", headers=A).json()["username"] == alice)
check("update bio", c.put("/api/users/me", headers=A, json={"bio": "hi"}).json()["bio"] == "hi")

check("create room without token -> 401", c.post("/api/rooms", json={"name": "x", "topic": "t"}).status_code == 401)
room = c.post("/api/rooms", headers=A, json={"name": "Python Help", "topic": "python", "description": "d"})
check("create room", room.status_code == 201, room.text)
rid = room.json()["id"]
check("list rooms / search", any(r["id"] == rid for r in c.get("/api/rooms", params={"q": "Python"}).json()))
check("topics", any(t["name"] == "python" for t in c.get("/api/topics").json()))

m = c.post("/api/messages", headers=B, json={"room_id": rid, "body": "hello from bob"})
check("bob posts message (message->room call)", m.status_code == 201, m.text)
check("message to missing room -> 404", c.post("/api/messages", headers=B, json={"room_id": 99999, "body": "x"}).status_code == 404)
check("list room messages", len(c.get("/api/messages", params={"room_id": rid}).json()) == 1)
check("bob cannot delete alice's room", c.delete(f"/api/rooms/{rid}", headers=B).status_code == 403)

time.sleep(1)  # allow async side effects
notes = c.get("/api/notifications", headers=A).json()
check("alice notified (message->notification call)", any(bob in n["message"] for n in notes), notes)
act = c.get("/api/activity").json()
check("activity feed has room_created + message_posted", {"room_created", "message_posted"} <= {e["type"] for e in act}, act)
check("activity stats", c.get("/api/activity/stats").json()["total_events"] >= 2)
check("internal endpoint blocked at gateway", c.post("/api/activity/events", json={}).status_code == 404)
check("bob can delete own message", c.delete(f"/api/messages/{m.json()['id']}", headers=B).status_code == 204)
check("host can delete room", c.delete(f"/api/rooms/{rid}", headers=A).status_code == 204)

print(f"\n{'ALL TESTS PASSED' if not fails else str(fails) + ' FAILED'}")
sys.exit(1 if fails else 0)
