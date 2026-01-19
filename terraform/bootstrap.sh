#!/bin/bash
# Flowex Infrastructure Bootstrap Script
# This script sets up the Terraform backend and deploys to staging or production

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="eu-west-1"
STATE_BUCKET="flowex-terraform-state-eu"
LOCK_TABLE="flowex-terraform-locks"

# Functions
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed. Please install it first:"
        echo "  - macOS: brew install terraform"
        echo "  - Linux: https://developer.hashicorp.com/terraform/downloads"
        echo "  - Windows: choco install terraform"
        exit 1
    fi

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first:"
        echo "  - https://aws.amazon.com/cli/"
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi

    log_info "Prerequisites check passed!"
    aws sts get-caller-identity --query 'Account' --output text
}

create_state_backend() {
    log_info "Setting up Terraform state backend..."

    # Check if bucket exists
    if aws s3api head-bucket --bucket "$STATE_BUCKET" 2>/dev/null; then
        log_info "State bucket already exists: $STATE_BUCKET"
    else
        log_info "Creating S3 bucket for Terraform state..."
        aws s3 mb "s3://$STATE_BUCKET" --region "$AWS_REGION"

        log_info "Enabling versioning..."
        aws s3api put-bucket-versioning \
            --bucket "$STATE_BUCKET" \
            --versioning-configuration Status=Enabled

        log_info "Enabling encryption..."
        aws s3api put-bucket-encryption \
            --bucket "$STATE_BUCKET" \
            --server-side-encryption-configuration \
            '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

        log_info "Blocking public access..."
        aws s3api put-public-access-block \
            --bucket "$STATE_BUCKET" \
            --public-access-block-configuration \
            "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
    fi

    # Check if DynamoDB table exists
    if aws dynamodb describe-table --table-name "$LOCK_TABLE" --region "$AWS_REGION" &>/dev/null; then
        log_info "Lock table already exists: $LOCK_TABLE"
    else
        log_info "Creating DynamoDB table for state locking..."
        aws dynamodb create-table \
            --table-name "$LOCK_TABLE" \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --region "$AWS_REGION"

        log_info "Waiting for table to be active..."
        aws dynamodb wait table-exists --table-name "$LOCK_TABLE" --region "$AWS_REGION"
    fi

    log_info "State backend ready!"
}

create_tfvars_template() {
    if [ -f "terraform.tfvars" ]; then
        log_warn "terraform.tfvars already exists, skipping..."
        return
    fi

    log_info "Creating terraform.tfvars template..."
    cat > terraform.tfvars << 'EOF'
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
EOF

    log_warn "Please edit terraform.tfvars with your configuration values!"
}

init_terraform() {
    log_info "Initializing Terraform..."
    terraform init
}

setup_workspace() {
    local env=$1

    # Check if workspace exists
    if terraform workspace list | grep -q "$env"; then
        log_info "Selecting workspace: $env"
        terraform workspace select "$env"
    else
        log_info "Creating workspace: $env"
        terraform workspace new "$env"
    fi
}

run_plan() {
    log_info "Running Terraform plan..."
    terraform plan -var-file=terraform.tfvars -out=tfplan
}

run_apply() {
    log_info "Applying Terraform configuration..."
    terraform apply tfplan
    rm -f tfplan
}

print_outputs() {
    log_info "Infrastructure outputs:"
    echo ""
    terraform output
}

show_usage() {
    echo "Usage: $0 [command] [environment]"
    echo ""
    echo "Commands:"
    echo "  init       - Set up state backend and initialize Terraform"
    echo "  plan       - Run Terraform plan"
    echo "  apply      - Apply Terraform configuration"
    echo "  destroy    - Destroy infrastructure (with confirmation)"
    echo "  outputs    - Show infrastructure outputs"
    echo "  full       - Run full deployment (init + plan + apply)"
    echo ""
    echo "Environment:"
    echo "  staging    - Deploy to staging (default)"
    echo "  production - Deploy to production"
    echo ""
    echo "Examples:"
    echo "  $0 init staging      - Initialize for staging"
    echo "  $0 full staging      - Full deployment to staging"
    echo "  $0 plan production   - Plan production deployment"
}

# Main script
COMMAND=${1:-"help"}
ENVIRONMENT=${2:-"staging"}

# Validate environment
if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    log_error "Invalid environment: $ENVIRONMENT. Must be 'staging' or 'production'."
    exit 1
fi

case $COMMAND in
    init)
        check_prerequisites
        create_state_backend
        create_tfvars_template
        init_terraform
        setup_workspace "$ENVIRONMENT"
        log_info "Initialization complete! Edit terraform.tfvars, then run: $0 plan $ENVIRONMENT"
        ;;
    plan)
        check_prerequisites
        setup_workspace "$ENVIRONMENT"
        run_plan
        log_info "Plan complete! Review above, then run: $0 apply $ENVIRONMENT"
        ;;
    apply)
        check_prerequisites
        setup_workspace "$ENVIRONMENT"
        if [ ! -f "tfplan" ]; then
            log_warn "No plan file found. Running plan first..."
            run_plan
        fi
        read -p "Apply this plan to $ENVIRONMENT? (yes/no): " confirm
        if [ "$confirm" == "yes" ]; then
            run_apply
            print_outputs
        else
            log_info "Apply cancelled."
        fi
        ;;
    destroy)
        check_prerequisites
        setup_workspace "$ENVIRONMENT"
        log_warn "This will DESTROY all infrastructure in $ENVIRONMENT!"
        read -p "Type '$ENVIRONMENT' to confirm: " confirm
        if [ "$confirm" == "$ENVIRONMENT" ]; then
            terraform destroy -var-file=terraform.tfvars
        else
            log_info "Destroy cancelled."
        fi
        ;;
    outputs)
        setup_workspace "$ENVIRONMENT"
        print_outputs
        ;;
    full)
        check_prerequisites
        create_state_backend
        create_tfvars_template
        init_terraform
        setup_workspace "$ENVIRONMENT"

        # Check if tfvars has been configured
        if grep -q 'auth0_domain.*= ""' terraform.tfvars; then
            log_error "Please configure terraform.tfvars before deploying!"
            log_info "Edit terraform.tfvars with your Auth0 credentials, then run: $0 plan $ENVIRONMENT"
            exit 1
        fi

        run_plan
        read -p "Apply this plan to $ENVIRONMENT? (yes/no): " confirm
        if [ "$confirm" == "yes" ]; then
            run_apply
            print_outputs
            log_info "Deployment complete!"
        else
            log_info "Apply cancelled. Run '$0 apply $ENVIRONMENT' when ready."
        fi
        ;;
    help|--help|-h|*)
        show_usage
        ;;
esac
