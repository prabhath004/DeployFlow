resource "aws_elasticache_subnet_group" "deployflow" {
  name       = "${var.project_name}-redis"
  subnet_ids = module.vpc.public_subnets
}

resource "aws_security_group" "redis" {
  name        = "${var.project_name}-redis"
  description = "Redis ingress from inside the VPC only"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_elasticache_cluster" "deployflow" {
  cluster_id           = "${var.project_name}-redis"
  engine               = "redis"
  node_type            = "cache.t4g.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.deployflow.name
  security_group_ids   = [aws_security_group.redis.id]
}
