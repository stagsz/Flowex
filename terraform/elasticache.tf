# Flowex Infrastructure - ElastiCache Configuration
# Redis cluster for caching and Celery broker

# -----------------------------------------------------------------------------
# ElastiCache Subnet Group
# -----------------------------------------------------------------------------

resource "aws_elasticache_subnet_group" "main" {
  name        = "${local.name_prefix}-redis-subnet-group"
  description = "Redis subnet group for ${local.name_prefix}"
  subnet_ids  = aws_subnet.private[*].id

  tags = {
    Name = "${local.name_prefix}-redis-subnet-group"
  }
}

# -----------------------------------------------------------------------------
# ElastiCache Parameter Group
# -----------------------------------------------------------------------------

resource "aws_elasticache_parameter_group" "main" {
  name        = "${local.name_prefix}-redis-params"
  family      = "redis7"
  description = "Redis parameters for ${local.name_prefix}"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  tags = {
    Name = "${local.name_prefix}-redis-params"
  }
}

# -----------------------------------------------------------------------------
# ElastiCache Cluster
# -----------------------------------------------------------------------------

resource "aws_elasticache_cluster" "main" {
  cluster_id           = "${local.name_prefix}-redis"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = local.is_production ? local.env_config.redis_node_type : var.redis_node_type
  num_cache_nodes      = local.is_production ? local.env_config.redis_num_cache_nodes : var.redis_num_cache_nodes
  port                 = 6379
  parameter_group_name = aws_elasticache_parameter_group.main.name
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]

  # Maintenance
  maintenance_window       = "sun:05:00-sun:06:00"
  snapshot_retention_limit = local.is_production ? 7 : 0
  snapshot_window          = local.is_production ? "04:00-05:00" : null

  # Notifications
  notification_topic_arn = local.is_production ? aws_sns_topic.alerts[0].arn : null

  # Upgrades
  auto_minor_version_upgrade = true
  apply_immediately          = !local.is_production

  tags = {
    Name = "${local.name_prefix}-redis"
  }
}

# -----------------------------------------------------------------------------
# Redis Security Group
# -----------------------------------------------------------------------------

resource "aws_security_group" "redis" {
  name        = "${local.name_prefix}-redis-sg"
  description = "Security group for ElastiCache Redis"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Redis from backend and celery"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.backend.id, aws_security_group.celery.id]
  }

  tags = {
    Name = "${local.name_prefix}-redis-sg"
  }
}

# -----------------------------------------------------------------------------
# SNS Topic for Alerts (Production only)
# -----------------------------------------------------------------------------

resource "aws_sns_topic" "alerts" {
  count = local.is_production ? 1 : 0

  name = "${local.name_prefix}-alerts"

  tags = {
    Name = "${local.name_prefix}-alerts"
  }
}
