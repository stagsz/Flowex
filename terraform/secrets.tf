# Flowex Infrastructure - Secrets Manager Configuration
# Application secrets and encryption keys

# -----------------------------------------------------------------------------
# KMS Key for encryption
# -----------------------------------------------------------------------------

resource "aws_kms_key" "main" {
  description             = "KMS key for ${local.name_prefix}"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${local.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow ECS Tasks"
        Effect = "Allow"
        Principal = {
          AWS = [
            aws_iam_role.ecs_execution.arn,
            aws_iam_role.ecs_task.arn
          ]
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-kms"
  }
}

resource "aws_kms_alias" "main" {
  name          = "alias/${local.name_prefix}"
  target_key_id = aws_kms_key.main.key_id
}

# -----------------------------------------------------------------------------
# Application Secrets
# -----------------------------------------------------------------------------

resource "aws_secretsmanager_secret" "app_secrets" {
  name        = "${local.name_prefix}/app-secrets"
  description = "Application secrets for ${local.name_prefix}"
  kms_key_id  = aws_kms_key.main.arn

  # Allow recovery for production, force delete for staging
  recovery_window_in_days = local.is_production ? 7 : 0

  tags = {
    Name = "${local.name_prefix}-app-secrets"
  }
}

# -----------------------------------------------------------------------------
# Random secrets for JWT and encryption
# -----------------------------------------------------------------------------

resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

resource "random_password" "token_encryption_key" {
  length  = 32
  special = false
}

# Note: The actual secret values are set in rds.tf after database is created
# to include the DATABASE_URL with the generated password

# -----------------------------------------------------------------------------
# Secret Rotation (Production only)
# -----------------------------------------------------------------------------

# For production, consider implementing secret rotation using Lambda
# This is a placeholder for future implementation

# resource "aws_secretsmanager_secret_rotation" "db_password" {
#   count = local.is_production ? 1 : 0
#
#   secret_id           = aws_secretsmanager_secret.app_secrets.id
#   rotation_lambda_arn = aws_lambda_function.rotate_secrets[0].arn
#
#   rotation_rules {
#     automatically_after_days = 30
#   }
# }
