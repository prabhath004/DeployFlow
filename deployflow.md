# DeployFlow Technical PRD — Free-First Complete System

## 1. Project Name

DeployFlow

## 2. Project Summary

DeployFlow is a cloud-native deployment orchestration platform that allows users to create projects from GitHub repositories, trigger deployments, process deployments asynchronously through workers, stream logs, cache status data, and observe system behavior through logs, metrics, and traces.

The system is designed to teach production backend and platform engineering while keeping AWS cost as close to free as possible.

## 3. Main Goal

Build a complete deployment platform using a free-first architecture.

The full system should include:

1. FastAPI backend
2. PostgreSQL database
3. Redis caching
4. Queue-based worker processing
5. Deployment state machine
6. Real-time deployment logs
7. Docker and Docker Compose
8. AWS SQS
9. AWS S3
10. AWS ECR
11. OpenTelemetry
12. Terraform
13. Optional short-lived EKS demo

## 4. Cost Strategy

The project should be built in three environments.

### Environment 1: Local Full System

This is the main development environment.

Cost: $0

Use locally:

* FastAPI
* PostgreSQL container
* Redis container
* Worker container
* Redis queue or local queue
* OpenTelemetry collector
* Jaeger
* Prometheus
* Grafana
* Docker Compose

This environment should simulate the complete production system without requiring AWS services.

### Environment 2: Cheap AWS Hybrid System

This is the main AWS learning environment.

Use AWS services that are free or very low cost:

* SQS
* S3
* ECR
* CloudWatch with limited logs
* IAM
* Optional Lambda for small event handlers

Avoid always-running expensive services:

* EKS
* NAT Gateway
* ALB
* RDS
* ElastiCache

In this version, the API and worker can still run locally or on one cheap/free compute option while using AWS SQS, S3, and ECR.

### Environment 3: Full AWS Demo System

This is only for final demo, screenshots, and resume validation.

Use temporarily:

* EKS
* RDS PostgreSQL
* ElastiCache Redis
* ALB
* CloudFront
* Terraform

Important rule:

Destroy the full AWS demo after testing.

Do not leave EKS, NAT Gateway, ALB, RDS, or ElastiCache running 24/7.

---

# 5. Product Scope

## 5.1 Core User Flow

A user should be able to:

1. Register.
2. Log in.
3. Create a project using a GitHub repository URL.
4. Trigger a deployment.
5. See deployment status.
6. View deployment logs.
7. Watch deployment progress.
8. Retry failed deployments.
9. View deployment history.

## 5.2 System Flow

```text
User triggers deployment
        |
        v
FastAPI API validates user and project ownership
        |
        v
PostgreSQL stores deployment record
        |
        v
Redis caches deployment status
        |
        v
Queue receives deployment job
        |
        v
Worker processes job asynchronously
        |
        v
Worker writes logs and updates status
        |
        v
User sees deployment result
```

---

# 6. Architecture

## 6.1 Local Full Architecture

```text
Browser / API Docs
        |
        v
FastAPI API
        |
        +------------------+
        |                  |
        v                  v
PostgreSQL              Redis
        |                  |
        |                  +--> Cache
        |                  +--> Rate limiting
        |                  +--> Pub/Sub logs
        |                  +--> Worker heartbeat
        |
        v
Local Queue / Redis Queue
        |
        v
Worker Service
        |
        +--> Simulated Git clone
        +--> Simulated Docker build
        +--> Simulated deploy
        +--> Writes logs
        +--> Updates deployment status
        |
        v
OpenTelemetry Collector
        |
        +--> Jaeger
        +--> Prometheus
        +--> Grafana
```

## 6.2 Free-First AWS Hybrid Architecture

```text
Local API / Local Worker
        |
        +--> AWS SQS
        |
        +--> AWS S3
        |
        +--> AWS ECR
        |
        +--> CloudWatch Logs
```

In this version:

* PostgreSQL runs locally.
* Redis runs locally.
* API runs locally.
* Worker runs locally.
* SQS is used as the real AWS queue.
* S3 is used for logs/artifacts.
* ECR is used for Docker image storage.

