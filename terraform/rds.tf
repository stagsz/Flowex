# Flowex Infrastructure - RDS Configuration
# PostgreSQL database with Multi-AZ support for production

# -----------------------------------------------------------------------------
# Random password for database
# -----------------------------------------------------------------------------

resource "random_password" "db_password" {
  length  = 32
  special = false
}

# -----------------------------------------------------------------------------
# RDS Instance
# -----------------------------------------------------------------------------

resource "aws_db_instance" "main" {
  identifier = "${local.name_prefix}-postgres"

  # Engine configuration
  engine               = "postgres"
  engine_version       = "15.4"
  instance_class       = local.is_production ? local.env_config.db_instance_class : var.db_instance_class
  parameter_group_name = aws_db_parameter_group.main.name

  # Storage
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.main.arn

  # Database
  db_name  = "flowex"
  username = "flowex_admin"
  password = random_password.db_password.result
  port     = 5432

  # Network
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.database.id]
  publicly_accessible    = false

  # High availability
  multi_az = local.is_production ? local.env_config.db_multi_az : var.db_multi_az

  # Backup
  backup_retention_period   = var.db_backup_retention_days
  backup_window             = "03:00-04:00"
  maintenance_window        = "Mon:04:00-Mon:05:00"
  copy_tags_to_snapshot     = true
  delete_automated_backups  = !local.is_production
  final_snapshot_identifier = local.is_production ? "${local.name_prefix}-final-snapshot" : null
  skip_final_snapshot       = !local.is_production

  # Monitoring
  performance_insights_enabled          = local.is_production
  performance_insights_retention_period = local.is_production ? 7 : 0
  monitoring_interval                   = local.is_production ? 60 : 0
  monitoring_role_arn                   = local.is_production ? aws_iam_role.rds_monitoring[0].arn : null
  enabled_cloudwatch_logs_exports       = ["postgresql", "upgrade"]

  # Protection
  deletion_protection = local.is_production ? local.env_config.db_deletion_protection : var.db_deletion_protection

  # Upgrades
  auto_minor_version_upgrade  = true
  allow_major_version_upgrade = false
  apply_immediately           = !local.is_production

  tags = {
    Name = "${local.name_prefix}-postgres"
  }

  lifecycle {
    prevent_destroy = false
  }
}

# -----------------------------------------------------------------------------
# RDS Parameter Group
# -----------------------------------------------------------------------------

resource "aws_db_parameter_group" "main" {
  name        = "${local.name_prefix}-postgres-params"
  family      = "postgres15"
  description = "PostgreSQL parameters for ${local.name_prefix}"

  parameter {
    name  = "log_statement"
    value = "ddl"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }

  parameter {
    name  = "pg_stat_statements.track"
    value = "all"
  }

  tags = {
    Name = "${local.name_prefix}-postgres-params"
  }
}

# -----------------------------------------------------------------------------
# Database Security Group
# -----------------------------------------------------------------------------

resource "aws_security_group" "database" {
  name        = "${local.name_prefix}-database-sg"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from backend"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.backend.id, aws_security_group.celery.id]
  }

  tags = {
    Name = "${local.name_prefix}-database-sg"
  }
}

# -----------------------------------------------------------------------------
# RDS Monitoring Role (Production only)
# -----------------------------------------------------------------------------

resource "aws_iam_role" "rds_monitoring" {
  count = local.is_production ? 1 : 0

  name = "${local.name_prefix}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-rds-monitoring"
  }
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  count = local.is_production ? 1 : 0

  role       = aws_iam_role.rds_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# -----------------------------------------------------------------------------
# Store database credentials in Secrets Manager
# -----------------------------------------------------------------------------

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.app_secrets.id

  secret_string = jsonencode({
    DATABASE_URL         = "postgresql://${aws_db_instance.main.username}:${random_password.db_password.result}@${aws_db_instance.main.endpoint}/${aws_db_instance.main.db_name}"
    REDIS_URL            = "redis://${aws_elasticache_cluster.main.cache_nodes[0].address}:${aws_elasticache_cluster.main.cache_nodes[0].port}/0"
    JWT_SECRET_KEY       = random_password.jwt_secret.result
    AUTH0_DOMAIN         = var.auth0_domain
    AUTH0_CLIENT_ID      = var.auth0_client_id
    AUTH0_CLIENT_SECRET  = var.auth0_client_secret
    TOKEN_ENCRYPTION_KEY = random_password.token_encryption_key.result
    MICROSOFT_CLIENT_ID  = var.microsoft_client_id
    MICROSOFT_CLIENT_SECRET = var.microsoft_client_secret
    GOOGLE_CLIENT_ID     = var.google_client_id
    GOOGLE_CLIENT_SECRET = var.google_client_secret
  })

  depends_on = [aws_db_instance.main, aws_elasticache_cluster.main]
}
