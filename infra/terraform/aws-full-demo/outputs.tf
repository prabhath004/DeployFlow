output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "kubeconfig_command" {
  value = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

output "rds_endpoint" {
  value     = aws_db_instance.deployflow.address
  sensitive = true
}

output "redis_endpoint" {
  value     = aws_elasticache_cluster.deployflow.cache_nodes[0].address
  sensitive = true
}

output "vpc_id" {
  value = module.vpc.vpc_id
}

# Reminder, printed on every plan/apply.
output "destroy_reminder" {
  value = <<-EOT
    ┌─────────────────────────────────────────────────────────────────┐
    │  REMINDER: this stack costs real money (~$100/month if forgotten)│
    │  After the demo, run: terraform destroy                          │
    │  Then verify in Cost Explorer that the bill stopped climbing.    │
    └─────────────────────────────────────────────────────────────────┘
  EOT
}
