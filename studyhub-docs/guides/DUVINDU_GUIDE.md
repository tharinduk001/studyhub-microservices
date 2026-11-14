# Duvindu's Guide - StudyHub Microservices

**Your role:** Senior developer: backend features, tests, CI and Kubernetes.
**Deadline:** 20 November. **Your issues:** #3, #13, #5 (stretch), #11 + service tests.
Thanks for the Django restructure: it is merged, and Tharindu has added the gateway and notification-service on top so we have 6 services.

---

## 1. The application in 2 minutes

**StudyHub** is a topic-based chat platform (rooms, messages, notifications, activity feed) split into **6 independent Django microservices**, each with its own database, behind one API gateway. This is what the lecturer wants to see (5-8 services).

| Service | Port | What it does | Code |
|---|---|---|---|
| api-gateway | 8000 | single entry point `/api/...`, rate limiting, health, serves the web UI | `studyhub-microservices/gateway/api/views.py` |
| user-service | 8001 | register, login/logout (session), profiles | `studyhub-microservices/user-service/api/views.py` |
| room-service | 8002 | rooms and topics | `studyhub-microservices/room-service/api/views.py` |
| message-service | 8003 | messages in rooms | `studyhub-microservices/message-service/api/views.py` |
| activity-service | 8004 | activity feed and stats | `studyhub-microservices/activity-service/api/views.py` |
| notification-service | 8005 | tells a room host when someone posts | `studyhub-microservices/notification-service/api/views.py` |

Key ideas (asked in the viva):
- **Database per service** - no shared tables.
- **One login for all services** - user-service stores the session in **Redis**; the other services read it. The gateway just forwards the cookie.
- **Service-to-service calls** - message-service must reach room-service (else 503); notification and activity calls are best-effort (if they are down, posting still works).
- **Internal endpoints** (`POST /notifications`, `POST /events`) need the `X-Internal-Key` header; the gateway blocks `/api/activity/events` from outside.

Diagram: see `README.md` (Mermaid). Task list: `studyhub-docs/TEAM_TASKS.md`.

---

## 2. One-time setup

1. Accept the GitHub invitation (email or https://github.com/tharinduk001/studyhub-microservices/invitations).
2. Install Git, Docker Desktop and Python 3.10+.
3. In a terminal:
```bash
git clone https://github.com/tharinduk001/studyhub-microservices.git
cd studyhub-microservices
git checkout develop
docker compose up --build
```
4. Open http://localhost:8000 (web UI): register, create a room, post a message. Health: http://localhost:8000/health.
5. In a second terminal: `pip install httpx` then `python scripts/smoke_test.py` - it should print `ALL TESTS PASSED`.
6. Stop with `docker compose down`.

## 3. Workflow for every task

```bash
git checkout develop
git pull
git checkout -b feature/<branch-name-from-the-task>
# ... change code, rebuild: docker compose up --build, test ...
git add .
git commit -m "feat: short description"
git push -u origin feature/<branch-name-from-the-task>
```
Then on GitHub click **Compare & pull request**, base branch **`develop`** (not main), 2-3 lines of description, and `Closes #<issue>`. **Push to the main repo, not your fork.** Tharindu reviews and merges.
Rules: one branch per task, small commits, no big restructuring PRs, never push straight to `main` or `develop`. Always `git pull` on `develop` before you start.

---

## 4. Your tasks (in this order)

### Task A - Message-service features (issue #3, branch `feature/message-service`) - due 16 Nov
File: `studyhub-microservices/message-service/api/views.py`. Auth = `current_user(request)` from `api/sessionauth.py` (returns `{"user_id", "username"}` or `None`).
1. **Edit a message**: add a `PUT` branch to `message_detail` (now only `DELETE`). Body `{"body": "new text"}`; 404 if missing, 403 if `message.user_id` is not the caller, else update, `save()` and return `message.public()`.
2. **Pagination**: in `messages_collection` GET add an `offset` query param and slice `[offset:offset+limit]`.
3. **Internal cleanup**: view that deletes all messages of a room (`Message.objects.filter(room_id=...).delete()`), protected with `X-Internal-Key` against `settings.INTERNAL_KEY` (same as activity-service `/events`).
4. **Wire it**: in room-service `room_detail` DELETE, after deleting, call it with `requests.delete(...)` in `try/except requests.RequestException`. Add `MESSAGE_URL` to room-service settings and to `docker-compose.yml`.
5. Add checks to `scripts/smoke_test.py` (edit ok, edit by another user 403, pagination, room delete cleans messages).
Done when: `python scripts/smoke_test.py` passes with your new checks.

### Task B - Tests for message-service and activity-service (branch `feature/tests-message-activity`) - 17 Nov
Copy the style of `studyhub-microservices/room-service/api/tests.py` or `notification-service/api/tests.py` (Django `TestCase`, `Client`, a logged-in client by writing the session). Run with `python manage.py test` inside each service folder. Mock `requests` in message-service tests (room lookup, notification and activity calls).

### Task C - CI pipeline (issue #13, branch `feature/ci`) - 17 Nov
Create `.github/workflows/ci.yml`:
```yaml
name: CI
on: [pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install django==5.1.4 requests redis httpx
      - run: for s in user-service room-service notification-service gateway; do (cd studyhub-microservices/$s && python manage.py test); done
      - run: docker compose up --build -d
      - run: sleep 15 && python scripts/smoke_test.py
      - run: docker compose down
```
Open a PR, check the green tick, add the badge to `README.md`.

### Task D (stretch) - Kubernetes (issue #5, branch `feature/kubernetes`) - 18 Nov
Folder `k8s/`: Deployment + Service per service and for Redis (images from `studyhub-microservices/<name>`), env vars from `docker-compose.yml`, NodePort or Ingress for the gateway. Describe `kubectl apply -f k8s/` in the README. (APISIX/Novu can be mentioned as future work.)

### Task E - Demo (issue #11) - 19 Nov
Be ready to show: `docker compose stop notification-service`, post a message (still works), `/health` shows it down, start it again; and explain the message flow (gateway -> message -> room, notification, activity) and the Redis session.

---

## 5. Suggested schedule
| Date | Goal |
|---|---|
| 15 Nov | Setup works, Task A started (branch pushed) |
| 16 Nov | Task A PR open |
| 17 Nov | Tasks B and C PRs open |
| 18 Nov | Kubernetes (if time), review fixes |
| 19 Nov | Rehearsal |
| 20 Nov | Submission |

**Stuck?** Send Tharindu the error text; don't wait more than an hour.
