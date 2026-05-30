resource "aws_ecr_repository" "deployflow" {
  name                 = var.project_name
  image_tag_mutability = "IMMUTABLE" # makes pushes deterministic; required for reproducibility

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Cost guardrail: keep only the last N images (PRD §16).
resource "aws_ecr_lifecycle_policy" "deployflow" {
  repository = aws_ecr_repository.deployflow.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep only the last ${var.ecr_max_image_count} images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = var.ecr_max_image_count
      }
      action = { type = "expire" }
    }]
  })
}
