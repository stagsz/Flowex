# Flowex Infrastructure - Variables
# Input variables for Terraform configuration

# -----------------------------------------------------------------------------
# General Configuration
# -----------------------------------------------------------------------------

variable "environment" {
  description = "Environment name (staging or production)"
  type        = string

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be either 'staging' or 'production'."
  }
}

variable "aws_region" {
  description = "AWS region for resources (GDPR compliant)"
  type        = string
  default     = "eu-west-1"
}

variable "domain_name" {
  description = "Base domain name for the application"
  type        = string
  default     = "flowex.io"
}

# -----------------------------------------------------------------------------
# Networking
# -----------------------------------------------------------------------------

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones to use"
  type        = list(string)
  default     = ["eu-west-1a", "eu-west-1b", "eu-west-1c"]
}

# -----------------------------------------------------------------------------
# ECS Configuration
# -----------------------------------------------------------------------------

variable "backend_cpu" {
  description = "CPU units for backend task (256, 512, 1024, 2048, 4096)"
  type        = number
  default     = 512
}

variable "backend_memory" {
  description = "Memory for backend task in MB"
  type        = number
  default     = 1024
}

variable "backend_desired_count" {
  description = "Desired number of backend tasks"
  type        = number
  default     = 1
}

variable "backend_min_count" {
  description = "Minimum number of backend tasks for auto-scaling"
  type        = number
  default     = 1
}

variable "backend_max_count" {
  description = "Maximum number of backend tasks for auto-scaling"
  type        = number
  default     = 4
}

variable "celery_cpu" {
  description = "CPU units for Celery worker task"
  type        = number
  default     = 512
}

variable "celery_memory" {
  description = "Memory for Celery worker task in MB"
  type        = number
  default     = 2048
}

variable "celery_desired_count" {
  description = "Desired number of Celery worker tasks"
  type        = number
  default     = 1
}

# -----------------------------------------------------------------------------
# RDS Configuration
# -----------------------------------------------------------------------------

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "Allocated storage for RDS in GB"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "Maximum allocated storage for RDS auto-scaling in GB"
  type        = number
  default     = 100
}

variable "db_multi_az" {
  description = "Enable Multi-AZ deployment for RDS"
  type        = bool
  default     = false
}

variable "db_deletion_protection" {
  description = "Enable deletion protection for RDS"
  type        = bool
  default     = false
}

variable "db_backup_retention_days" {
  description = "Number of days to retain automated backups"
  type        = number
  default     = 7
}

# -----------------------------------------------------------------------------
# ElastiCache Configuration
# -----------------------------------------------------------------------------

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_cache_nodes" {
  description = "Number of cache nodes in the cluster"
  type        = number
  default     = 1
}

# -----------------------------------------------------------------------------
# Auth0 Configuration
# -----------------------------------------------------------------------------

variable "auth0_domain" {
  description = "Auth0 domain"
  type        = string
  sensitive   = true
}

variable "auth0_client_id" {
  description = "Auth0 client ID"
  type        = string
  sensitive   = true
}

variable "auth0_client_secret" {
  description = "Auth0 client secret"
  type        = string
  sensitive   = true
}

# -----------------------------------------------------------------------------
# OAuth Configuration (Optional)
# -----------------------------------------------------------------------------

variable "microsoft_client_id" {
  description = "Microsoft OAuth client ID"
  type        = string
  default     = ""
  sensitive   = true
}

variable "microsoft_client_secret" {
  description = "Microsoft OAuth client secret"
  type        = string
  default     = ""
  sensitive   = true
}

variable "google_client_id" {
  description = "Google OAuth client ID"
  type        = string
  default     = ""
  sensitive   = true
}

variable "google_client_secret" {
  description = "Google OAuth client secret"
  type        = string
  default     = ""
  sensitive   = true
}

# -----------------------------------------------------------------------------
# Environment-specific defaults
# -----------------------------------------------------------------------------

locals {
  # Staging defaults
  staging_config = {
    backend_desired_count = 1
    backend_min_count     = 1
    backend_max_count     = 2
    db_instance_class     = "db.t3.micro"
    db_multi_az           = false
    db_deletion_protection = false
    redis_node_type       = "cache.t3.micro"
    redis_num_cache_nodes = 1
  }

  # Production defaults
  production_config = {
    backend_desired_count = 2
    backend_min_count     = 2
    backend_max_count     = 4
    db_instance_class     = "db.r6g.large"
    db_multi_az           = true
    db_deletion_protection = true
    redis_node_type       = "cache.r6g.large"
    redis_num_cache_nodes = 2
  }

  # Select config based on environment
  env_config = var.environment == "production" ? local.production_config : local.staging_config
}
