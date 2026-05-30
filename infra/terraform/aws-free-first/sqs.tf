resource "aws_sqs_queue" "deployments_dlq" {
  name                      = "${var.project_name}-deployments-dlq"
  message_retention_seconds = 1209600 # 14 days, SQS max — give yourself time to inspect failures
}

resource "aws_sqs_queue" "deployments" {
  name                       = "${var.project_name}-deployments"
  visibility_timeout_seconds = var.sqs_visibility_timeout
  message_retention_seconds  = 345600 # 4 days

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.deployments_dlq.arn
    maxReceiveCount     = var.sqs_max_receive_count
  })
}
