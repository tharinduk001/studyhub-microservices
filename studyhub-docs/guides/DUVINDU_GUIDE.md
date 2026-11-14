# Duvindu's Guide - StudyHub Microservices

**Your role:** Senior developer. You own the backend features, security and DevOps tasks.
**Deadline:** 20 November (then presentation + viva). **Your issues:** #3, #4, #12, #13, #5 (stretch), #11.

---

## 1. The application in 2 minutes

**StudyHub** is a topic-based chat platform (rooms, messages, activity feed). You built the original Django version (`studyhub-cloud-version/`); it's now also split into **4 independent Django microservices**, each with its own database. There is **no gateway** - each service is published directly on its own port.

| Service | Port | What it does | File |
|---|---|---|---|
| user-service | 8001 | register, login/logout (session), profiles | `studyhub-microservices/user-service/api/views.py` |
| room-service | 8002 | rooms and topics | `studyhub-microservices/room-service/api/views.py` |
| message-service | 8003 | messages in rooms | `studyhub-microservices/message-service/api/views.py` |
| activity-service | 8004 | activity feed and stats | `studyhub-microservices/activity-service/api/views.py` |

Removed entirely (not just hidden): **api-gateway** and **notification-service**. Both are planned for a future Kubernetes environment instead - gateway via **APISIX**, notifications via **Novu** - but neither exists in this repo yet.

