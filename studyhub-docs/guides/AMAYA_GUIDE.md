# Amaya's Guide - StudyHub Microservices

**Your role:** Documentation, API testing, and one small code change.
**Deadline:** 20 November (then presentation + viva). **Your issues:** #6, #7, #9, #10, #11.
You do **not** need to be an expert. Every task below has steps; ask Tharindu whenever you are unsure.

---

## 1. What is the project? (read this first)

**StudyHub** is a chat website where people join **rooms** about a **topic** (for example "python") and write **messages**. There is also an **activity feed** showing what is happening.

The special part: instead of one big program (a "monolith"), the system is split into **small independent programs called microservices**. Each one does one job and has its own database:

| Service | Job | Port |
|---|---|---|
| user-service | sign up, log in/out, profile | 8001 |
| room-service | create and list rooms/topics | 8002 |
| message-service | write and read messages | 8003 |
| activity-service | the activity feed and statistics | 8004 |

There is **no front door/gateway** right now - you talk to each service directly on its own port, with Postman or curl (there's no web page to click through either; it was removed along with the gateway).

Example: when Bob writes a message, message-service asks room-service "does this room exist?", saves the message, then tells activity-service to record it. Logging in happens once, on user-service - after that, every service recognizes the same login automatically because they all share one login-session store (Redis) behind the scenes. You don't need to understand Redis to use the app; you just need Postman (or a browser) to keep cookies between requests, the same way it normally does.

Why microservices? If one service is broken (e.g. activity-service), the others keep working. The marks are given for the idea **and** for showing this architecture clearly - that is where your tasks help most.

Planned for later (not built yet, only in the diagram): a real gateway called **APISIX** and a notification system called **Novu**, both meant to run in Kubernetes eventually.

---

## 2. One-time setup

1. Accept the GitHub invitation (check your email or https://github.com/tharinduk001/studyhub-microservices/invitations).
2. Install: **Git**, **Docker Desktop**, and **Postman**. (Python isn't needed for your tasks - everything runs in Docker.)
3. Open a terminal and run:
```bash
git clone https://github.com/tharinduk001/studyhub-microservices.git
cd studyhub-microservices
git checkout develop
docker compose up --build
```
4. There's no single web page to open. Instead, check each service is alive: open `http://localhost:8001/health`, `:8002/health`, `:8003/health`, `:8004/health` in your browser - each should show `{"service": "...", "status": "ok"}`.
5. Stop everything with `docker compose down` (or `Ctrl+C` then `docker compose down`).

## 3. How to save your work (do this for each task)

```bash
git checkout develop
git pull
git checkout -b feature/<branch-name-given-in-the-task>
# ... do your work ...
git add .
git commit -m "docs: short description of what you did"
git push -u origin feature/<branch-name-given-in-the-task>
```
Then go to the repository on GitHub, click **Compare & pull request**, make sure the base branch is **`develop`**, and write one or two lines about what you did. Tharindu will review it. This is how your contribution is recorded - please always use your own branch and your own commits.

---

## 4. Your tasks (in this order)

### Task 1 - Architecture diagram (issue #6, branch `feature/diagram`) - easy
This one is mostly already done, but check it and improve it if you can:
1. Open `studyhub-docs/architecture.png` - it already shows the 4 services, their databases, Redis for shared sessions, and a separate dashed "Kubernetes (planned)" box with APISIX and Novu in it.
2. If you want to redraw or improve it: use https://app.diagrams.net (draw.io) or https://mermaid.live. Keep the same idea - solid boxes for what's actually running (the 4 services + Redis), and a clearly separate/dashed area for APISIX + Novu (planned, not built).
3. Export as **PNG** and overwrite `studyhub-docs/architecture.png`. `README.md` already links to it (`![Architecture](studyhub-docs/architecture.png)`) - no README change needed unless you rename the file.
4. Commit and open a pull request.

### Task 2 - Postman collection (issue #7, branch `feature/postman`) - easy/medium
Goal: a file that lets anyone test every endpoint with clicks. The app must be running (`docker compose up --build`).
1. In Postman create a **Collection** "StudyHub" and an **Environment** with one variable per service base URL: `userUrl = http://localhost:8001`, `roomUrl = http://localhost:8002`, `messageUrl = http://localhost:8003`, `activityUrl = http://localhost:8004`.
2. Turn on Postman's cookie jar (it's on by default) - logging in once will carry the session to every request after that, the same way a browser does. There's no token to paste anywhere.
3. Add one request for each row below:

| Request | Method and URL | Body (example) |
|---|---|---|
| Register | POST `{{userUrl}}/auth/register` | `{"username":"amaya","email":"a@x.com","password":"secret123"}` |
| Login | POST `{{userUrl}}/auth/login` | `{"username":"amaya","password":"secret123"}` |
| Logout | POST `{{userUrl}}/auth/logout` | - |
| My profile | GET `{{userUrl}}/users/me` | - |
| Update profile | PUT `{{userUrl}}/users/me` | `{"bio":"Hello"}` |
| List rooms | GET `{{roomUrl}}/rooms` | - |
| Create room | POST `{{roomUrl}}/rooms` | `{"name":"Python Help","topic":"python","description":"Ask here"}` |
| Get room | GET `{{roomUrl}}/rooms/1` | - |
| Topics | GET `{{roomUrl}}/topics` | - |
| Post message | POST `{{messageUrl}}/messages` | `{"room_id":1,"body":"Hello!"}` |
| List messages | GET `{{messageUrl}}/messages?room_id=1` | - |
| Activity feed | GET `{{activityUrl}}/activity` | - |
| Activity stats | GET `{{activityUrl}}/activity/stats` | - |

4. Run Register (or Login) first, then try the other requests in order - you must be logged in before Create room or Post message will work (they return 401 otherwise, which is also worth a screenshot). Take **screenshots** of a few successful responses (e.g. Create room 201, Post message 201) for the report.
5. Export the collection (`...` -> Export) to `studyhub-docs/postman_collection.json`, commit, open a pull request.

### Task 3 - Small code change: filter the activity feed (issue #9, branch `feature/activity-filter`) - guided
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
    event_type = request.GET.get("type")
    events = Event.objects.all()
    if event_type:
        events = events.filter(type=event_type)
    events = events.order_by("-id")[:limit]
    return JsonResponse([e.public() for e in events], safe=False)
```
Test: run `docker compose up --build`, then in Postman/browser open `http://localhost:8004/activity?type=message_posted`. You should only see message events (post a message first via Task 2's requests if the feed is empty). Commit, open a pull request. (Ask Tharindu if the code looks scary - this is exactly what he is there for.)

### Task 4 - Report and slides (issue #10) - important for marks
Write in a shared document (Google Doc / Word). Suggested sections:
1. **Project idea** - what StudyHub is, who uses it, why it is useful.
2. **Business scenarios** - the table of 4 services from section 1 (which capability each service owns).
3. **Architecture** - the diagram from Task 1 and a short explanation of how services communicate (including: no gateway right now, sessions shared via Redis instead of a token).
4. **Technologies** - Python/Django, SQLite (one DB per service), Redis (shared sessions), Docker, GitHub.
5. **Team contribution** - a table: member, services/tasks, what they built. Add GitHub evidence: screenshot of *Insights -> Contributors*, the list of pull requests and issues.
6. **Testing** - your Postman screenshots.
7. **Challenges and future work** - e.g. reintroducing a gateway (APISIX) and notifications (Novu) once there's a Kubernetes environment, message queues, PostgreSQL per service.
Slides (about 10): title, idea, scenarios, architecture diagram, demo, each member's contribution, testing, lessons learned.

### Task 5 - Demo rehearsal (issue #11)
Practise explaining the project idea and clicking through Postman: register, create room, post message, see it in the activity feed. Know the name and job of each of the 4 services, and be ready to explain that there's no web page or gateway yet - everything is demoed through Postman directly against each service's port.

---

## 5. Suggested schedule
| Date | Goal |
|---|---|
| 12 Nov | Accept invite, `docker compose up --build` works, health checks pass |
| 13 Nov | Task 1 (diagram) pull request |
| 14-15 Nov | Task 2 (Postman) pull request |
| 16 Nov | Task 3 pull request |
| 17-19 Nov | Report and slides, rehearsal |
| 20 Nov | Submission |

**Stuck?** Copy the error message and send it to Tharindu - nobody expects you to solve everything alone.
