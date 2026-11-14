# Tharindu's Guide - Team Lead

**Your role:** Team lead and integrator: architecture, repo, reviews, testing, release and presentation.
**Deadline:** 20 November (then presentation + viva). **Your issues:** #1, #2, #11, plus the extra tasks below.
Repo: https://github.com/tharinduk001/studyhub-microservices

---

## 1. Project snapshot

**StudyHub** = topic-based chat platform split into **4 independent Django microservices** (user, room, message, activity), each with its own SQLite database, session-based auth shared via Redis, REST calls between services, Docker Compose to start everything. There is **no gateway** right now - each service is published directly on its own port (8001-8004). Details: `README.md`, `studyhub-docs/architecture.png`.

Already done (on branch `optimize-workload`, not yet merged): all 4 services converted to Django, gateway and notification-service removed, session auth via Redis, `docker-compose.yml` updated, docs updated. Two things planned for later in Kubernetes only (not built yet): a gateway via **APISIX** and notifications via **Novu**.

Not yet done: a real unit test suite (the old pytest-based one was removed during the restructuring and needs to be rewritten for the Django services).

## 2. Team split (who owns what)

| Member | GitHub | Main responsibility |
|---|---|---|
| Tharindu | tharinduk001 | integration, tests for user/room services, reviews, release, architecture presentation |
| Duvindu | duvindu-embuldeniya | message-service features, gateway/notification follow-up (APISIX/Novu, Kubernetes), CI |
| Amaya | selya1722 | diagram, Postman, activity filter, report and slides |

Their detailed guides: `studyhub-docs/guides/DUVINDU_GUIDE.md` and `studyhub-docs/guides/AMAYA_GUIDE.md`.

## 3. Workflow (same for everyone)

```bash
git checkout develop && git pull
git checkout -b feature/<name>
# work, test, commit often
git push -u origin feature/<name>
# open a pull request into develop
```
`main` = stable only. `develop` = integration. One feature branch per task.

---

## 4. Your tasks

### Task 1 - Unit tests for user-service and room-service (issue #1, branch `feature/tests-core`)
There is no test suite right now - write one from scratch. Each service is a Django app (`manage.py`, `api/`), not a single `app.py` module anymore.

