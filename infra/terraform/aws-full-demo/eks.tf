# Minimal EKS cluster. Single managed node group, smallest instance type.
#
# Cost reality: control plane is $0.10/hr regardless of cluster size.
# Two t3.small nodes are ~$15/month each. Plan budget accordingly.

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.24"

  cluster_name    = "${var.project_name}-eks"
  cluster_version = "1.30"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.public_subnets

  cluster_endpoint_public_access = true

  enable_cluster_creator_admin_permissions = true

  eks_managed_node_groups = {
    default = {
      instance_types = ["t3.small"]
      min_size       = 1
      desired_size   = 2
      max_size       = 3
      capacity_type  = "SPOT" # cheaper, fine for a demo
      subnet_ids     = module.vpc.public_subnets
    }
  }
}
