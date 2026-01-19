# Flowex Deployment Guide

This document covers deploying Flowex to AWS infrastructure using Terraform and GitHub Actions.

## Architecture Overview

```
                    ┌─────────────────┐
                    │    Route 53     │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
    ┌─────────▼─────────┐       ┌──────────▼──────────┐
    │    CloudFront     │       │        ALB          │
    │   (Frontend CDN)  │       │   (API Gateway)     │
    └─────────┬─────────┘       └──────────┬──────────┘
              │                             │
    ┌─────────▼─────────┐       ┌──────────▼──────────┐
    │        S3         │       │    ECS Fargate      │
    │  (Static Assets)  │       │  ┌───────┬────────┐ │
    └───────────────────┘       │  │Backend│ Celery │ │
                                │  └───┬───┴────┬───┘ │
                                └──────┼────────┼─────┘
                                       │        │
                          ┌────────────┼────────┼────────────┐
                          │            │        │            │
                ┌─────────▼────┐ ┌─────▼────┐ ┌─▼────────────▼───┐
                │     RDS      │ │  Redis   │ │       S3         │
                │ (PostgreSQL) │ │(ElastiC.)│ │    (Uploads)     │
                └──────────────┘ └──────────┘ └──────────────────┘
```

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** v2 installed and configured
3. **Terraform** v1.5+ installed
4. **Docker** installed for building images
5. **Domain** registered in Route 53

### Required AWS Permissions

The deploying user/role needs permissions for:
- ECR, ECS, EC2, VPC
- RDS, ElastiCache
- S3, CloudFront
- ACM, Route 53
- IAM, KMS, Secrets Manager
- CloudWatch

## Initial Setup

### 1. Bootstrap Terraform State

Create the S3 bucket and DynamoDB table for Terraform state:

```bash
# Create S3 bucket for state
aws s3 mb s3://flowex-terraform-state-eu --region eu-west-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket flowex-terraform-state-eu \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket flowex-terraform-state-eu \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name flowex-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region eu-west-1
```

### 2. Configure Route 53

Ensure your domain is hosted in Route 53:

```bash
# Create hosted zone (if not exists)
aws route53 create-hosted-zone \
  --name flowex.io \
  --caller-reference $(date +%s)

# Update your domain registrar with the NS records
```

### 3. Set Up GitHub OIDC

GitHub Actions uses OIDC for AWS authentication. The Terraform configuration creates the OIDC provider automatically.

### 4. Create Terraform Variables File

Create `terraform/terraform.tfvars`:

```hcl
# terraform/terraform.tfvars

environment = "staging"  # or "production"
domain_name = "flowex.io"

# Auth0 Configuration
auth0_domain        = "your-tenant.auth0.com"
auth0_client_id     = "your-client-id"
auth0_client_secret = "your-client-secret"

# Optional: OAuth Providers
microsoft_client_id     = ""
microsoft_client_secret = ""
google_client_id        = ""
google_client_secret    = ""
```

**Note:** Never commit `terraform.tfvars` with secrets. Use environment variables or a secrets manager for CI/CD.

## Deployment

### Manual Deployment (First Time)

```bash
cd terraform

# Initialize Terraform
terraform init

# Create staging workspace
terraform workspace new staging

# Plan the deployment
terraform plan -var-file=terraform.tfvars

# Apply the infrastructure
terraform apply -var-file=terraform.tfvars
```

### Build and Push Docker Images

```bash
# Login to ECR
aws ecr get-login-password --region eu-west-1 | \
  docker login --username AWS --password-stdin \
  <account-id>.dkr.ecr.eu-west-1.amazonaws.com

# Build and push backend
cd backend
docker build -t flowex-backend .
docker tag flowex-backend:latest \
  <account-id>.dkr.ecr.eu-west-1.amazonaws.com/flowex-staging/backend:latest
docker push <account-id>.dkr.ecr.eu-west-1.amazonaws.com/flowex-staging/backend:latest

# Build and push frontend (if using ECS for frontend)
cd ../frontend
docker build -t flowex-frontend \
  --build-arg VITE_API_URL=https://api.staging.flowex.io \
  --build-arg VITE_AUTH0_DOMAIN=your-tenant.auth0.com \
  --build-arg VITE_AUTH0_CLIENT_ID=your-client-id .
```

### Run Database Migrations

```bash
# Run migration task
aws ecs run-task \
  --cluster flowex-staging-cluster \
  --task-definition flowex-staging-migration \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[subnet-xxx,subnet-yyy],
    securityGroups=[sg-xxx],
    assignPublicIp=DISABLED
  }"
```

### CI/CD Deployment

After initial setup, deployments happen automatically via GitHub Actions:

1. **Push to main** → Deploys to staging
2. **Manual workflow dispatch** → Deploy to staging or production

Configure GitHub environment secrets:
- `AWS_ACCOUNT_ID`: Your AWS account ID

Configure GitHub environment variables:
- `AUTH0_DOMAIN`: Auth0 domain
- `AUTH0_CLIENT_ID`: Auth0 client ID
- `FRONTEND_BUCKET`: S3 bucket name for frontend
- `CLOUDFRONT_DISTRIBUTION_ID`: CloudFront distribution ID
- `PRIVATE_SUBNETS`: Comma-separated subnet IDs
- `BACKEND_SECURITY_GROUP`: Backend security group ID

## Environment Configuration