Key ideas (you will be asked about these in the viva):
- **Database per service** - no shared tables.
- **Session auth, not JWT** - user-service is the only service that writes `request.session` (on register/login/logout). room-service and message-service only read it. All 4 services share the same session store via **Redis** (`REDIS_URL`), so a login on user-service is visible everywhere. This works across different ports with zero extra client code, because cookies are scoped by host, not by port.
- **Service-to-service calls** - message-service calls room-service synchronously (must succeed, 503 if room-service is down) and activity-service best-effort (if it's down, posting still works).
- **The internal endpoint** (`POST /events` on activity-service) uses the `X-Internal-Key` header - unrelated to user sessions, it's service-to-service only, and there's no gateway to block it at anymore (activity-service checks it itself).

Diagram: `studyhub-docs/architecture.png`. Overview: `README.md`.

---

## 2. One-time setup

1. Accept the GitHub invitation (email or https://github.com/tharinduk001/studyhub-microservices/invitations).
2. Install Git, Python 3.10+ and Docker Desktop (Docker is the easiest way to run this now - Redis has to be running for sessions to work across services).
3. In a terminal:
```bash
git clone https://github.com/tharinduk001/studyhub-microservices.git
cd studyhub-microservices
git checkout develop
docker compose up --build
```
4. Each service is now reachable directly: `http://localhost:8001` (user) ... `:8004` (activity). No web UI exists - test with curl or Postman, using a cookie jar so the session carries across ports:
```bash
curl -c cookies.txt -b cookies.txt -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" -d '{"username":"duvindu","email":"d@x.com","password":"secret123"}'
curl -c cookies.txt -b cookies.txt -X POST http://localhost:8002/rooms \
  -H "Content-Type: application/json" -d '{"name":"Python Help","topic":"python"}'
```
5. Stop everything with `docker compose down`.

If you want to run a single service without Docker (e.g. to debug), `pip install django redis requests gunicorn` then `cd studyhub-microservices/<service> && python manage.py migrate && python manage.py runserver <port>`. Without a real Redis running and `REDIS_URL` exported in every terminal, sessions won't be shared between services - fine for poking at one service alone, not for a full login-to-post flow.

## 3. Workflow for every task

```bash
git checkout develop
git pull
git checkout -b feature/<branch-name-from-the-task>
# ... make changes, rebuild with docker compose up --build, test ...
git add .
git commit -m "feat: short description"
git push -u origin feature/<branch-name-from-the-task>
```
Then on GitHub click **Compare & pull request**, set the base branch to **`develop`** (not main), write 2-3 lines of description, and mention the issue (`Closes #3`). Tharindu reviews and merges.
Rules: one branch per task, small commits, never push directly to `main` or `develop`.

---

## 4. Your tasks

### Task A - Message-service features (issue #3)
File: `studyhub-microservices/message-service/api/views.py`. Note: auth here means `current_user(request)` from `api/sessionauth.py`, not a JWT payload - it returns `{"user_id": ..., "username": ...}` or `None`.

1. **Edit a message** - add a `PUT` branch to `message_detail` (it currently only handles `DELETE`). Body: `{"body": "new text"}`. Copy the logic of the delete branch: 404 if missing, 403 if `message.user_id` isn't the caller's `user_id`, otherwise update `message.body` and `save()`, return the updated row via `message.public()`.
2. **Pagination** - in `messages_collection`'s `GET` branch, add an `offset` query param and change the queryset slice to `[offset:offset+limit]`.
3. **Internal cleanup** - add a view that deletes all messages for a room (`Message.objects.filter(room_id=...).delete()`), protected the same way activity-service protects `/events` - check `X-Internal-Key` against `settings.INTERNAL_KEY`.
4. **Wire it up** - in room-service's `room_detail` `DELETE` branch, after deleting the room, call this new endpoint with `requests.delete(...)` inside a `try/except requests.RequestException` (same best-effort pattern as `publish_event`). Add a `MESSAGE_URL` setting to room-service and set it in `docker-compose.yml`.
5. Add tests for edit (200, and 403 for another user's fake session) and pagination once Tharindu's test suite (#1) exists.

Done when: deleting a room leaves no messages for it, verified manually via curl/Postman.

### Task B - Notification follow-up (issue #4)
There is no notification-service anymore - it was removed, not featured, during the restructuring. The original plan ("mark all read + unread count") doesn't apply to code that doesn't exist. What's actually planned: **Novu**, run in Kubernetes, as described in issue #5. If you want contribution credit under #4 before Kubernetes happens, options:
1. Write up the Novu integration plan (what triggers a notification, what API Novu expects, where in message-service/room-service the call would go) as a short doc.
2. Or: treat #4 as superseded by #5 and merge the two in the issue tracker.

### Task C - Gateway follow-up (issue #12)
Same situation as #4: the gateway was removed, not hardened. There's no process to rate-limit or validate tokens at anymore - sessions are validated per-service via the shared Redis store, not at a gateway. The original "JWT validation and rate limiting" plan is gone along with JWT. What's left of this idea:
1. If you still want rate limiting somewhere before Kubernetes/APISIX, it would have to go in each service individually (e.g. a small Django middleware checking a per-IP request count) - not a gateway concern anymore.
2. Otherwise, treat this as superseded by #5 (APISIX in Kubernetes does rate limiting out of the box).

### Task D - CI pipeline (issue #13, branch `feature/ci`)
Create `.github/workflows/ci.yml`. There's no `scripts/run_local.py`/`smoke_test.py` anymore, so CI should instead bring up the real stack and curl it:
```yaml
name: CI
on: [pull_request]
jobs:
  smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker compose up --build -d
      - run: sleep 10
      - run: for p in 8001 8002 8003 8004; do curl -f http://localhost:$p/health; done
      - run: docker compose down
```
If Tharindu's pytest suite (#1) exists by the time you do this, add a step per service: `cd studyhub-microservices/user-service && pip install -r requirements.txt pytest && python -m pytest tests -v`.
Push, open a PR, check the green tick. Add the badge to `README.md`.

### Task E (stretch) - Kubernetes: APISIX + Novu (issue #5, branch `feature/kubernetes`)
Folder `k8s/`: one Deployment + Service per Django microservice (image built from `studyhub-microservices/<name>`), a Deployment + Service for Redis, env vars from `docker-compose.yml`. Then:
- **APISIX** as the gateway: routes `/` traffic to the 4 services, replacing the direct-port access we use locally.
- **Novu** for notifications: message-service (and maybe room-service) call it instead of a local notification-service.
Document how to apply (`kubectl apply -f k8s/`) in the README.

### Task F - Demo (issue #11)
Rehearse and be ready to demo: stop one service (`docker compose stop activity-service`), post a message (still works, room-service/message-service don't depend on it), show `/health` on the stopped one returning nothing, then `docker compose start activity-service`. Explain the session-sharing-via-Redis flow since there's no gateway to point at anymore.

---

## 5. Suggested schedule
| Date | Goal |
|---|---|
| 12 Nov | Accept invite, `docker compose up --build` works |
| 14 Nov | PR for Task A open |
| 16 Nov | Task D (CI) merged; Tasks B/C written up or merged into #5 |
| 17-18 Nov | Kubernetes (if time), fix review comments |
| 19 Nov | Rehearsal |
| 20 Nov | Submission |

**Stuck?** Ask Tharindu in the group chat with the error text; don't wait more than an hour.
