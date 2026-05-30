# Public-subnet-only VPC.
#
# WHY no private subnets + NAT Gateway: NAT is $32/month minimum. For a
# short-lived demo we don't need it. EKS nodes get public IPs and can
# reach the internet directly. PRD §16 explicitly forbids NAT for daily dev.

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.13"

  name = "${var.project_name}-vpc"
  cidr = var.vpc_cidr

  azs            = var.azs
  public_subnets = [cidrsubnet(var.vpc_cidr, 4, 0)]
  # No private subnets, no NAT.

  enable_dns_hostnames = true
  enable_dns_support   = true

  # EKS needs these subnet tags to discover where to place ELBs/nodes.
  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }
}
