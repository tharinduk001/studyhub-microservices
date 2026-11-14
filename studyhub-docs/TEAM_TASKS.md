# Team Task Plan

Deadline: **20 November** (presentation + viva afterwards). Everyone works on their own `feature/*` branch and opens a pull request into `develop`. Commit often so GitHub shows each person's contribution. Tasks are tracked as GitHub issues (labels: `tharindu`, `duvindu`, `amaya`).

| Member | GitHub | Role |
|---|---|---|
| Tharindu Kalhara | tharinduk001 | Team lead: architecture, repo, integration, review |
| Duvindu Embuldeniya | duvindu-embuldeniya | Senior developer: backend features, security, DevOps |
| Amaya Jayasekara | selya1722 | Documentation, API testing and a small backend change |

## Tharindu (lead)
- [x] Architecture, repo, user-service, room-service, docker-compose (branch `feature/core-services`)
- [ ] #1 Unit tests for user-service and room-service - previous suite was removed during the Django/session-auth restructuring; needs to be rewritten from scratch (`feature/tests-core`)
- [ ] #2 Review all pull requests, keep `develop` green, merge to `main` and tag `v1.0`
- [ ] #11 Rehearse demo; present architecture and service communication

## Duvindu (experienced, most technical work)
- [ ] #3 Message-service: edit message, pagination, internal room cleanup (`optimize-workload`)
- [ ] #4 Notification-service: mark all read + unread count (`optimize-workload`)
- [ ] #12 Gateway: rate limiting (`optimize-workload`)
- [ ] #13 CI: GitHub Actions running the smoke test (`feature/ci`)
- [ ] #5 Kubernetes manifests, stretch goal - gateway via APISIX, notifications via Novu (`feature/kubernetes`)
- [ ] #11 Rehearse demo; present message flow, resilience demo (stop a service), CI/Kubernetes

## Amaya (guided, well-scoped tasks)
- [ ] #6 Final architecture diagram (`feature/diagram`)
- [ ] #7 Postman collection for all endpoints (`feature/postman`)
- [ ] #8 No web UI exists anymore (removed along with the gateway) - no longer applicable as written; ask Tharindu for a replacement task (`feature/frontend-polish`)
- [ ] #9 Activity-service: filter feed by event type, one small change (`feature/activity-filter`)
- [ ] #10 Report and slides: project idea, scenarios, team contributions
- [ ] #11 Rehearse demo; present the project idea and a Postman walk-through of the API (no web UI anymore)

## Shared before submission
- [ ] Everyone can run `docker compose up --build` on their own machine
- [ ] Each service's `/health` responds and the register -> create room -> post message -> activity feed flow works end to end (no `scripts/smoke_test.py` anymore - check manually via curl/Postman)
- [ ] Rehearse the demo twice; each person explains the parts they built
- [ ] Tag the final commit on `main` (`v1.0`)

## Evidence of contribution
GitHub Insights -> Contributors, the pull request list, issues assigned per person, and `git shortlog -sn` output in the report.
