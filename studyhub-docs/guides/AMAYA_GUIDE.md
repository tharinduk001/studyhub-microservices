# Amaya's Guide - StudyHub Microservices

**Your role:** Documentation, API testing, the look of the web page, and one small code change.
**Deadline:** 20 November. **Your issues:** #7, #9, #8, #10, #11 + diagram update.
You do **not** need to be an expert. Every task has steps; ask Tharindu whenever you are unsure.

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
2. Install Git, Docker Desktop, Python 3.10+, VS Code and Postman.
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

**In plain words:** people join **rooms** about a **topic**, write **messages** and get **notifications**. Instead of one big program, six small programs ("microservices") each do one job and have their own database. If one breaks (e.g. notifications), the rest keep working.

## 4. Your tasks (in this order)

### Task 1 - Postman collection (issue #7, branch `feature/postman`) - due 15 Nov
The app must be running (`docker compose up --build`). Everything goes through the gateway.
1. In Postman create a **Collection** "StudyHub" and an **Environment** with `baseUrl = http://localhost:8000`.
2. Add one request per row (use `{{baseUrl}}` in the URL). For POST/PUT use *Body -> raw -> JSON*. **Login is a cookie**: Postman stores it automatically after Register/Login, so just run Register (or Login) first.

| Request | Method and URL | Body (example) |
|---|---|---|
| Register | POST `/api/auth/register` | `{"username":"amaya","email":"a@x.com","password":"secret123"}` |
| Login | POST `/api/auth/login` | `{"username":"amaya","password":"secret123"}` |
| My profile | GET `/api/users/me` | - |
| Update profile | PUT `/api/users/me` | `{"bio":"Hello"}` |
| Logout | POST `/api/auth/logout` | - |
| List rooms | GET `/api/rooms` | - |
| Create room | POST `/api/rooms` | `{"name":"Python Help","topic":"python","description":"Ask here"}` |
| Get room | GET `/api/rooms/1` | - |
| Topics | GET `/api/topics` | - |
| Post message | POST `/api/messages` | `{"room_id":1,"body":"Hello!"}` |
| List messages | GET `/api/messages?room_id=1` | - |
| Notifications | GET `/api/notifications` | - |
| Unread count | GET `/api/notifications/count` | - |
| Mark all read | POST `/api/notifications/read-all` | - |
| Activity feed | GET `/api/activity` | - |
| Activity stats | GET `/api/activity/stats` | - |
| Health | GET `/health` | - |

3. To see a notification: register a second user in the browser UI and post in your room, then call Notifications in Postman.
4. Take **screenshots** of a few successful responses (Create room 201, Post message 201, Notifications) for the report.
5. Export the collection (`...` -> Export) and save it as `studyhub-docs/postman_collection.json`, commit, open a pull request.

### Task 2 - Activity feed filter (issue #9, branch `feature/activity-filter`) - due 16 Nov
File: `studyhub-microservices/activity-service/api/views.py`. Find the function `feed`:
```python
@require_http_methods(["GET"])
def feed(request):
    limit = int(request.GET.get("limit", 20))
    events = Event.objects.order_by("-id")[:limit]
    return JsonResponse([e.public() for e in events], safe=False)
```
Replace it with:
```python
@require_http_methods(["GET"])
def feed(request):
    limit = int(request.GET.get("limit", 20))
    events = Event.objects.order_by("-id")
    event_type = request.GET.get("type")
    if event_type:
        events = events.filter(type=event_type)
    return JsonResponse([e.public() for e in events[:limit]], safe=False)
```
Test: run `docker compose up --build`, create a room and post a message in the UI, then open http://localhost:8004/activity?type=message_posted - you should only see message events. Commit, open a pull request. (Ask Tharindu if this feels scary - that is what he is there for.)

### Task 3 - Make the web page look good (issue #8, branch `feature/frontend-polish`) - due 16 Nov
File: `studyhub-microservices/gateway/api/static/index.html`. Everything between `<style>` and `</style>` at the top is the design. **Only change the CSS and visible text** - do not touch the part under `<script>`. Ideas: colours (header is `#3f51b5`), fonts, spacing, button hover, nicer boxes, a logo/heading. After a change run `docker compose up --build` and refresh http://localhost:8000. Take before/after screenshots. Commit, open a pull request.

### Task 4 - Update the architecture diagram (branch `feature/diagram-v2`) - due 17 Nov
The old image `studyhub-docs/architecture.png` shows 4 services. The system now has 6 (gateway, user, room, message, activity, notification) plus Redis for sessions. Use the Mermaid diagram in `README.md` (paste it into https://mermaid.live) or draw it in https://app.diagrams.net. Show: client -> gateway -> 5 services, a database cylinder for each service, Redis shared by the user/room/message/notification services. Export PNG, overwrite `studyhub-docs/architecture.png`, commit, open a pull request.

### Task 5 - Report and slides (issue #10) - finish by 18 Nov
Shared document, suggested sections: 1 Project idea, 2 Business scenarios (table of the 6 services), 3 Architecture (diagram and how services communicate), 4 Technologies (Python/Django, SQLite per service, Redis sessions, Docker), 5 Team contribution (table + GitHub screenshots: Insights -> Contributors, pull requests, issues), 6 Testing (Postman screenshots, smoke test output), 7 Challenges and future work (Kubernetes, message queue, PostgreSQL). Slides (about 10): title, idea, scenarios, architecture, demo, each member's contribution, testing, lessons learned.

### Task 6 - Demo rehearsal (issue #11) - 19 Nov
Practise explaining the idea and clicking through the UI: register, create room, post message, see the notification. Know the job of each of the 6 services.

---

## 5. Suggested schedule
| Date | Goal |
|---|---|
| 14-15 Nov | Setup works, Task 1 (Postman) PR |
| 16 Nov | Tasks 2 and 3 PRs |
| 17 Nov | Task 4 (diagram) PR |
| 18-19 Nov | Report, slides, rehearsal |
| 20 Nov | Submission |

**Stuck?** Copy the error message and send it to Tharindu.
