# Real deployment target: ECS Fargate.
#
# This deliberately uses the default VPC and public subnets to avoid NAT Gateway,
# ALB, RDS, or other always-on costs. Each deployed app runs as one tiny Fargate
# task behind a public IP. The worker creates/updates ECS services dynamically.

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_ecs_cluster" "deployflow_apps" {
  name = "${var.project_name}-apps"
}

resource "aws_cloudwatch_log_group" "deployflow_apps" {
  name              = "/deployflow/apps"
  retention_in_days = var.log_retention_days
}

resource "aws_security_group" "ecs_apps" {
  name        = "${var.project_name}-ecs-apps"
  description = "Public ingress for DeployFlow demo app tasks"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "App HTTP port"
    from_port   = var.deployed_app_port
    to_port     = var.deployed_app_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow outbound image pulls and app egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

data "aws_iam_policy_document" "ecs_task_execution_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "ecs_task_execution" {
  name               = "${var.project_name}-ecs-task-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_execution_assume_role.json
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