This gives real AWS experience without running expensive infrastructure.

## 6.3 Optional Full AWS Demo Architecture

```text
CloudFront
    |
    v
S3 Frontend
    |
    v
ALB
    |
    v
EKS API Service
    |
    +--------------------+
    |                    |
    v                    v
RDS PostgreSQL       ElastiCache Redis
    |
    v
SQS
    |
    v
EKS Worker Service
    |
    +--> S3 logs/artifacts
    +--> ECR images
    +--> EKS app deployments
    +--> OpenTelemetry
```

This architecture should only be used for short testing/demo sessions.

---

# 7. Tech Stack

## Backend

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* Alembic
* PostgreSQL
* JWT authentication

## Cache

* Redis
* Cache-aside pattern
* TTL-based status caching
* Redis Pub/Sub for logs
* Redis rate limiting

## Queue

Local:

* Redis queue or simple Python queue

AWS:

* SQS standard queue
* SQS dead-letter queue

## Worker

* Python worker process
* Async job processing
* Deployment state updates
* Log writing
* Retry support
* Graceful shutdown

## Infrastructure

* Docker
* Docker Compose
* Terraform
* AWS IAM
* AWS SQS
* AWS S3
* AWS ECR
* Optional EKS demo

## Observability

* OpenTelemetry
* Structured JSON logs
* Prometheus
* Grafana
* Jaeger
* CloudWatch limited logs

---

# 8. AWS Service Plan

## Use Early

These are safe and useful:

### IAM

Purpose:

* Create least-privilege permissions.
* Create roles for local AWS access, GitHub Actions, and future services.

Cost:

* Free.

### SQS

Purpose:

* Deployment job queue.
* Worker pulls deployment jobs.
* Supports retries and DLQ design.

Cost strategy:

* Keep polling controlled.
* Use long polling.
* Avoid aggressive infinite polling loops.

### S3

Purpose:

* Store deployment logs.
* Store build artifacts.
* Store frontend later.

Cost strategy:

* Store tiny files only.
* Enable lifecycle cleanup.
* Delete test artifacts regularly.

### ECR

Purpose:

* Store Docker images.

Cost strategy:

* Push small images.
* Delete old images.
* Add lifecycle policy.

### CloudWatch

Purpose:

* Store limited API/worker logs.
* Create simple alarms later.

Cost strategy:

* Keep log retention short.
* Do not spam logs.
* Use local Grafana/Jaeger for heavy observability.

---

## Use Later, Carefully

### RDS PostgreSQL

Purpose:

* Managed PostgreSQL.

Cost strategy:

* Use local PostgreSQL for most development.
* Use RDS only for final AWS demo.
* Single-AZ only.
* Smallest instance possible.
* Delete after demo.

### ElastiCache Redis

Purpose:

* Managed Redis.

Cost strategy:

* Use local Redis for most development.
* Use ElastiCache only for final demo.
* Delete after demo.

### ALB

Purpose:

* Route traffic to backend.

Cost strategy:

* Avoid until final cloud demo.
* Delete after demo.

### EKS

Purpose:

* Kubernetes deployment.

Cost strategy:

* Do not run 24/7.
* Use only for final demo.
* Destroy cluster after testing.

### NAT Gateway

Purpose:

* Allows private subnet resources to access internet.

Cost strategy:

* Avoid if possible.
* Use public subnet demo architecture for learning.
* Use VPC endpoints where possible.
* Never leave NAT Gateway running accidentally.

---

# 9. Functional Requirements

## 9.1 Authentication

Users can:

* Register
* Log in
* Receive JWT token
* Access protected APIs

Rules:

* Store hashed passwords only.
* Do not store plaintext passwords.
* JWT must contain user ID.
* Protected routes require valid token.

## 9.2 Project Management

Users can:

* Create a project.
* List their projects.
* View one project.
* Update a project.
* Archive/delete a project.

Project fields:

