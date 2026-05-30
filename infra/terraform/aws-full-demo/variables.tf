variable "project_name" {
  type    = string
  default = "deployflow-demo"
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "vpc_cidr" {
  type    = string
  default = "10.42.0.0/16"
}

# Single AZ on purpose — PRD §16: no multi-AZ for the demo, half the cost.
variable "azs" {
  type    = list(string)
  default = ["us-east-1a"]
}

# Match the free-first stack's defaults so artifacts/queues line up.
variable "db_username" {
  type    = string
  default = "deployflow"
}

variable "db_password" {
  type      = string
  sensitive = true
  # No default — Terraform will prompt. Or use TF_VAR_db_password.
}

locals {
  tags = {
    Project   = "DeployFlow"
    ManagedBy = "Terraform"
    Stack     = "full-demo"
    # If you see this tag still present 24h after the demo, that means
    # `terraform destroy` was never run. Set an alarm.
    Ephemeral = "true"
  }
}
