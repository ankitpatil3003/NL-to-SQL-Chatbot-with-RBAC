# PostgreSQL 16 on RDS, private subnets only. pgvector and pg_trgm are available on RDS and
# created by the migrations (db/*.sql). PostgreSQL 15+ on RDS forces SSL (rds.force_ssl = 1), so
# the app's DATABASE_URL carries ?ssl=require.

resource "random_password" "db_master" {
  length  = 32
  special = false # goes into a URL
}

resource "aws_db_subnet_group" "main" {
  name       = var.project
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "main" {
  identifier     = var.project
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.db_instance_class

  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = "pharma"
  username = "pharma"
  password = random_password.db_master.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  multi_az               = false # user decision: minimal sizing

  backup_retention_period    = 1
  auto_minor_version_upgrade = true
  apply_immediately          = true

  # Demo environment: `terraform destroy` removes it cleanly. For real production set
  # deletion_protection = true and keep a final snapshot.
  deletion_protection = false
  skip_final_snapshot = true
}

locals {
  db_url = "postgresql+asyncpg://pharma:${random_password.db_master.result}@${aws_db_instance.main.address}:5432/pharma?ssl=require"
}
