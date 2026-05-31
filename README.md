# DeployFlow

DeployFlow is a deployment orchestration platform. A user connects a GitHub repo, clicks deploy, watches live logs, and gets a real running URL on AWS ECS Fargate.

It is built like a real cloud control plane: authenticated API, PostgreSQL, Redis, queue workers, Docker builds, ECR pushes, ECS deploys, S3 log archives, Terraform infrastructure, and OpenTelemetry observability.

## What Happens Behind The Scenes

```text
Browser -> React frontend -> FastAPI
                       |
                       +-> PostgreSQL: users, projects, deployments, logs
                       +-> Redis: cache, rate limits, heartbeat, log pub/sub
                       +-> Queue: Redis Streams locally or SQS in AWS mode
                                      |
                                      v
                                   Worker
                                      |
                                      +-> clone GitHub repo
                                      +-> build Docker image or static-site image
                                      +-> push image to ECR
                                      +-> deploy service to ECS Fargate
                                      +-> stream logs through Redis Pub/Sub
                                      +-> persist logs in PostgreSQL
                                      +-> archive final logs to S3
```

Normal repositories should include a root `Dockerfile`.

Static-site fallback is supported: if there is no root `Dockerfile` but there is a root `index.html`, DeployFlow generates a temporary Dockerfile and serves the site on port `8000`.

## Features

- JWT authentication and user ownership checks.
- Project CRUD for GitHub repositories.
- Asynchronous deployment jobs.
- Real-time deployment logs through Server-Sent Events.
- Deployment retry, cancel, and delete actions.
- Redis-backed deployment status cache.
- Per-user deployment rate limiting.
- Worker liveness through Redis heartbeat TTL keys.
- AWS SQS job queue in real AWS mode.
- AWS ECR image pushes.
- AWS ECS Fargate app hosting.
- AWS S3 deployment log archives.
- CloudWatch logs for ECS tasks.
- Terraform-managed low-cost AWS stack.
- OpenTelemetry traces and metrics.

## Tech Stack

| Area | Tech |
|---|---|
| Frontend | React, Vite, TypeScript, Tailwind CSS |
| API | FastAPI, Pydantic |
| Database | PostgreSQL, SQLAlchemy async, Alembic |
| Cache / realtime | Redis, Redis Pub/Sub |
| Queue | Redis Streams locally, AWS SQS in real AWS mode |
| Worker | Python async worker |
| Build / registry | Git, Docker, AWS ECR |
| Deploy target | AWS ECS Fargate |
| Artifacts / logs | AWS S3, CloudWatch Logs |
| Infra | Docker Compose, Terraform |
| Observability | OpenTelemetry, Jaeger, Prometheus, Grafana |

## Repository Layout

`backend/` contains the FastAPI app, SQLAlchemy models, repositories, services, worker, observability setup, and Alembic migrations. `frontend/` contains the React app. `infra/` contains Terraform, OpenTelemetry, Prometheus, and Grafana config. `docker-compose.yml` runs local mode, and `docker-compose.aws.yml` points the local API/worker at real AWS.

## Backend Design

The backend uses `routes -> services -> repositories -> models`. Routes handle HTTP and auth dependencies. Services enforce ownership, deployment state rules, queue publishing, cache invalidation, and AWS behavior. Repositories isolate SQLAlchemy reads and writes. Important files are `deployment_service.py`, `deployment_state_machine.py`, `queue_service.py`, `image_registry.py`, `ecs_deployer.py`, and `deployment_worker.py`.

## Deployment Lifecycle

Normal path: `PENDING -> QUEUED -> RUNNING -> BUILDING -> PUSHING_IMAGE -> DEPLOYING -> SUCCEEDED`.

Failure ends in `FAILED`. Retry is `FAILED -> RETRYING -> QUEUED`. Cancelling a non-terminal deployment moves it to `CANCELLED`. Invalid transitions are blocked in `deployment_state_machine.py`.

## Frontend Flows

Users can register, log in, create projects, trigger deployments, watch live logs, open deployed URLs, retry failures, cancel active deployments, and delete terminal deployments.

Important: deleting a deployment removes the DeployFlow database row and cascaded database logs. It does not currently delete the ECS service, ECR image, S3 archive, or CloudWatch logs.

<img width="1166" height="766" alt="image" src="https://github.com/user-attachments/assets/4799563a-4057-46b7-86d0-7e1d45a1d540" />



## API Overview

```text
POST   /auth/register
POST   /auth/login
GET    /auth/me

POST   /projects
GET    /projects
GET    /projects/{project_id}
PATCH  /projects/{project_id}
DELETE /projects/{project_id}

POST   /projects/{project_id}/deployments
GET    /projects/{project_id}/deployments
GET    /deployments/{deployment_id}
GET    /deployments/{deployment_id}/status
POST   /deployments/{deployment_id}/retry
POST   /deployments/{deployment_id}/cancel
DELETE /deployments/{deployment_id}

GET    /deployments/{deployment_id}/logs
GET    /deployments/{deployment_id}/logs/stream

GET    /health
GET    /ready
```

## Redis

