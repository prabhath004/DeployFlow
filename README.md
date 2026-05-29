# DeployFlow

DeployFlow is a cloud-native deployment orchestration platform for triggering, processing, and monitoring containerized application deployments.

It provides authenticated project management, queue-based deployment processing, background workers, real-time logs, Redis caching, and observability through structured logs, metrics, and traces.

## Features

- JWT-based authentication
- Project creation for GitHub repositories
- Manual deployment triggers
- Deployment status tracking
- Queue-based background workers
- Redis caching for high-read deployment data
- Real-time deployment logs
- Idempotent deployment requests
- Retry and dead-letter queue design
- Health and readiness checks
- Dockerized local development
- AWS-ready deployment architecture
- OpenTelemetry-based observability

## Architecture

Client
  |
  v
FastAPI API
  |
  +--> PostgreSQL
  |
  +--> Redis
  |
  +--> Queue
          |
          v
        Worker
          |
          +--> Build Docker image
          +--> Push to ECR
          +--> Deploy to EKS
          +--> Emit logs/metrics/traces

## Tech Stack

**Backend:** Python, FastAPI, Pydantic, SQLAlchemy, Alembic  
**Database:** PostgreSQL  
**Cache:** Redis  
**Queue:** Redis Queue locally, AWS SQS for cloud  
**Infrastructure:** Docker, Docker Compose, Terraform  
**Cloud:** AWS S3, ECR, EKS, RDS, ElastiCache, SQS, ALB, CloudFront  
**Observability:** OpenTelemetry, structured logs, metrics, distributed traces  

## Core Flow

1. User creates a project with a GitHub repository URL.
2. User triggers a deployment.
3. API validates authentication and project ownership.
4. API creates a deployment record in PostgreSQL.
5. Deployment job is pushed to a queue.
6. Worker processes the job asynchronously.
7. Worker builds and deploys the containerized application.
8. Logs and status updates are streamed back to the user.
9. Deployment is marked as SUCCEEDED or FAILED.

## API Overview

### Health

GET /health  
GET /ready  

### Auth

POST /auth/register  
POST /auth/login  

### Projects

POST /projects  
GET /projects  
GET /projects/{project_id}  

### Deployments

POST /projects/{project_id}/deployments  
GET /projects/{project_id}/deployments  
GET /deployments/{deployment_id}  
GET /deployments/{deployment_id}/logs  
GET /deployments/{deployment_id}/logs/stream  

## Deployment States

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

## Reliability

DeployFlow includes production-style reliability patterns:

- Idempotency keys to prevent duplicate deployment requests
- Queue-based workers for long-running deployment jobs
- Retry handling with exponential backoff
- Dead-letter queue design for failed jobs
- Worker heartbeats
- Graceful shutdown
- Health and readiness endpoints
- Safe deployment state transitions

## Observability

DeployFlow is designed to capture system behavior across the API, queue, worker, and deployment lifecycle.

Tracked signals include:

- API request latency
- Deployment duration
- Queue depth
- Worker job duration
- Deployment success/failure count
- Redis cache hit/miss rate
- Distributed traces across API and worker services

