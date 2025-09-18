#!/bin/bash
# Orca Core Azure Infrastructure Bootstrap Script
# This script deploys the complete Azure infrastructure for Orca Core

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env.local"
PARAMS_DIR="$SCRIPT_DIR/../params"

# Default values
ENVIRONMENT="dev"
LOCATION="East US"
RESOURCE_GROUP_NAME="orcacore-rg"
DEPLOYMENT_METHOD="bicep"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if Azure CLI is installed
    if ! command_exists az; then
        log_error "Azure CLI is not installed. Please install it first:"
        log_error "  https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi

    # Check if user is logged in to Azure
    if ! az account show >/dev/null 2>&1; then
        log_error "You are not logged in to Azure. Please run: az login"
        exit 1
    fi

    # Check if Bicep is available (if using Bicep)
    if [ "$DEPLOYMENT_METHOD" = "bicep" ]; then
        if ! command_exists az bicep; then
            log_warning "Bicep CLI is not available. Installing..."
            az bicep install
        fi
    fi

    # Check if Terraform is available (if using Terraform)
    if [ "$DEPLOYMENT_METHOD" = "terraform" ]; then
        if ! command_exists terraform; then
            log_error "Terraform is not installed. Please install it first:"
            log_error "  https://www.terraform.io/downloads.html"
            exit 1
        fi
    fi

    log_success "Prerequisites check completed"
}

# Function to load environment variables
load_environment() {
    log_info "Loading environment variables..."

    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file not found: $ENV_FILE"
        log_error "Please run 'make configure-azure-openai' first to create the environment file"
        exit 1
    fi

    # Source the environment file
    set -a
    source "$ENV_FILE"
    set +a

    # Validate required variables
    local required_vars=(
        "AZURE_SUBSCRIPTION_ID"
        "AZURE_TENANT_ID"
        "AZURE_RESOURCE_GROUP"
        "AZURE_OPENAI_ENDPOINT"
        "AZURE_OPENAI_API_KEY"
        "AZURE_OPENAI_DEPLOYMENT"
    )

    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_error "Required environment variable $var is not set"
            log_error "Please run 'make configure-azure-openai' to configure all required variables"
            exit 1
        fi
    done

    # Set variables from environment
    ENVIRONMENT="${ORCA_ENVIRONMENT:-dev}"
    LOCATION="${AZURE_LOCATION:-East US}"
    RESOURCE_GROUP_NAME="$AZURE_RESOURCE_GROUP"

    log_success "Environment variables loaded successfully"
}

# Function to create resource group
create_resource_group() {
    log_info "Creating resource group: $RESOURCE_GROUP_NAME"

    if az group show --name "$RESOURCE_GROUP_NAME" >/dev/null 2>&1; then
        log_warning "Resource group $RESOURCE_GROUP_NAME already exists"
    else
        az group create \
            --name "$RESOURCE_GROUP_NAME" \
            --location "$LOCATION" \
            --tags Project=OrcaCore Environment="$ENVIRONMENT" ManagedBy=Bootstrap
        log_success "Resource group created successfully"
    fi
}

# Function to deploy with Bicep
deploy_bicep() {
    log_info "Deploying infrastructure with Bicep..."

    local bicep_dir="$SCRIPT_DIR/../bicep"
    local params_file="$PARAMS_DIR/$ENVIRONMENT.json"

    # Create parameters file if it doesn't exist
    if [ ! -f "$params_file" ]; then
        log_info "Creating parameters file: $params_file"
        mkdir -p "$PARAMS_DIR"
        cat > "$params_file" << EOF
{
  "\$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "environment": {
      "value": "$ENVIRONMENT"
    },
    "location": {
      "value": "$LOCATION"
    },
    "openaiServiceName": {
      "value": "$(echo "$AZURE_OPENAI_ENDPOINT" | sed 's|https://||' | sed 's|\.openai\.azure\.com||')"
    },
    "mlWorkspaceName": {
      "value": "orca-ml-workspace-$ENVIRONMENT"
    },
    "acrName": {
      "value": "orcacoreacr$ENVIRONMENT"
    },
    "aksName": {
      "value": "orca-aks-$ENVIRONMENT"
    },
    "keyVaultName": {
      "value": "orca-keyvault-$ENVIRONMENT"
    },
    "appInsightsName": {
      "value": "orca-appinsights-$ENVIRONMENT"
    },
    "storageAccountName": {
      "value": "orcacorestorage$ENVIRONMENT"
    }
  }
}
EOF
    fi

    # Deploy main infrastructure
    log_info "Deploying main infrastructure..."
    az deployment group create \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --template-file "$bicep_dir/main.bicep" \
        --parameters "@$params_file" \
        --name "orca-infrastructure-$(date +%Y%m%d-%H%M%S)"

    # Deploy Key Vault secrets
    log_info "Deploying Key Vault secrets..."
    az deployment group create \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --template-file "$bicep_dir/keyvault-secrets.bicep" \
        --parameters \
            keyVaultName="orca-keyvault-$ENVIRONMENT" \
            azureOpenaiApiKey="$AZURE_OPENAI_API_KEY" \
            azureOpenaiEndpoint="$AZURE_OPENAI_ENDPOINT" \
            azureOpenaiDeployment="$AZURE_OPENAI_DEPLOYMENT" \
        --name "orca-secrets-$(date +%Y%m%d-%H%M%S)"

    log_success "Bicep deployment completed successfully"
}

