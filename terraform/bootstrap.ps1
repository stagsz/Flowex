# Flowex Infrastructure Bootstrap Script (PowerShell)
# This script sets up the Terraform backend and deploys to staging or production

param(
    [Parameter(Position=0)]
    [ValidateSet("init", "plan", "apply", "destroy", "outputs", "full", "help")]
    [string]$Command = "help",

    [Parameter(Position=1)]
    [ValidateSet("staging", "production")]
    [string]$Environment = "staging"
)

$ErrorActionPreference = "Stop"

# Configuration
$AWS_REGION = "eu-west-1"
$STATE_BUCKET = "flowex-terraform-state-eu"
$LOCK_TABLE = "flowex-terraform-locks"

# Functions
function Write-Info { param($Message) Write-Host "[INFO] $Message" -ForegroundColor Green }
function Write-Warn { param($Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Err { param($Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }

function Test-Prerequisites {
    Write-Info "Checking prerequisites..."

    # Check Terraform
    if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) {
        Write-Err "Terraform is not installed. Please install it first:"
        Write-Host "  - Windows: choco install terraform"
        Write-Host "  - Or download from: https://developer.hashicorp.com/terraform/downloads"
        exit 1
    }

    # Check AWS CLI
    if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
        Write-Err "AWS CLI is not installed. Please install it first:"
        Write-Host "  - Windows: choco install awscli"
        Write-Host "  - Or download from: https://aws.amazon.com/cli/"
        exit 1
    }

    # Check AWS credentials
    try {
        $identity = aws sts get-caller-identity 2>&1
        if ($LASTEXITCODE -ne 0) { throw "AWS credentials not configured" }
    }
    catch {
        Write-Err "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    }

    Write-Info "Prerequisites check passed!"
    $account = aws sts get-caller-identity --query 'Account' --output text
    Write-Host "  AWS Account: $account"
}

function New-StateBackend {
    Write-Info "Setting up Terraform state backend..."

    # Check if bucket exists
    $bucketExists = aws s3api head-bucket --bucket $STATE_BUCKET 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Info "State bucket already exists: $STATE_BUCKET"
    }
    else {
        Write-Info "Creating S3 bucket for Terraform state..."
        aws s3 mb "s3://$STATE_BUCKET" --region $AWS_REGION

        Write-Info "Enabling versioning..."
        aws s3api put-bucket-versioning `
            --bucket $STATE_BUCKET `
            --versioning-configuration Status=Enabled

        Write-Info "Enabling encryption..."
        aws s3api put-bucket-encryption `
            --bucket $STATE_BUCKET `
            --server-side-encryption-configuration `
            '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

        Write-Info "Blocking public access..."
        aws s3api put-public-access-block `
            --bucket $STATE_BUCKET `
            --public-access-block-configuration `
            "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
    }

    # Check if DynamoDB table exists
    $tableExists = aws dynamodb describe-table --table-name $LOCK_TABLE --region $AWS_REGION 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Info "Lock table already exists: $LOCK_TABLE"
    }
    else {
        Write-Info "Creating DynamoDB table for state locking..."
        aws dynamodb create-table `
            --table-name $LOCK_TABLE `
            --attribute-definitions AttributeName=LockID,AttributeType=S `
            --key-schema AttributeName=LockID,KeyType=HASH `
            --billing-mode PAY_PER_REQUEST `
            --region $AWS_REGION

        Write-Info "Waiting for table to be active..."
        aws dynamodb wait table-exists --table-name $LOCK_TABLE --region $AWS_REGION
    }

    Write-Info "State backend ready!"
}

function New-TfvarsTemplate {
    if (Test-Path "terraform.tfvars") {
        Write-Warn "terraform.tfvars already exists, skipping..."
        return
    }

    Write-Info "Creating terraform.tfvars template..."
    @"
# Flowex Terraform Variables
# Fill in your values below

environment = "staging"  # Change to "production" for prod deployment
domain_name = "flowex.io"

# Auth0 Configuration (required)
auth0_domain        = ""  # e.g., "your-tenant.auth0.com"
auth0_client_id     = ""  # Your Auth0 application client ID
auth0_client_secret = ""  # Your Auth0 application client secret

# OAuth Providers (optional - leave empty if not using)
microsoft_client_id     = ""
microsoft_client_secret = ""
google_client_id        = ""
google_client_secret    = ""

# Override defaults if needed (optional)
# backend_cpu           = 512
# backend_memory        = 1024
# backend_desired_count = 1
# db_instance_class     = "db.t3.micro"
# redis_node_type       = "cache.t3.micro"
"@ | Out-File -FilePath "terraform.tfvars" -Encoding UTF8

    Write-Warn "Please edit terraform.tfvars with your configuration values!"
}

function Initialize-Terraform {
    Write-Info "Initializing Terraform..."
    terraform init
    if ($LASTEXITCODE -ne 0) { throw "Terraform init failed" }
}

function Set-Workspace {
    param($Env)

    $workspaces = terraform workspace list 2>&1
    if ($workspaces -match $Env) {
        Write-Info "Selecting workspace: $Env"
        terraform workspace select $Env
    }
    else {
        Write-Info "Creating workspace: $Env"
        terraform workspace new $Env
    }
    if ($LASTEXITCODE -ne 0) { throw "Workspace setup failed" }
}

function Invoke-Plan {
    Write-Info "Running Terraform plan..."
    terraform plan -var-file=terraform.tfvars -out=tfplan
    if ($LASTEXITCODE -ne 0) { throw "Terraform plan failed" }
}

function Invoke-Apply {
    Write-Info "Applying Terraform configuration..."
    terraform apply tfplan
    if ($LASTEXITCODE -ne 0) { throw "Terraform apply failed" }
    Remove-Item -Path "tfplan" -ErrorAction SilentlyContinue
}

function Show-Outputs {
    Write-Info "Infrastructure outputs:"
    Write-Host ""
    terraform output
}

function Show-Usage {
    Write-Host @"
Usage: .\bootstrap.ps1 [command] [environment]

Commands:
  init       - Set up state backend and initialize Terraform
  plan       - Run Terraform plan
  apply      - Apply Terraform configuration
  destroy    - Destroy infrastructure (with confirmation)
  outputs    - Show infrastructure outputs
  full       - Run full deployment (init + plan + apply)

Environment:
  staging    - Deploy to staging (default)
  production - Deploy to production

Examples:
  .\bootstrap.ps1 init staging      - Initialize for staging
  .\bootstrap.ps1 full staging      - Full deployment to staging
  .\bootstrap.ps1 plan production   - Plan production deployment
"@
}

# Main script
switch ($Command) {
    "init" {
        Test-Prerequisites
        New-StateBackend
        New-TfvarsTemplate
        Initialize-Terraform
        Set-Workspace -Env $Environment
        Write-Info "Initialization complete! Edit terraform.tfvars, then run: .\bootstrap.ps1 plan $Environment"
    }
    "plan" {
        Test-Prerequisites
        Set-Workspace -Env $Environment
        Invoke-Plan
        Write-Info "Plan complete! Review above, then run: .\bootstrap.ps1 apply $Environment"
    }
    "apply" {
        Test-Prerequisites
        Set-Workspace -Env $Environment
        if (-not (Test-Path "tfplan")) {
            Write-Warn "No plan file found. Running plan first..."
            Invoke-Plan
        }
        $confirm = Read-Host "Apply this plan to $Environment? (yes/no)"
        if ($confirm -eq "yes") {
            Invoke-Apply
            Show-Outputs
        }
        else {
            Write-Info "Apply cancelled."
        }
    }
    "destroy" {
        Test-Prerequisites
        Set-Workspace -Env $Environment
        Write-Warn "This will DESTROY all infrastructure in $Environment!"
        $confirm = Read-Host "Type '$Environment' to confirm"
        if ($confirm -eq $Environment) {
            terraform destroy -var-file=terraform.tfvars
        }
        else {
            Write-Info "Destroy cancelled."
        }
    }
    "outputs" {
        Set-Workspace -Env $Environment
        Show-Outputs
    }
    "full" {
        Test-Prerequisites
        New-StateBackend
        New-TfvarsTemplate
        Initialize-Terraform
        Set-Workspace -Env $Environment

        # Check if tfvars has been configured
        $tfvars = Get-Content "terraform.tfvars" -Raw
        if ($tfvars -match 'auth0_domain\s*=\s*""') {
            Write-Err "Please configure terraform.tfvars before deploying!"
            Write-Info "Edit terraform.tfvars with your Auth0 credentials, then run: .\bootstrap.ps1 plan $Environment"
            exit 1
        }

        Invoke-Plan
        $confirm = Read-Host "Apply this plan to $Environment? (yes/no)"
        if ($confirm -eq "yes") {
            Invoke-Apply
            Show-Outputs
            Write-Info "Deployment complete!"
        }
        else {
            Write-Info "Apply cancelled. Run '.\bootstrap.ps1 apply $Environment' when ready."
        }
    }
    default {
        Show-Usage
    }
}
