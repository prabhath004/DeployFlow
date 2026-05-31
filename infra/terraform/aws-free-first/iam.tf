# Least-privilege IAM for the API + worker. We create a single IAM user
# whose access keys you can stuff into your .env. In a production setup
# you'd swap this for an IAM role assumed by EC2/ECS/EKS via IRSA.

resource "aws_iam_user" "deployflow_runtime" {
  name = "${var.project_name}-runtime"
}

resource "aws_iam_access_key" "deployflow_runtime" {
  user = aws_iam_user.deployflow_runtime.name
}

data "aws_iam_policy_document" "deployflow_runtime" {
  # SQS — publish + consume the deployments queue and the DLQ.
  statement {
    sid    = "SQSAccess"
    effect = "Allow"
    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:ChangeMessageVisibility",
    ]
    resources = [
      aws_sqs_queue.deployments.arn,
      aws_sqs_queue.deployments_dlq.arn,
    ]
  }

  # S3 — read/write the artifacts bucket only.
  statement {
    sid    = "S3Artifacts"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.artifacts.arn,
      "${aws_s3_bucket.artifacts.arn}/*",
    ]
  }

  # ECR — push/pull the deployflow repo only.
  statement {
    sid    = "ECRAuth"
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken",
    ]
    resources = ["*"] # the auth-token call doesn't accept resource scoping
  }
  statement {
    sid    = "ECRRepo"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:DescribeRepositories",
      "ecr:DescribeImages",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:PutImage",
    ]
    resources = [aws_ecr_repository.deployflow.arn]
  }

  # CloudWatch Logs — write into the deployflow log group only.
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "${aws_cloudwatch_log_group.deployflow.arn}:*",
      "${aws_cloudwatch_log_group.deployflow_apps.arn}:*",
    ]
  }

  # ECS Fargate — create/update one-service-per-project demo deployments.
  statement {
    sid    = "ECSDeployments"
    effect = "Allow"
    actions = [
      "ecs:CreateService",
      "ecs:UpdateService",
      "ecs:DescribeServices",
      "ecs:ListTasks",
      "ecs:DescribeTasks",
      "ecs:RegisterTaskDefinition",
      "ecs:DescribeTaskDefinition",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "PassECSTaskExecutionRole"
    effect = "Allow"
    actions = [
      "iam:PassRole",
    ]
    resources = [aws_iam_role.ecs_task_execution.arn]
  }

  statement {
    sid    = "EC2NetworkLookup"
    effect = "Allow"
    actions = [
      "ec2:DescribeNetworkInterfaces",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_user_policy" "deployflow_runtime" {
  name   = "${var.project_name}-runtime"
  user   = aws_iam_user.deployflow_runtime.name
  policy = data.aws_iam_policy_document.deployflow_runtime.json
}
