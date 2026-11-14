# Team Task Plan

Deadline: **20 November** (presentation + viva afterwards). Everyone works on their own `feature/*` branch **in the main repo** and opens a pull request into `develop`. Tasks are GitHub issues (labels `tharindu`, `duvindu`, `amaya`).

## Current system (14 Nov): 6 Django microservices
api-gateway (8000, web UI) | user (8001) | room (8002) | message (8003) | activity (8004) | notification (8005) + Redis for shared sessions. Run with `docker compose up --build`, test with `python scripts/smoke_test.py` (26 checks) and `python manage.py test` inside each service.

| Member | GitHub | Role |
|---|---|---|
| Tharindu Kalhara | tharinduk001 | Team lead: integration, gateway, notification-service, tests, release |
| Duvindu Embuldeniya | duvindu-embuldeniya | Backend features, CI, Kubernetes |
| Amaya Jayasekara | selya1722 | Diagram, Postman, UI styling, activity filter, report and slides |

## Tharindu (lead)
- [x] Docker verification (#16), room edit/delete UI (#18), stats panel (#20)
- [x] #1 Unit tests (user, room, notification, gateway)
- [x] #4 Notification-service built (read-all, unread count) and #12 gateway with rate limiting built
- [x] Restored web UI and `scripts/smoke_test.py` for the Django structure
- [ ] #2 Review PRs, keep `develop` green, release `main` + tag `v1.0` (18-19 Nov)
- [ ] #11 Demo and viva (architecture, gateway, sessions via Redis)

## Duvindu
- [ ] #3 Message-service: edit message, pagination, internal room cleanup (`feature/message-service`) - **due 16 Nov**
- [ ] Unit tests for message-service and activity-service (`feature/tests-message-activity`) - 17 Nov
- [ ] #13 CI: GitHub Actions running `docker compose up` + `scripts/smoke_test.py` (`feature/ci`) - 17 Nov
- [ ] #5 Kubernetes manifests, stretch (`feature/kubernetes`) - 18 Nov
- [ ] #11 Demo and viva (message flow, resilience demo, CI, Kubernetes)

## Amaya
- [ ] #7 Postman collection (through the gateway, `http://localhost:8000/api/...`) (`feature/postman`) - 15 Nov
- [ ] #9 Activity feed filter by type (`feature/activity-filter`) - 16 Nov
- [ ] #8 Polish the web UI CSS (`feature/frontend-polish`) - 16 Nov
- [ ] Update the architecture diagram to the 6-service version (`feature/diagram-v2`, see README) - 17 Nov
- [ ] #10 Report and slides - 18 Nov
- [ ] #11 Demo and viva (idea, scenarios, UI walk-through)

## Shared before submission
- [ ] Everyone can run `docker compose up --build` and `python scripts/smoke_test.py` passes
- [ ] Rehearse the demo twice; each person explains what they built
- [ ] Tag the final commit on `main` (`v1.0`)

## Evidence of contribution
GitHub Insights -> Contributors, the PR list, issues per person, `git shortlog -sn`.