```text
id
user_id
name
repository_url
branch
status
created_at
updated_at
```

## 9.3 Deployment Trigger

Users can trigger a deployment for a project they own.

Flow:

```text
POST /projects/{project_id}/deployments
        |
        v
Check auth
        |
        v
Check ownership
        |
        v
Create deployment row
        |
        v
Set status QUEUED
        |
        v
Cache status in Redis
        |
        v
Send job to queue
        |
        v
Return deployment_id
```

## 9.4 Deployment Worker

Worker should:

1. Poll queue.
2. Read deployment job.
3. Mark deployment as RUNNING.
4. Write log: deployment started.
5. Mark deployment as BUILDING.
6. Simulate or run Docker build.
7. Mark deployment as DEPLOYING.
8. Simulate or run deployment.
9. Mark deployment as SUCCEEDED or FAILED.
10. Write final log.

## 9.5 Deployment Logs

Logs should include:

```text
id
deployment_id
level
source
message
created_at
```

Example:

```text
INFO | worker | Deployment started
INFO | worker | Building image
INFO | worker | Deployment succeeded
```

## 9.6 Redis Caching

Cache deployment status.

Key format:

```text
deployment:{deployment_id}:status
```

Example:

```text
deployment:dep_123:status = BUILDING
```

Cache TTL:

```text
deployment status: 10 seconds
project metadata: 60 seconds
dashboard summary: 30 seconds
```

## 9.7 Queue Processing

Deployment job message:

```json
{
  "deployment_id": "dep_123",
  "project_id": "prj_123",
  "user_id": "usr_123",
  "repository_url": "https://github.com/user/repo",
  "branch": "main",
  "attempt": 1
}
```

Queue requirements:

* API publishes deployment jobs.
* Worker consumes deployment jobs.
* Worker handles failures.
* Failed jobs should retry later.
* After max attempts, job goes to DLQ.

## 9.8 Real-Time Logs

Local version:

* Use Redis Pub/Sub.
* API exposes SSE endpoint.
* Frontend/API docs can stream logs.

Flow:

```text
Worker writes log
        |
        v
PostgreSQL stores log
        |
        v
Redis Pub/Sub publishes log
        |
        v
API stream sends log to client
```

## 9.9 Observability

The system should emit:

* structured logs
* metrics
* traces

Track:

```text
api_request_count
api_request_latency
deployment_created_count
deployment_success_count
deployment_failure_count
worker_job_duration
queue_depth
redis_cache_hit_count
redis_cache_miss_count
```

---

# 10. Non-Functional Requirements

## 10.1 Cost

The system must be designed to avoid surprise AWS costs.

Rules:

1. Run full system locally first.
2. Use AWS SQS/S3/ECR before EKS/RDS/ElastiCache.
3. Avoid NAT Gateway.
4. Avoid always-running EKS.
5. Avoid always-running RDS.
6. Avoid always-running ElastiCache.
7. Use AWS Budgets before deploying.
8. Destroy demo infrastructure after use.

## 10.2 Reliability

The system should:

* Avoid duplicate deployments.
* Recover from worker crashes.
* Use retries for temporary failures.
* Use DLQ for repeated failures.
* Keep deployment state consistent.
* Provide health and readiness endpoints.

## 10.3 Security

The system should:

* Hash passwords.
* Use JWT auth.
* Enforce ownership checks.
* Store secrets in `.env` locally.
* Use IAM least privilege in AWS.
* Avoid logging secrets.
* Keep database and Redis private in full AWS mode.

## 10.4 Performance

Local targets:

```text
GET /health under 100ms
POST /deployments under 500ms
GET /deployments/{id} under 200ms
Worker job simulation under 10 seconds
```

Cloud targets:

```text
SQS message processing under 5 seconds
Deployment status cache read under 100ms
API p95 under 500ms for normal reads
```

---

# 11. API Design

## Health

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

```http
GET /ready
```

Response:

```json
{
  "api": "ok",
  "database": "ok",
  "redis": "ok",
  "queue": "ok"
}
```

## Auth

