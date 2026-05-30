# DeployFlow — Free-first AWS infrastructure

Terraform for the **cheap** AWS resources DeployFlow uses: SQS + DLQ, S3 bucket, ECR repo, IAM user, CloudWatch log group. All effectively free under the AWS free tier and ongoing free pricing.

This stack is deliberately small. EKS, RDS, ElastiCache, ALB, NAT Gateway, CloudFront — none of those are here. They're in `../aws-full-demo/` and are demo-only per PRD §16.

## Before you apply

**Do these three things first, in order, no exceptions:**

1. **Create AWS Budgets** — both via Console:
   - Budget #1: $5/month, alert at 50% and 100%
   - Budget #2: $10/month, alert at 100% — this is the "something is seriously wrong" line
   These take 2 minutes and have saved more accidental bills than anything else.

2. **Confirm your region** — `us-east-1` is the default here; pick one and never use multi-region for this project.

3. **Confirm you have credentials** with permission to create SQS/S3/ECR/IAM/CloudWatch resources. The simplest path: an admin IAM user / SSO role for your own account.

## Apply

```sh
cd infra/terraform/aws-free-first
terraform init
terraform plan      # review what's about to be created — should be ~10 resources
terraform apply     # type 'yes' when satisfied
```

After apply:

```sh
# print the env vars you need to plug into backend/.env
terraform output env_block
# get the access keys (sensitive)
terraform output -raw iam_access_key_id
terraform output -raw iam_secret_access_key
```

Then in `backend/.env`:

```env
QUEUE_BACKEND=sqs
AWS_REGION=us-east-1
# AWS_ENDPOINT_URL deliberately unset → boto3 hits real AWS
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789012/deployflow-deployments
SQS_DLQ_URL=https://sqs.us-east-1.amazonaws.com/123456789012/deployflow-deployments-dlq
ARTIFACTS_BACKEND=s3
S3_ARTIFACTS_BUCKET=deployflow-artifacts-abcdef12
ECR_REPOSITORY_URI=123456789012.dkr.ecr.us-east-1.amazonaws.com/deployflow
```

Then `docker compose -f docker-compose.yml up -d` — same containers, real AWS endpoints.

## What you get

| Resource | Purpose | Monthly cost |
|---|---|---|
| `aws_sqs_queue.deployments` | the deployment job queue | $0 for first 1M req |
| `aws_sqs_queue.deployments_dlq` | failed messages after 5 retries | ~$0 |
| `aws_s3_bucket.artifacts` | per-deploy log archives, 7-day expiry | <$0.01 |
| `aws_ecr_repository.deployflow` | container images, keep last 10 | <$0.01 |
| `aws_cloudwatch_log_group./deployflow` | runtime logs, 3-day retention | <$0.01 |
| `aws_iam_user.deployflow-runtime` | credentials for the app | $0 |

Realistic total for a dev/portfolio account: **a few cents per month**, often $0 thanks to free-tier allowances.

## Cost guardrails baked in

- All buckets have `public_access_block` (no accidental public exposure).
- S3 lifecycle deletes `deployments/*` after 7 days.
- S3 incomplete-multipart cleanup after 1 day (these silently rack up otherwise).
- ECR lifecycle keeps only the last 10 images.
- CloudWatch retention is 3 days, not "never expires."
- Every resource is tagged `Project=DeployFlow` so you can audit in Cost Explorer.

## Destroy

```sh
terraform destroy
```

ECR repos with images and S3 buckets with objects need `-force` flags or empty-first; if Terraform complains, empty the bucket and delete images in the AWS Console first, then re-run `destroy`.

## Why no Terraform state backend (S3/DynamoDB)?

Solo dev project. Local state in `terraform.tfstate` is fine. Add `s3` + `dynamodb` backend blocks when more than one human starts running `apply`.