Redis is not the source of truth. PostgreSQL is. Redis is used for short-lived speed and coordination.

| Use | Example | TTL |
|---|---|---|
| Deployment status cache | `deployment:{id}:status` | 10 sec |
| Project metadata cache | project metadata keys | 60 sec |
| Dashboard summary cache | dashboard summary keys | 30 sec |
| Deploy rate limit | per-user counter | 60 sec |
| Worker heartbeat | `worker:{id}:heartbeat` | 30 sec |
| Live logs | `logs:{deployment_id}` | pub/sub only |

The deployment status endpoint verifies ownership in PostgreSQL, reads Redis on cache hit, falls back to PostgreSQL on miss, then refreshes Redis.

Live logs use Redis Pub/Sub and Server-Sent Events. Historical logs are read from PostgreSQL.

## Queue

Local mode uses Redis Streams.

Real AWS mode uses SQS:

- API publishes a deployment job to SQS.
- Worker polls SQS.
- Worker processes clone/build/push/deploy.
- Worker deletes the SQS message only after processing.
- Failed messages can move to the DLQ after retries.

The queue abstraction is in `backend/app/services/queue_service.py`.

## AWS Services

Real AWS mode uses:

| Service | Purpose |
|---|---|
| SQS | Deployment job queue |
| SQS DLQ | Failed job queue |
| S3 | Deployment log archives |
| ECR | Docker image repository |
| ECS Fargate | Running deployed apps |
| CloudWatch Logs | ECS task logs |
| IAM | Runtime user, policies, task execution role |

PostgreSQL, Redis, API, and worker still run locally in Docker Compose. This keeps the control plane cheap while proving the deployment path is real.

## Terraform

Terraform lives in:

```sh
infra/terraform/aws-free-first
```

It creates SQS, SQS DLQ, S3, ECR, ECS cluster, ECS security group, ECS task execution role, CloudWatch log groups, runtime IAM user, and IAM policy.

It intentionally does not create EKS, RDS, ElastiCache, NAT Gateway, ALB, or CloudFront. Those are avoided to keep AWS credits from burning fast.

Commands:

```sh
cd infra/terraform/aws-free-first
terraform init
terraform apply
terraform output env_block
terraform destroy
```

## Cost Notes

Usually cheap:

- SQS
- Small S3 log archives
- Small ECR images
- CloudWatch with short retention
- IAM

Costs while running:

- ECS Fargate services with `desiredCount=1`

When you are done testing, destroy Terraform or delete/scale down ECS services.

## OpenTelemetry

The local stack includes:

| Tool | URL |
|---|---|
| Jaeger | `http://localhost:16686` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3001` |

API and worker export OTLP to `otel-collector:4317`.

The collector sends traces to Jaeger and exposes metrics for Prometheus. Grafana is provisioned with Prometheus and Jaeger datasources.

Config:

```text
infra/otel/collector.yaml
infra/prometheus/prometheus.yml
infra/grafana/provisioning/datasources/datasources.yml
backend/app/observability/
```

## Local Development

Start the backend stack:

```sh
docker compose up -d
docker compose exec api alembic upgrade head
curl http://localhost:8000/ready
```

Start the frontend:

```sh
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Real AWS Mode

Create `backend/.env` from Terraform outputs and secrets:

```text
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
SQS_QUEUE_URL=...
SQS_DLQ_URL=...
S3_ARTIFACTS_BUCKET=...
ECR_REPOSITORY_URI=...
ECS_CLUSTER_NAME=...
ECS_SUBNET_IDS=...
ECS_SECURITY_GROUP_ID=...
ECS_TASK_EXECUTION_ROLE_ARN=...
```

Start local API and worker pointed at AWS:

```sh
docker compose down
docker compose --env-file backend/.env \
  -f docker-compose.yml -f docker-compose.aws.yml \
  up -d postgres redis api worker
curl http://localhost:8000/ready
```

Then run the frontend and deploy a GitHub repo from the UI.

## Requirements For Deployed Repos

Preferred:

- root `Dockerfile`
- app listens on port `8000`
- image can run on Linux ARM64

Static fallback:

- root `index.html`
- no Dockerfile required
- served on port `8000`

Current limitation: framework build detection is not automatic yet. A React, Vite, or Next app without a Dockerfile and without a root `index.html` needs a Dockerfile.

## Secrets

Do not commit:

- `backend/.env`
- AWS access keys
- Terraform state containing credentials
- JWT secrets

Use `.env.example` files as templates.

## Checks

```sh
docker compose exec api python -m compileall app
cd frontend && npm run typecheck
curl http://localhost:8000/ready
```

## Current Limitations

- No automatic framework build detection beyond root `index.html`.
- No custom domains or TLS.
- No ALB or CloudFront.
- Deployment delete does not remove AWS resources yet.
- The real-AWS control plane still uses local PostgreSQL and Redis.
- ECS apps use public IPs, which is fine for demos but not production.

## Cleanup

Stop local containers:

```sh
docker compose down
```

Remove AWS resources:

```sh
cd infra/terraform/aws-free-first
terraform destroy
```

Run cleanup after real AWS testing so ECS does not keep billing.