### Staging vs Production

| Configuration | Staging | Production |
|--------------|---------|------------|
| Domain | staging.flowex.io | flowex.io |
| API | api.staging.flowex.io | api.flowex.io |
| ECS Tasks | 1 | 2-4 (auto-scale) |
| RDS Instance | db.t3.micro | db.r6g.large |
| RDS Multi-AZ | No | Yes |
| Redis | cache.t3.micro | cache.r6g.large |
| Backups | 7 days | 30 days |
| Deletion Protection | No | Yes |

### Environment Variables

The following environment variables are injected into ECS tasks:

| Variable | Description | Source |
|----------|-------------|--------|
| `ENVIRONMENT` | Environment name | Task definition |
| `STORAGE_PROVIDER` | "aws" | Task definition |
| `AWS_REGION` | "eu-west-1" | Task definition |
| `AWS_S3_BUCKET` | Uploads bucket name | Task definition |
| `DATABASE_URL` | PostgreSQL connection string | Secrets Manager |
| `REDIS_URL` | Redis connection string | Secrets Manager |
| `JWT_SECRET_KEY` | JWT signing key | Secrets Manager |
| `AUTH0_DOMAIN` | Auth0 tenant domain | Secrets Manager |
| `AUTH0_CLIENT_ID` | Auth0 client ID | Secrets Manager |
| `AUTH0_CLIENT_SECRET` | Auth0 client secret | Secrets Manager |
| `TOKEN_ENCRYPTION_KEY` | Fernet encryption key | Secrets Manager |

## Monitoring

### CloudWatch Dashboard

Access the pre-configured dashboard:

```bash
# Open dashboard URL
aws cloudwatch get-dashboard --dashboard-name flowex-staging-dashboard
```

Dashboard includes:
- ECS CPU and memory utilization
- ALB request count and response time
- RDS CPU and connections
- Redis CPU and memory
- Error logs

### Alarms (Production)

Production environment includes CloudWatch alarms for:
- High CPU (> 80%)
- High memory (> 85%)
- Slow response time (> 2s)
- 5xx errors (> 10/5min)
- Low disk space (< 5GB)

### Logs

View application logs:

```bash
# Backend logs
aws logs tail /ecs/flowex-staging/backend --follow

# Celery worker logs
aws logs tail /ecs/flowex-staging/celery --follow
```

## Rollback Procedures

### ECS Service Rollback

```bash
# List recent task definitions
aws ecs list-task-definitions \
  --family-prefix flowex-staging-backend \
  --sort DESC

# Update service to previous task definition
aws ecs update-service \
  --cluster flowex-staging-cluster \
  --service flowex-staging-backend \
  --task-definition flowex-staging-backend:123
```

### Database Rollback

```bash
# Run downgrade migration
aws ecs run-task \
  --cluster flowex-staging-cluster \
  --task-definition flowex-staging-backend \
  --launch-type FARGATE \
  --overrides '{
    "containerOverrides": [{
      "name": "backend",
      "command": ["alembic", "downgrade", "-1"]
    }]
  }' \
  --network-configuration "awsvpcConfiguration={...}"
```

### Infrastructure Rollback

```bash
cd terraform

# Review previous state
terraform show

# Apply previous configuration (from git)
git checkout HEAD~1 -- *.tf
terraform plan
terraform apply
```

## Troubleshooting

### Common Issues

**1. ECS tasks failing to start**

```bash
# Check task stopped reason
aws ecs describe-tasks \
  --cluster flowex-staging-cluster \
  --tasks <task-arn>

# Common causes:
# - Image pull failure: Check ECR permissions
# - Secrets access: Check Secrets Manager permissions
# - Health check failure: Check container logs
```

**2. Database connection issues**

```bash
# Test connectivity from bastion/VPN
psql "postgresql://user:pass@endpoint:5432/flowex"

# Check security groups allow traffic from ECS
aws ec2 describe-security-groups --group-ids sg-xxx
```

**3. ALB health checks failing**

```bash
# Check target health
aws elbv2 describe-target-health \
  --target-group-arn <tg-arn>

# Verify /health endpoint responds
curl -v http://localhost:8000/health
```

**4. CloudFront 403 errors**

```bash
# Check S3 bucket policy
aws s3api get-bucket-policy --bucket flowex-staging-frontend-xxx

# Invalidate cache after deployment
aws cloudfront create-invalidation \
  --distribution-id <dist-id> \
  --paths "/*"
```

### Getting Help

1. Check CloudWatch logs for errors
2. Review ECS task stopped reasons
3. Verify security group rules
4. Check IAM permissions
5. Review Terraform state for configuration drift

## Cost Optimization

### Staging Environment

- Use `FARGATE_SPOT` for non-critical workloads
- Scale down to 0 tasks during off-hours
- Use smaller RDS/Redis instances

### Production Environment

- Reserved instances for RDS (up to 60% savings)
- Savings Plans for Fargate
- S3 Intelligent Tiering for uploads
- CloudFront price class optimization

## Security Checklist

- [ ] All secrets stored in Secrets Manager
- [ ] KMS encryption enabled for RDS, S3, ECR
- [ ] VPC endpoints for AWS services
- [ ] Security groups follow least privilege
- [ ] HTTPS enforced everywhere
- [ ] WAF enabled for CloudFront (optional)
- [ ] GuardDuty enabled
- [ ] CloudTrail logging enabled
