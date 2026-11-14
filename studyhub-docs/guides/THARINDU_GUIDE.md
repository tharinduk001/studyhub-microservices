# Tharindu's Guide - Team Lead

**Your role:** Team lead and integrator. **Deadline:** 20 November. Repo: https://github.com/tharinduk001/studyhub-microservices

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

## 4. Status and your remaining tasks

**Done by you:** architecture and the original FastAPI version (`v0.1` tag), Docker check (#16), unit tests (#17), room edit/delete (#18), stats panel (#20). On `feature/add-notification-gateway`: notification-service (read-all, unread count), gateway with rate limiting, restored web UI, `scripts/smoke_test.py` (26 checks), tests for user, room, notification and gateway (28 tests).
**Merged from Duvindu:** the Django restructure (#19).

### Remaining
- [ ] Merge the `feature/add-notification-gateway` PR; tell the team to `git pull`.
- [ ] #2 Review PRs: base is `develop`, small diff, run `docker compose up --build` + `python scripts/smoke_test.py`, no secrets or databases committed, then merge.
- [ ] Optional extra contribution: request-ID logging in the gateway, or a room member count.
- [ ] **Release (18-19 Nov):** `git checkout main && git pull && git merge --no-ff develop && git tag v1.0 && git push origin main --tags`. Then a fresh-clone check: `docker compose up --build`.
- [ ] #11 Present: architecture, gateway, Redis sessions, sync vs best-effort calls, Docker, tests.

### Viva Q&A to prepare
- Why microservices instead of the monolith? (independent deploy, fault isolation, team ownership)
- What if notification-service is down? (post still succeeds; only room-service is critical)
- How does one login work across services? (user-service writes the session to Redis, the others read it; the gateway forwards the cookie)
- How are internal endpoints protected? (`X-Internal-Key`, blocked at the gateway)
- What would you improve? (message broker, PostgreSQL per service, Kubernetes, a dedicated auth service or JWT)

### Team coordination
- Check Issues/PRs daily; status check with each person on 15 and 17 Nov.
- No restructuring in PRs without agreeing first.
- Evidence for the report: Insights -> Contributors, PR list, `git shortlog -sn --all`.

## 5. Schedule
| Date | Goal |
|---|---|
| 14 Nov | Merge notification-gateway PR, tell the team to pull |
| 15-16 Nov | Review Duvindu's #3 and Amaya's #7, #8, #9 |
| 17 Nov | CI and tests merged, diagram v2 |
| 18 Nov | Release candidate, report draft |
| 19 Nov | Release `v1.0`, full rehearsal |
| 20 Nov | Submission |