```http
POST /auth/register
```

Request:

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

```http
POST /auth/login
```

Request:

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

Response:

```json
{
  "access_token": "token",
  "token_type": "bearer"
}
```

## Projects

```http
POST /projects
GET /projects
GET /projects/{project_id}
PATCH /projects/{project_id}
DELETE /projects/{project_id}
```

Create project request:

```json
{
  "name": "My API",
  "repository_url": "https://github.com/user/repo",
  "branch": "main"
}
```

## Deployments

```http
POST /projects/{project_id}/deployments
GET /projects/{project_id}/deployments
GET /deployments/{deployment_id}
POST /deployments/{deployment_id}/retry
POST /deployments/{deployment_id}/cancel
```

Trigger deployment request:

```json
{
  "branch": "main"
}
```

Response:

```json
{
  "deployment_id": "dep_123",
  "project_id": "prj_123",
  "status": "QUEUED"
}
```

## Logs

```http
GET /deployments/{deployment_id}/logs
GET /deployments/{deployment_id}/logs/stream
```

---

# 12. Database Schema

## users

```text
id
email
password_hash
created_at
updated_at
```

## projects

```text
id
user_id
name
repository_url
branch
status
created_at
updated_at
```

## deployments

```text
id
project_id
user_id
status
branch
commit_sha
image_uri
error_message
started_at
finished_at
created_at
updated_at
```

## deployment_logs

```text
id
deployment_id
level
source
message
created_at
```

## idempotency_keys

```text
id
user_id
key
request_hash
response_body
created_at
```

## worker_heartbeats

```text
id
worker_id
last_seen_at
status
```

---

# 13. Deployment State Machine

States:

```text
PENDING
QUEUED
RUNNING
BUILDING
PUSHING_IMAGE
DEPLOYING
SUCCEEDED
FAILED
CANCELLED
RETRYING
```

MVP flow:

```text
QUEUED -> RUNNING -> BUILDING -> DEPLOYING -> SUCCEEDED
```

Advanced flow:

```text
QUEUED -> RUNNING -> BUILDING -> PUSHING_IMAGE -> DEPLOYING -> SUCCEEDED
```

Failure flow:

```text
RUNNING -> FAILED
BUILDING -> FAILED
PUSHING_IMAGE -> FAILED
DEPLOYING -> FAILED
FAILED -> RETRYING -> QUEUED
```

Invalid transitions should be blocked.

---

# 14. Project Structure

```text
DeployFlow/
  backend/
    app/
      main.py

      api/
        routes/
          health.py
          auth.py
          projects.py
          deployments.py
          logs.py

      core/
        config.py
        security.py

      db/
        database.py

      models/
        user.py
        project.py
        deployment.py
        deployment_log.py
        idempotency_key.py

      schemas/
        auth.py
        project.py
        deployment.py
        log.py

      repositories/
        user_repo.py
        project_repo.py
        deployment_repo.py
        log_repo.py

      services/
        auth_service.py
        project_service.py
        deployment_service.py
        cache_service.py
        queue_service.py
        log_service.py

      workers/
        deployment_worker.py

      observability/
        logging.py
        tracing.py
        metrics.py

    tests/
    alembic/
    Dockerfile
    requirements.txt

  frontend/
    src/
    Dockerfile

  infra/
    terraform/
      local/
      aws-free-first/
      aws-full-demo/

  k8s/
    api-deployment.yaml
    worker-deployment.yaml
    service.yaml
    ingress.yaml

  docker-compose.yml
  README.md
```

---

# 15. Build Phases

## Phase 1: Local Backend Foundation

Build:

* FastAPI app
* `/health`
* `/ready`
* folder structure
* config system

No AWS.

## Phase 2: PostgreSQL

Build:

* PostgreSQL local container
* SQLAlchemy setup
* Alembic setup
* users table
* projects table
* deployments table
* deployment_logs table

No AWS.

## Phase 3: Auth + Ownership

Build:

* register
* login
* password hashing
* JWT auth
* protected routes
* ownership checks