1. `pip install pytest django` (each service's own `requirements.txt` already has `django`, `gunicorn`, and `redis`/`requests` where needed).
2. Create `studyhub-microservices/user-service/tests/test_users.py`. Set `DJANGO_SETTINGS_MODULE` and `DB_PATH` **before** calling `django.setup()`:
```python
import os, tempfile
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "users.db")

import django
django.setup()
from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)

from django.test import Client
client = Client()

def register(name="alice"):
    return client.post("/auth/register", data='{"username":"%s","email":"a@x.com","password":"secret123"}' % name,
                        content_type="application/json")

def test_register_and_duplicate():
    assert register("alice").status_code == 201
    assert register("alice").status_code == 409

def test_me_requires_login():
    assert client.get("/users/me").status_code == 401
    register("carol")
    assert client.get("/users/me").json()["username"] == "carol"
```
Note: there's no token to pass around - `register`/`login` set a session cookie on `client`, and the same `client` instance carries it to the next request automatically (just like a browser).
3. Run from the service folder: `cd studyhub-microservices/user-service && python -m pytest tests -v`.
4. Do the same for `studyhub-microservices/room-service/tests/test_rooms.py` (set `DB_PATH` to `rooms.db`). Since room-service doesn't own the login, fake a session directly instead of registering through user-service:
```python
session = client.session
session["user_id"] = 1
session["username"] = "alice"
session.save()
```
Test: create room (201), no session (401), list/search, update/delete by the host (ok) and by another user with a different fake session (403). To avoid the network call to activity-service, monkeypatch `publish_event` in `api.views`.
5. Commit, push, open PR. Optional: Duvindu's CI (#13) can run these too.

### Task 2 - Review and integration (issue #2) - ongoing
For every pull request:
- [ ] Branch targets `develop`, small focused diff, clear title, mentions the issue (`Closes #N`).
- [ ] Pull the branch, run `docker compose up --build`, and manually check `/health` on all 4 ports plus one end-to-end flow (register -> create room -> post message -> activity feed).
- [ ] No secrets, `.env`, `venv/` or `*.db` files committed.
- [ ] Each service still only touches its own database.
- Leave at least one helpful comment, then merge (use "Create a merge commit" to keep history visible).
- Make sure `docker-compose.yml` env vars match any new settings (e.g. a new service needing `ROOM_URL`/`ACTIVITY_URL`/`REDIS_URL`).

### Task 3 - Verify Docker (you, branch `feature/docker-verify`)
1. Start Docker Desktop, run `docker compose up --build` from the repo root.
2. Check `docker compose ps` shows 5 containers (`redis` + the 4 services). Hit `http://localhost:8001/health` ... `:8004/health`.
3. Resilience check: `docker compose stop activity-service`, post a message again via message-service - it should still succeed (activity recording is best-effort), then `docker compose start activity-service`.
4. Fix any problems (likely candidates: ports already in use, env vars, Redis not ready yet). A `.gitattributes` with `* text=auto eol=lf` keeps Dockerfiles on LF line endings on Windows if that comes up again.

### Task 4 - Contribution tasks beyond the lead role
Pick at least two so your Git history shows more than setup:
- **Profile bio editing** - the endpoint already exists (`PUT /users/me` on user-service); build a small script or Postman flow that demonstrates it.
- **Room edit/delete** - already implemented (`PUT`/`DELETE /rooms/<id>` on room-service, host-only). Write a short demo script for it.
- **`/activity/stats` walkthrough** - already implemented on activity-service; show it off in the demo/report.
- **Structured logging**: add a request-ID header and log it consistently across the 4 services (there's no gateway to add it at centrally anymore, so it would need to be per-service middleware).

### Task 5 - Release (end of project)
```bash
git checkout main && git pull
git merge --no-ff develop
git tag v1.0
git push origin main --tags
```
Do this on **18-19 Nov**, after all PRs are merged. Final check: fresh clone -> `docker compose up --build` works, and the cross-service session flow (see README's "Compose run" section) works.

### Task 6 - Presentation and viva (issue #11)
You explain: architecture (database per service, no gateway, session auth shared via Redis, sync vs best-effort calls), the Docker setup and manual testing. Prepare answers to:
- Why microservices instead of the monolith? (independent deploy, fault isolation, team ownership)
- Why Django sessions instead of JWT, and how does that even work without a gateway? (cookies are scoped by host, not port, so the same `sessionid` cookie reaches every service; Redis is the shared store that lets the services, which are separate processes, agree on what a session means)
- What happens if activity-service is down? (room/message creation still succeeds; only the room lookup is critical)
- What would you improve? (APISIX as a real gateway, Novu for notifications - both planned for Kubernetes - message broker, PostgreSQL per service)

### Team coordination
- Assign issues: #3, #12, #13, #5 to Duvindu; #6, #7, #9, #10 to Amaya; add everyone to #11.
- Check the Issues/PR list every day; ask each person for a status on 14 Nov and 17 Nov.
- Make sure each person's commits are under their own GitHub account (needed as contribution evidence).
- Evidence for the report: Insights -> Contributors screenshot, PR list, `git shortlog -sn --all`.

## 5. Schedule

| Date | Goal |
|---|---|
| 11-12 Nov | Teammates accepted and set up; issues assigned; Task 3 (Docker) done |
| 13-15 Nov | Task 1 tests; first PRs from Duvindu and Amaya reviewed |
| 16-17 Nov | All feature PRs merged; Task 4 contributions |
| 18 Nov | Release candidate, report draft ready |
| 19 Nov | Release `v1.0`, full rehearsal (everyone) |
| 20 Nov | Submission |
