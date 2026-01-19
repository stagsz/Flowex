# Flowex Staging Deployment Checklist

This document provides a step-by-step checklist for deploying Flowex to the staging environment.

**Prerequisites:** Complete all items in order. Each section must be done before the next.

---

## Phase 1: External Service Setup

### 1.1 AWS Account Setup

- [ ] **AWS Account created** with billing enabled
- [ ] **IAM user/role** with administrator access for initial setup
- [ ] **AWS CLI installed** and configured locally:
  ```bash
  aws configure
  # Enter: Access Key ID, Secret Access Key, Region: eu-west-1
  ```
- [ ] **Verify credentials:**
  ```bash
  aws sts get-caller-identity
  ```

### 1.2 Auth0 Setup

- [ ] **Auth0 tenant created** at [auth0.com](https://auth0.com)
- [ ] **Application created** (Regular Web Application)
  - Name: `Flowex Staging`
  - Allowed Callback URLs: `https://api.staging.flowex.io/auth/callback`
  - Allowed Logout URLs: `https://staging.flowex.io`
  - Allowed Web Origins: `https://staging.flowex.io`
- [ ] **Record credentials:**
  - Auth0 Domain: `____________________.auth0.com`
  - Client ID: `____________________`
  - Client Secret: `____________________`

### 1.3 Domain Setup

- [ ] **Domain registered** (flowex.io or your domain)
- [ ] **Route 53 hosted zone created:**
  ```bash
  aws route53 create-hosted-zone --name flowex.io --caller-reference $(date +%s)
  ```
- [ ] **NS records updated** at domain registrar with Route 53 nameservers

---

## Phase 2: Terraform Infrastructure

### 2.1 Initialize Terraform Backend

Run from the `terraform/` directory:

**Windows (PowerShell):**
```powershell
.\bootstrap.ps1 init staging
```

**Linux/macOS:**
```bash
./bootstrap.sh init staging
```

This creates:
- [ ] S3 bucket for Terraform state (`flowex-terraform-state-eu`)
- [ ] DynamoDB table for state locking (`flowex-terraform-locks`)
- [ ] `terraform.tfvars` template file

### 2.2 Configure Terraform Variables

Edit `terraform/terraform.tfvars`:

```hcl
environment = "staging"
domain_name = "flowex.io"  # Your domain

# Auth0 Configuration (required)
auth0_domain        = "your-tenant.auth0.com"
auth0_client_id     = "your-client-id"
auth0_client_secret = "your-client-secret"

# OAuth Providers (optional)
microsoft_client_id     = ""
microsoft_client_secret = ""
google_client_id        = ""
google_client_secret    = ""
```

### 2.3 Deploy Infrastructure

**Windows (PowerShell):**
```powershell
.\bootstrap.ps1 full staging
```

**Linux/macOS:**
```bash
./bootstrap.sh full staging
```

This creates:
- [ ] VPC with public/private subnets
- [ ] ECS Fargate cluster
- [ ] RDS PostgreSQL database
- [ ] ElastiCache Redis
- [ ] S3 buckets (frontend, uploads)
- [ ] CloudFront distribution
- [ ] Application Load Balancer
- [ ] ECR repositories
- [ ] Secrets Manager secrets
- [ ] IAM roles and policies
- [ ] ACM SSL certificates

### 2.4 Record Terraform Outputs

After `terraform apply`, save these values:

```bash
terraform output
```

Record:
- [ ] `frontend_bucket_name`: `____________________`
- [ ] `cloudfront_distribution_id`: `____________________`
- [ ] `private_subnet_ids`: `____________________`
- [ ] `backend_security_group_id`: `____________________`
- [ ] `ecr_backend_repository_url`: `____________________`
- [ ] `api_url`: `____________________`
- [ ] `frontend_url`: `____________________`

---

## Phase 3: GitHub Configuration

### 3.1 Create GitHub Environment

1. Go to: `Repository → Settings → Environments`
2. Create environment: `staging`
3. Optionally add deployment protection rules

### 3.2 Configure GitHub Environment Variables

Go to: `Repository → Settings → Environments → staging → Environment variables`

Add variables:
| Variable Name | Value | Source |
|--------------|-------|--------|
| `AWS_ACCOUNT_ID` | Your 12-digit AWS account ID | AWS Console |
| `AUTH0_DOMAIN` | `your-tenant.auth0.com` | Auth0 |
| `AUTH0_CLIENT_ID` | Auth0 client ID | Auth0 |
| `FRONTEND_BUCKET` | S3 bucket name | Terraform output |
| `CLOUDFRONT_DISTRIBUTION_ID` | CloudFront ID | Terraform output |
| `PRIVATE_SUBNETS` | Comma-separated subnet IDs | Terraform output |
| `BACKEND_SECURITY_GROUP` | Security group ID | Terraform output |

---

## Phase 4: Initial Deployment

### 4.1 Build and Push Docker Images (First Time Only)

Before the first CI/CD run, manually build and push images:

```bash
# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Login to ECR
aws ecr get-login-password --region eu-west-1 | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.eu-west-1.amazonaws.com

# Build and push backend
cd backend
docker build -t flowex-backend .
docker tag flowex-backend:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.eu-west-1.amazonaws.com/flowex-staging/backend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.eu-west-1.amazonaws.com/flowex-staging/backend:latest

# Build and push frontend (for initial deployment)
cd ../frontend
npm ci --legacy-peer-deps
npm run build
```

### 4.2 Trigger CI/CD Deployment

Option A: Push to main branch
```bash
git push origin main
```

Option B: Manual workflow dispatch
1. Go to: `Repository → Actions → Deploy`
2. Click "Run workflow"
3. Select environment: `staging`
4. Click "Run workflow"

### 4.3 Verify Deployment

- [ ] **Check GitHub Actions** - All jobs should pass
- [ ] **Check ECS services** - Tasks running:
  ```bash
  aws ecs list-services --cluster flowex-staging-cluster
  aws ecs describe-services --cluster flowex-staging-cluster \
    --services flowex-staging-backend flowex-staging-celery-worker
  ```
- [ ] **Check API health:**
  ```bash
  curl https://api.staging.flowex.io/health
  ```
- [ ] **Check frontend:**
  Open https://staging.flowex.io in browser

---

## Phase 5: Post-Deployment Verification

### 5.1 Functional Tests

- [ ] **Authentication flow** - Login via Auth0 SSO
- [ ] **File upload** - Upload a test PDF
- [ ] **Processing** - Verify PDF processing starts
- [ ] **Export** - Test DXF and Excel export

### 5.2 Monitoring Setup

- [ ] **CloudWatch Dashboard** - Access via AWS Console
- [ ] **Sentry** - Verify errors are captured (if configured)
- [ ] **Log access:**
  ```bash
  aws logs tail /ecs/flowex-staging/backend --follow
  ```

---

## Troubleshooting

### ECS Tasks Not Starting

```bash
# Check task stopped reason
aws ecs describe-tasks --cluster flowex-staging-cluster --tasks <task-arn>

# Check container logs
aws logs tail /ecs/flowex-staging/backend --since 30m
```

Common causes:
- Image not found in ECR → Push images first
- Secrets not accessible → Check IAM permissions
- Health check failing → Check /health endpoint

### Database Connection Issues

```bash
# Check security groups allow ECS → RDS traffic
aws ec2 describe-security-groups --group-ids <rds-sg-id>

# Check RDS endpoint
aws rds describe-db-instances --db-instance-identifier flowex-staging-db
```

### CloudFront 403 Errors

```bash
# Invalidate cache
aws cloudfront create-invalidation \
  --distribution-id <dist-id> \
  --paths "/*"

# Check S3 bucket has objects
aws s3 ls s3://<frontend-bucket>
```

---

## Cost Estimation (Staging)

| Resource | Monthly Cost (Approx) |
|----------|----------------------|
| ECS Fargate (2 tasks) | $30-50 |
| RDS db.t3.micro | $15-20 |
| ElastiCache cache.t3.micro | $12-15 |
| S3 (10GB) | $0.23 |
| CloudFront | $1-5 |
| Route 53 | $0.50 |
| Secrets Manager | $0.40/secret |
| **Total** | **~$60-100/month** |

To reduce costs:
- Stop ECS tasks during off-hours
- Use FARGATE_SPOT for Celery workers
- Reduce RDS storage to minimum

---

## Next Steps

After staging is verified:
1. Invite beta testers
2. Monitor error rates and performance
3. Collect feedback for improvements
4. Plan production deployment

---

*Last updated: 2026-01-19*
