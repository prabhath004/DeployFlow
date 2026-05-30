# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current State

This repository is **pre-implementation**: it contains only `deployflow.md` (the technical PRD) and a placeholder `README.md`. No backend, frontend, infra, or tests exist yet. Treat `deployflow.md` as the source of truth for scope, architecture, and sequencing — when starting work, read it first and follow the phase ordering in §15.

## The Cost Constraint Is Load-Bearing

DeployFlow's defining constraint is **"free-first"** — it is explicitly designed as a learning project that must not incur surprise AWS bills. This shapes nearly every architectural decision and overrides convenience:

- **Three environments, not one** (PRD §4): Local Full ($0, primary dev), Cheap AWS Hybrid (SQS/S3/ECR only, API+worker still local), Full AWS Demo (EKS/RDS/ElastiCache/ALB — short-lived, must be `terraform destroy`'d after).
- **Never introduce always-on expensive services** into the default dev or CI path: EKS, NAT Gateway, ALB, RDS, ElastiCache, Multi-AZ anything. These belong only in the `aws-full-demo` Terraform environment.
- **Keep the three Terraform environments separated** under `infra/terraform/{local,aws-free-first,aws-full-demo}/` so the demo stack cannot be applied by accident.
- Cost guardrails (PRD §16) — tag everything `Project=DeployFlow`, S3/ECR lifecycle cleanup, CloudWatch retention 1–3 days, single region — are requirements, not suggestions.

If a change would make the "run locally for $0" path harder or push the user toward always-on AWS, surface the tradeoff before implementing.

## Architecture (from PRD §6)

The system is a queue-based deployment orchestrator with a strict API → DB → queue → worker split:

```
FastAPI API  ──writes──►  PostgreSQL (source of truth)
     │                         ▲
     ├──caches──►  Redis  ─────┤  (status TTL cache, pub/sub for log streaming, rate limit, worker heartbeat)
     │
     └──enqueues──►  Queue (Redis queue locally; AWS SQS in hybrid)  ──►  Worker
                                                                            │
                                                                            ├─ updates deployment state in Postgres
                                                                            ├─ writes deployment_logs rows
                                                                            └─ publishes log lines to Redis pub/sub
```

Cross-cutting concerns that span multiple files:

- **Deployment state machine** (PRD §13): `QUEUED → RUNNING → BUILDING → [PUSHING_IMAGE →] DEPLOYING → SUCCEEDED|FAILED|CANCELLED`, with `FAILED → RETRYING → QUEUED`. Invalid transitions must be blocked at the service layer, not just the DB. The worker (`backend/app/workers/deployment_worker.py`) and the deployment service (`backend/app/services/deployment_service.py`) must agree on transitions.
- **Queue abstraction**: API code must publish through a `queue_service` interface so the local Redis queue and AWS SQS are swappable without touching routes or workers. Job message shape is fixed in PRD §9.7.
- **Cache-aside on deployment status**: writes go to Postgres first, then update the Redis key `deployment:{id}:status` (TTL 10s). Reads check Redis, fall back to Postgres on miss. Don't invert this order.
- **Real-time logs**: worker writes to `deployment_logs` (Postgres) *and* publishes to Redis pub/sub. The SSE endpoint `GET /deployments/{id}/logs/stream` subscribes to pub/sub — it does not poll Postgres.
- **Idempotency**: deployment triggers use the `idempotency_keys` table (PRD §12) to prevent duplicate jobs from retried client requests.
- **Ownership checks** run on every project/deployment route — JWT gives `user_id`, and the service layer must verify the resource belongs to that user before acting.

## Planned Layout

The target structure is in PRD §14. Key points future instances should preserve:

- `backend/app/` follows a routes → services → repositories → models layering. Routes stay thin; business logic and state-machine enforcement live in `services/`.
- `workers/deployment_worker.py` is a separate process, not an in-process background task. It shares models/repositories with the API but has its own entrypoint and Dockerfile target.
- `observability/` (`logging.py`, `tracing.py`, `metrics.py`) is wired into both the API and the worker — OpenTelemetry traces should connect the API request to the worker job (PRD §17 criterion 15).

## Build Phase Order (PRD §15)

Phases are sequenced so that AWS isn't touched until Phase 8. Don't pull AWS work earlier — the local stack (Phases 1–7) must run end-to-end on Docker Compose with $0 cost before SQS/S3/ECR are introduced. EKS work (Phase 12) is explicitly optional and demo-only.

## Commands

No build/test/lint commands exist yet. Once `backend/` is scaffolded the expected entrypoints (per the PRD) will be:

- Local full stack: `docker-compose up` (Phase 7)
- API dev server: standard `uvicorn app.main:app --reload` from `backend/`
- Worker: `python -m app.workers.deployment_worker` from `backend/`
- Migrations: `alembic upgrade head` from `backend/`

Update this section once the actual commands are committed.
