variable "project_name" {
  type        = string
  default     = "deployflow"
  description = "Used as a name prefix and tag for every resource."
}

variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "Single region — PRD §16 cost rule: never multi-region."
}

variable "log_retention_days" {
  type        = number
  default     = 3
  description = "CloudWatch log retention — PRD §16: 1–3 days only."
}

variable "s3_artifact_expiration_days" {
  type        = number
  default     = 7
  description = "S3 lifecycle: delete deployment logs/artifacts after N days."
}

variable "sqs_max_receive_count" {
  type        = number
  default     = 5
  description = "After this many failed receives, the message goes to the DLQ."
}

variable "sqs_visibility_timeout" {
  type        = number
  default     = 60
  description = "How long a worker has to ack a message before it's redelivered."
}

variable "ecr_max_image_count" {
  type        = number
  default     = 10
  description = "ECR lifecycle: keep only the most recent N images."
}

variable "deployed_app_port" {
  type        = number
  default     = 8000
  description = "Container port exposed by deployed apps on ECS Fargate."
}

variable "ecs_task_cpu" {
  type        = number
  default     = 256
  description = "Fargate task CPU units for deployed apps. 256 is the smallest option."
}

variable "ecs_task_memory" {
  type        = number
  default     = 512
  description = "Fargate task memory MB for deployed apps. 512 pairs with 256 CPU."
}

variable "ecs_cpu_architecture" {
  type        = string
  default     = "ARM64"
  description = "CPU architecture for deployed app tasks. ARM64 matches Apple Silicon local Docker builds."

  validation {
    condition     = contains(["ARM64", "X86_64"], var.ecs_cpu_architecture)
    error_message = "ecs_cpu_architecture must be ARM64 or X86_64."
  }
}

# Common tags applied to every resource. The Project tag is the PRD §16 audit hook.
locals {
  tags = {
    Project   = "DeployFlow"
    ManagedBy = "Terraform"
    Stack     = "free-first"
  }
}
