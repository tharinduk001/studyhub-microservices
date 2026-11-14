"""End-to-end test through the gateway. Usage: python scripts/smoke_test.py [base_url]
Start the system first (docker compose up --build). Exits non-zero on failure.
Login is a session cookie, so each user gets their own httpx.Client (its own cookie jar)."""
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


anon = httpx.Client(base_url=BASE, timeout=10)
alice_c = httpx.Client(base_url=BASE, timeout=10)
bob_c = httpx.Client(base_url=BASE, timeout=10)

h = anon.get("/health").json()
check("gateway health: all 5 services up", len(h["services"]) == 5 and all(v == "up" for v in h["services"].values()), h)
check("web UI served by gateway", "StudyHub" in anon.get("/").text)

alice, bob = f"alice{suffix}", f"bob{suffix}"
ra = alice_c.post("/api/auth/register", json={"username": alice, "email": "a@x.com", "password": "secret123"})
check("register alice", ra.status_code == 201, ra.text)
check("duplicate username rejected", anon.post("/api/auth/register", json={"username": alice, "email": "a@x.com", "password": "secret123"}).status_code == 409)
check("register bob", bob_c.post("/api/auth/register", json={"username": bob, "email": "b@x.com", "password": "secret123"}).status_code == 201)
check("login wrong password -> 401", anon.post("/api/auth/login", json={"username": alice, "password": "nope"}).status_code == 401)
check("login ok", httpx.Client(base_url=BASE).post("/api/auth/login", json={"username": alice, "password": "secret123"}).status_code == 200)
check("session works across services: /users/me", alice_c.get("/api/users/me").json().get("username") == alice)

check("create room without login -> 401", anon.post("/api/rooms", json={"name": "x", "topic": "t"}).status_code == 401)
room = alice_c.post("/api/rooms", json={"name": "Python Help", "topic": "python", "description": "d"})
check("create room (login shared with room-service)", room.status_code == 201, room.text)
rid = room.json()["id"]
check("search rooms", any(r["id"] == rid for r in anon.get("/api/rooms", params={"q": "Python"}).json()))
check("topics", any(t["name"] == "python" for t in anon.get("/api/topics").json()))

m = bob_c.post("/api/messages", json={"room_id": rid, "body": "hello from bob"})
check("bob posts message (message -> room call)", m.status_code == 201, m.text)
check("message to missing room -> 404", bob_c.post("/api/messages", json={"room_id": 99999, "body": "x"}).status_code == 404)
check("list room messages", len(anon.get("/api/messages", params={"room_id": rid}).json()) == 1)
check("bob cannot delete alice's room", bob_c.delete(f"/api/rooms/{rid}").status_code == 403)

time.sleep(1)
notes = alice_c.get("/api/notifications").json()
check("alice notified (message -> notification call)", any(bob in n["message"] for n in notes), notes)
check("unread count = 1", alice_c.get("/api/notifications/count").json().get("unread") == 1)
check("mark all read", alice_c.post("/api/notifications/read-all").json().get("updated") == 1)
check("unread count = 0", alice_c.get("/api/notifications/count").json().get("unread") == 0)
act = anon.get("/api/activity").json()
check("activity feed: room_created + message_posted", {"room_created", "message_posted"} <= {e["type"] for e in act}, act)
check("activity stats", anon.get("/api/activity/stats").json()["total_events"] >= 2)
check("internal endpoint blocked at gateway", anon.post("/api/activity/events", json={}).status_code == 404)
check("bob can delete own message", bob_c.delete(f"/api/messages/{m.json()['id']}").status_code == 204)
check("host can delete room", alice_c.delete(f"/api/rooms/{rid}").status_code == 204)
check("logout invalidates session", alice_c.post("/api/auth/logout").status_code in (200, 204) and alice_c.get("/api/users/me").status_code == 401)

print(f"\n{'ALL TESTS PASSED' if not fails else str(fails) + ' FAILED'}")
sys.exit(1 if fails else 0)
