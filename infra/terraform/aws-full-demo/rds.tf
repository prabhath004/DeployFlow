# Smallest possible RDS Postgres. Single-AZ, smallest burstable instance.

resource "aws_db_subnet_group" "deployflow" {
  name       = "${var.project_name}-pg"
  subnet_ids = module.vpc.public_subnets
}

resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds"
  description = "Postgres ingress from inside the VPC only"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
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

resource "aws_db_instance" "deployflow" {
  identifier              = "${var.project_name}-pg"
  engine                  = "postgres"
  engine_version          = "16"
  instance_class          = "db.t4g.micro"
  allocated_storage       = 20
  storage_type            = "gp3"
  db_name                 = "deployflow"
  username                = var.db_username
  password                = var.db_password
  multi_az                = false
  publicly_accessible     = false
  skip_final_snapshot     = true
  backup_retention_period = 0    # demo only — no backups
  deletion_protection     = false
  db_subnet_group_name    = aws_db_subnet_group.deployflow.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
}