No AWS.

## Phase 4: Deployment API

Build:

* create project
* trigger deployment
* deployment state machine
* deployment history
* deployment logs endpoint

No AWS.

## Phase 5: Redis

Build:

* Redis local container
* cache service
* deployment status cache
* rate limit deployment triggers
* worker heartbeat keys

No AWS.

## Phase 6: Local Queue + Worker

Build:

* local Redis queue
* worker process
* simulated deployment job
* worker status updates
* worker logs

No AWS.

## Phase 7: Docker Compose Full Local Stack

Build:

* API container
* worker container
* PostgreSQL container
* Redis container
* OTel collector
* Jaeger
* Prometheus
* Grafana

Cost: $0.

## Phase 8: AWS SQS Integration

Build:

* SQS queue
* SQS DLQ
* queue service abstraction
* local API publishes to SQS
* local worker consumes from SQS

AWS used:

* IAM
* SQS

Avoid:

* EKS
* RDS
* ElastiCache
* NAT Gateway

## Phase 9: AWS S3 + ECR

Build:

* store deployment logs/artifacts in S3
* build Docker image locally
* push image to ECR
* add ECR lifecycle policy

AWS used:

* S3
* ECR
* IAM

Avoid:

* EKS for now

## Phase 10: OpenTelemetry

Build locally:

* structured logs
* traces
* metrics
* OTel collector
* Jaeger dashboard
* Prometheus metrics
* Grafana dashboard

AWS optional:

* send limited logs to CloudWatch

## Phase 11: Terraform Free-First

Create Terraform for:

* SQS
* SQS DLQ
* S3 bucket
* ECR repo
* IAM policy
* CloudWatch log group

Do not create:

* EKS
* RDS
* ElastiCache
* NAT Gateway
* ALB

## Phase 12: Optional Full AWS Demo

Create separate Terraform environment:

```text
aws-full-demo
```

This may create:

* VPC
* EKS
* RDS
* ElastiCache
* ALB
* CloudFront

Rules:

* Run only for demo.
* Record demo.
* Take screenshots.
* Run `terraform destroy`.

---

# 16. Cost Guardrails

Before any AWS deployment:

1. Create AWS Budget alert at $5.
2. Create second alert at $10.
3. Use one AWS region only.
4. Tag every resource with `Project=DeployFlow`.
5. Use Terraform for all AWS resources.
6. Never manually create random resources.
7. Set S3 lifecycle cleanup.
8. Set ECR lifecycle cleanup.
9. Set CloudWatch log retention to 1 or 3 days.
10. Destroy full AWS demo after testing.

Avoid for daily development:

```text
EKS
NAT Gateway
ALB
RDS
ElastiCache
Multi-AZ anything
```

Use daily:

```text
Docker Compose
Local PostgreSQL
Local Redis
Local OTel stack
SQS
S3
ECR
```

---

# 17. Final Success Criteria

DeployFlow is complete when:

1. User can register and log in.
2. User can create a project.
3. User can trigger deployment.
4. Deployment is stored in PostgreSQL.
5. Deployment status is cached in Redis.
6. Deployment job is sent to queue.
7. Worker processes deployment asynchronously.
8. Worker writes logs.
9. User can view deployment status.
10. User can view deployment logs.
11. Local full stack runs with Docker Compose.
12. API and worker can use AWS SQS.
13. Worker can upload artifacts/logs to S3.
14. Docker image can be pushed to ECR.
15. OpenTelemetry traces show API-to-worker flow.
16. Terraform creates free-first AWS resources.
17. Optional EKS demo is completed and destroyed safely.

---

# 18. Resume-Ready Description

DeployFlow is a cloud-native deployment orchestration platform built with FastAPI, PostgreSQL, Redis, Docker, AWS SQS, S3, ECR, Terraform, and OpenTelemetry. It supports authenticated project management, asynchronous deployment workers, Redis-backed status caching, real-time deployment logs, queue-based job processing, idempotent deployment triggers, retry/DLQ design, and distributed observability across API and worker services.
