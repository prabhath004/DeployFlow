resource "aws_cloudwatch_log_group" "deployflow" {
  name              = "/deployflow"
  retention_in_days = var.log_retention_days
}