# Function to deploy with Terraform
deploy_terraform() {
    log_info "Deploying infrastructure with Terraform..."

    local terraform_dir="$SCRIPT_DIR/../terraform"
    local tfvars_file="$terraform_dir/terraform.tfvars"

    # Create terraform.tfvars file
    if [ ! -f "$tfvars_file" ]; then
        log_info "Creating terraform.tfvars file..."
        cat > "$tfvars_file" << EOF
# Terraform variables for Orca Core
resource_group_name = "$RESOURCE_GROUP_NAME"
location           = "$LOCATION"
environment        = "$ENVIRONMENT"

openai_service_name     = "$(echo "$AZURE_OPENAI_ENDPOINT" | sed 's|https://||' | sed 's|\.openai\.azure\.com||')"
openai_deployment_name  = "$AZURE_OPENAI_DEPLOYMENT"

ml_workspace_name = "orca-ml-workspace-$ENVIRONMENT"
acr_name         = "orcacoreacr$ENVIRONMENT"
aks_name         = "orca-aks-$ENVIRONMENT"
key_vault_name   = "orca-keyvault-$ENVIRONMENT"
app_insights_name = "orca-appinsights-$ENVIRONMENT"
storage_account_name = "orcacorestorage$ENVIRONMENT"

tags = {
  Project     = "OrcaCore"
  Environment = "$ENVIRONMENT"
  ManagedBy   = "Terraform"
}
EOF
    fi

    # Initialize and deploy Terraform
    cd "$terraform_dir"
    terraform init
    terraform plan -out=tfplan
    terraform apply tfplan

    log_success "Terraform deployment completed successfully"
}

# Function to configure kubectl
configure_kubectl() {
    log_info "Configuring kubectl for AKS cluster..."

    local aks_name="orca-aks-$ENVIRONMENT"

    # Get AKS credentials
    az aks get-credentials \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --name "$aks_name" \
        --overwrite-existing

    # Verify connection
    if kubectl cluster-info >/dev/null 2>&1; then
        log_success "kubectl configured successfully"
        log_info "Current context: $(kubectl config current-context)"
    else
        log_error "Failed to configure kubectl"
        exit 1
    fi
}

# Function to display deployment summary
display_summary() {
    log_success "Azure infrastructure deployment completed!"
    echo
    log_info "Deployment Summary:"
    echo "  Environment: $ENVIRONMENT"
    echo "  Resource Group: $RESOURCE_GROUP_NAME"
    echo "  Location: $LOCATION"
    echo "  Deployment Method: $DEPLOYMENT_METHOD"
    echo
    log_info "Next Steps:"
    echo "  1. Build and push Docker images: make build-docker"
    echo "  2. Deploy to AKS: make deploy-azure"
    echo "  3. Configure monitoring: kubectl apply -f k8s/monitoring/"
    echo "  4. Test the deployment: make test-deployment"
    echo
    log_info "Useful Commands:"
    echo "  View AKS cluster: az aks show --resource-group $RESOURCE_GROUP_NAME --name orca-aks-$ENVIRONMENT"
    echo "  Get AKS credentials: az aks get-credentials --resource-group $RESOURCE_GROUP_NAME --name orca-aks-$ENVIRONMENT"
    echo "  View Key Vault: az keyvault show --name orca-keyvault-$ENVIRONMENT"
    echo "  List secrets: az keyvault secret list --vault-name orca-keyvault-$ENVIRONMENT"
}

# Function to show help
show_help() {
    cat << EOF
Orca Core Azure Infrastructure Bootstrap Script

Usage: $0 [OPTIONS]

Options:
  -e, --environment ENV    Environment name (dev, staging, prod) [default: dev]
  -l, --location LOC       Azure location [default: East US]
  -m, --method METHOD      Deployment method (bicep, terraform) [default: bicep]
  -h, --help              Show this help message

Examples:
  $0                                    # Deploy with default settings
  $0 -e staging -l "West US 2"         # Deploy staging environment
  $0 -m terraform                      # Deploy using Terraform
  $0 -e prod -l "East US" -m bicep     # Deploy production with Bicep

Prerequisites:
  - Azure CLI installed and logged in
  - Environment file (.env.local) configured
  - Required permissions to create Azure resources

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -l|--location)
            LOCATION="$2"
            shift 2
            ;;
        -m|--method)
            DEPLOYMENT_METHOD="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate deployment method
if [[ "$DEPLOYMENT_METHOD" != "bicep" && "$DEPLOYMENT_METHOD" != "terraform" ]]; then
    log_error "Invalid deployment method: $DEPLOYMENT_METHOD"
    log_error "Supported methods: bicep, terraform"
    exit 1
fi

# Main execution
main() {
    log_info "Starting Orca Core Azure infrastructure deployment..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Location: $LOCATION"
    log_info "Deployment Method: $DEPLOYMENT_METHOD"
    echo

    check_prerequisites
    load_environment
    create_resource_group

    if [ "$DEPLOYMENT_METHOD" = "bicep" ]; then
        deploy_bicep
    else
        deploy_terraform
    fi

    configure_kubectl
    display_summary
}

# Run main function
main "$@"
