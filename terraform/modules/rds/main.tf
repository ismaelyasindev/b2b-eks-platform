variable "cluster_name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "allowed_security_group_ids" {
  type = list(string)
}

variable "instance_classes" {
  type = map(string)
}

resource "aws_db_subnet_group" "this" {
  name       = "${var.cluster_name}-rds"
  subnet_ids = var.private_subnet_ids
}

resource "aws_security_group" "rds" {
  name   = "${var.cluster_name}-rds"
  vpc_id = var.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "postgres" {
  for_each = toset(var.allowed_security_group_ids)

  security_group_id            = aws_security_group.rds.id
  referenced_security_group_id = each.value
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "rds" {
  security_group_id = aws_security_group.rds.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_db_instance" "this" {
  for_each = var.instance_classes

  identifier     = "${var.cluster_name}-${each.key}"
  engine         = "postgres"
  engine_version = "16"
  instance_class = each.value

  allocated_storage     = 20
  max_allocated_storage = 50
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "b2b"
  username = "postgres"
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  multi_az               = false
  availability_zone      = null

  backup_retention_period = 1
  skip_final_snapshot     = true
  deletion_protection     = false
  apply_immediately       = true
}

output "endpoints" {
  value = { for env, db in aws_db_instance.this : env => db.address }
}

output "master_user_secret_arns" {
  value = { for env, db in aws_db_instance.this : env => try(db.master_user_secret[0].secret_arn, null) }
}

output "security_group_id" {
  value = aws_security_group.rds.id
}
