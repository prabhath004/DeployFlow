# These outputs are the values you plug into the API/worker .env to switch
# from LocalStack to real AWS. Print them with `terraform output`.

output "aws_region" {
  value = data.aws_region.current.name
}

output "sqs_queue_url" {
  value = aws_sqs_queue.deployments.url
}

output "sqs_dlq_url" {
  value = aws_sqs_queue.deployments_dlq.url
}

output "s3_artifacts_bucket" {
  value = aws_s3_bucket.artifacts.bucket
}

output "ecr_repository_uri" {
  value = aws_ecr_repository.deployflow.repository_url
}

output "cloudwatch_log_group" {
  value = aws_cloudwatch_log_group.deployflow.name
}

output "iam_access_key_id" {
  value     = aws_iam_access_key.deployflow_runtime.id
  sensitive = true
}

output "iam_secret_access_key" {
  value     = aws_iam_access_key.deployflow_runtime.secret
  sensitive = true
}

# Convenience: a ready-to-paste .env block.
output "env_block" {
  description = "Copy this into backend/.env after `terraform apply`."
  value = <<-EOT
    QUEUE_BACKEND=sqs
    AWS_REGION=${data.aws_region.current.name}
    # leave AWS_ENDPOINT_URL UNSET for real AWS
    AWS_ACCESS_KEY_ID=<see: terraform output -raw iam_access_key_id>
    AWS_SECRET_ACCESS_KEY=<see: terraform output -raw iam_secret_access_key>
    SQS_QUEUE_URL=${aws_sqs_queue.deployments.url}
    SQS_DLQ_URL=${aws_sqs_queue.deployments_dlq.url}
    ARTIFACTS_BACKEND=s3
    S3_ARTIFACTS_BUCKET=${aws_s3_bucket.artifacts.bucket}
    ECR_REPOSITORY_URI=${aws_ecr_repository.deployflow.repository_url}
  EOT
  sensitive = true
}
