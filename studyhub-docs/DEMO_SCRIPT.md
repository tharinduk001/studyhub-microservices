# StudyHub - Demo Script and Viva Prep (10 minutes)

## Before the demo
- `docker compose up --build` (first build ~2 min; do it before the session) and open http://localhost:8000.
- Have two browsers (or one normal + one private window) and `http://localhost:8000/health` in a tab.
- Postman collection: `studyhub-docs/postman_collection.json`.

## Speaking order (who says what)
| Time | Who | Topic |
|---|---|---|
| 0:00 | Amaya | Idea: topic-based study chat, what problem it solves. Show architecture diagram |
| 1:30 | Duvindu | Cloud/deployment: Docker, CI, Kubernetes / cloud branch |
| 3:00 | Tharindu | Live demo (steps below) |
| 8:00 | Tharindu | Design decisions (see Q&A) |
| 9:30 | All | Questions |

## Live demo steps
1. `docker compose ps`: 6 services + Redis, each in its own container.
2. Browser A: register `alice`, create a room "Python Help". Browser B: register `bob`, open the room, post a message.
3. Back in A: alice sees a **notification**; the **activity feed** and **stats** updated.
4. Edit and delete a message (owner only). Try deleting alice's message as bob: refused.
5. **Resilience:** `docker compose stop notification-service`, bob posts again: still works. Show `/health` marks it down. `docker compose start notification-service`.
6. **Critical dependency:** `docker compose stop room-service`, post: returns 503 (message needs room to validate). Start it again.
7. Delete the room: its messages are cleaned up (room -> message internal call).
8. Show `/api/activity/events` is blocked from outside (internal key never forwarded by the gateway).
9. Run `python scripts/smoke_test.py`: 32 end-to-end checks pass. Mention CI runs unit tests + this on every PR.

## Likely viva questions
- **Why microservices here?** Independent deploy/scale/failure per capability; the notification outage demo proves isolation.
- **Database per service?** Yes, 5 separate SQLite DBs; services never read each other's DB, only call APIs.
- **How does login work across services?** user-service writes a Django session into shared Redis; the other services read the same session. Gateway forwards the cookie only.
- **Sync vs async calls?** message->room is synchronous and critical (503 if down). message->notification and ->activity are best-effort (failure is ignored, posting still works).
- **How are internal endpoints protected?** `X-Internal-Key` shared secret; the gateway never forwards it and blocks `/api/activity/events`.
- **What does the gateway do?** Single entry point, routing, per-IP rate limiting, health aggregation, serves the web UI.
- **What is "internal cleanup"?** When a room is deleted, room-service calls message-service `DELETE /messages?room_id=` with the internal key so no orphan messages remain.
- **Limitations / future work?** SQLite -> PostgreSQL, async queue (RabbitMQ/Kafka) for events, JWT/OAuth, in-memory rate limit -> Redis, Kubernetes autoscaling.
- **How did you work as a team?** Branches + PRs + reviews, issues per task, GitHub Actions CI, develop/main release with tag v1.0.

## Fallback if something breaks
Run `docker compose down -v && docker compose up --build`, or show the recorded smoke-test output and Postman collection.
