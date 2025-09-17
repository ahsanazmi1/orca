#!/bin/bash
# Key Vault Secrets Management for Orca Core
# This script manages secrets in Azure Key Vault

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

# Default values
ENVIRONMENT="dev"
KEY_VAULT_NAME=""
ACTION=""

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if Azure CLI is installed
    if ! command -v az >/dev/null 2>&1; then
        log_error "Azure CLI is not installed. Please install it first:"
        log_error "  https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi

    # Check if user is logged in to Azure
    if ! az account show >/dev/null 2>&1; then
        log_error "You are not logged in to Azure. Please run: az login"
        exit 1
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

    # Set Key Vault name if not provided
    if [ -z "$KEY_VAULT_NAME" ]; then
        KEY_VAULT_NAME="orca-keyvault-$ENVIRONMENT"
    fi

    log_success "Environment variables loaded successfully"
}

# Function to validate Key Vault exists
validate_key_vault() {
    log_info "Validating Key Vault: $KEY_VAULT_NAME"

    if ! az keyvault show --name "$KEY_VAULT_NAME" >/dev/null 2>&1; then
        log_error "Key Vault '$KEY_VAULT_NAME' does not exist"
        log_error "Please run the bootstrap script first to create the infrastructure"
        exit 1
    fi

    log_success "Key Vault validation completed"
}

# Function to set secrets in Key Vault
set_secrets() {
    log_info "Setting secrets in Key Vault: $KEY_VAULT_NAME"

    # Azure OpenAI secrets
    if [ -n "${AZURE_OPENAI_API_KEY:-}" ]; then
        log_info "Setting Azure OpenAI API key..."
        az keyvault secret set \
            --vault-name "$KEY_VAULT_NAME" \
            --name "azure-openai-api-key" \
            --value "$AZURE_OPENAI_API_KEY" \
            --output none
        log_success "Azure OpenAI API key set"
    fi

    if [ -n "${AZURE_OPENAI_ENDPOINT:-}" ]; then
        log_info "Setting Azure OpenAI endpoint..."
        az keyvault secret set \
            --vault-name "$KEY_VAULT_NAME" \
            --name "azure-openai-endpoint" \
            --value "$AZURE_OPENAI_ENDPOINT" \
            --output none
        log_success "Azure OpenAI endpoint set"
    fi

    if [ -n "${AZURE_OPENAI_DEPLOYMENT:-}" ]; then
        log_info "Setting Azure OpenAI deployment..."
        az keyvault secret set \
            --vault-name "$KEY_VAULT_NAME" \
            --name "azure-openai-deployment" \
            --value "$AZURE_OPENAI_DEPLOYMENT" \
            --output none
        log_success "Azure OpenAI deployment set"
    fi

    # Azure ML secrets (if available)
    if [ -n "${AZURE_ML_WORKSPACE_KEY:-}" ]; then
        log_info "Setting Azure ML workspace key..."
        az keyvault secret set \
            --vault-name "$KEY_VAULT_NAME" \
            --name "azure-ml-workspace-key" \
            --value "$AZURE_ML_WORKSPACE_KEY" \
            --output none
        log_success "Azure ML workspace key set"
    fi

    if [ -n "${AZURE_ML_WORKSPACE_ENDPOINT:-}" ]; then
        log_info "Setting Azure ML workspace endpoint..."
        az keyvault secret set \
            --vault-name "$KEY_VAULT_NAME" \
            --name "azure-ml-workspace-endpoint" \
            --value "$AZURE_ML_WORKSPACE_ENDPOINT" \
            --output none
        log_success "Azure ML workspace endpoint set"
    fi

    # Orca Core configuration secrets
    log_info "Setting Orca Core configuration secrets..."

    az keyvault secret set \
        --vault-name "$KEY_VAULT_NAME" \
        --name "environment" \
        --value "$ENVIRONMENT" \
        --output none

    az keyvault secret set \
        --vault-name "$KEY_VAULT_NAME" \
        --name "orca-decision-mode" \
        --value "RULES_PLUS_AI" \
        --output none

    az keyvault secret set \
        --vault-name "$KEY_VAULT_NAME" \
        --name "orca-use-xgb" \
        --value "true" \
        --output none

    az keyvault secret set \
        --vault-name "$KEY_VAULT_NAME" \
        --name "orca-explain-enabled" \
        --value "true" \
        --output none

    log_success "Orca Core configuration secrets set"

    log_success "All secrets set successfully in Key Vault"
}

# Function to get secrets from Key Vault
get_secrets() {
    log_info "Getting secrets from Key Vault: $KEY_VAULT_NAME"

    # List all secrets
    log_info "Available secrets:"
    az keyvault secret list \
        --vault-name "$KEY_VAULT_NAME" \
        --query "[].name" \
        --output table

    echo
    log_info "Secret values (use with caution):"

    # Get specific secrets
    local secrets=(
        "azure-openai-api-key"
        "azure-openai-endpoint"
        "azure-openai-deployment"
        "environment"
        "orca-decision-mode"
        "orca-use-xgb"
        "orca-explain-enabled"
    )

    for secret in "${secrets[@]}"; do
        if az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name "$secret" >/dev/null 2>&1; then
            local value=$(az keyvault secret show \
                --vault-name "$KEY_VAULT_NAME" \
                --name "$secret" \
                --query "value" \
                --output tsv)
            echo "  $secret: $value"
        else
            echo "  $secret: (not found)"
        fi
    done
}

# Function to delete secrets from Key Vault
delete_secrets() {
    log_warning "This will delete all Orca Core secrets from Key Vault: $KEY_VAULT_NAME"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Operation cancelled"
        exit 0
    fi

    log_info "Deleting secrets from Key Vault: $KEY_VAULT_NAME"

    local secrets=(
        "azure-openai-api-key"
        "azure-openai-endpoint"
        "azure-openai-deployment"
        "azure-ml-workspace-key"
        "azure-ml-workspace-endpoint"
        "environment"
        "orca-decision-mode"
        "orca-use-xgb"
        "orca-explain-enabled"
    )

    for secret in "${secrets[@]}"; do
        if az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name "$secret" >/dev/null 2>&1; then
            log_info "Deleting secret: $secret"
            az keyvault secret delete \
                --vault-name "$KEY_VAULT_NAME" \
                --name "$secret" \
                --output none
            log_success "Secret deleted: $secret"
        else
            log_warning "Secret not found: $secret"
        fi
    done

    log_success "All secrets deleted successfully"
}

# Function to backup secrets
backup_secrets() {
    local backup_file="keyvault-backup-$(date +%Y%m%d-%H%M%S).json"
    log_info "Backing up secrets to: $backup_file"

    # Get all secrets and create backup
    az keyvault secret list \
        --vault-name "$KEY_VAULT_NAME" \
        --query "[].{name:name,value:value}" \
        --output json > "$backup_file"

    log_success "Secrets backed up to: $backup_file"
}

# Function to restore secrets
restore_secrets() {
    local backup_file="$1"

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    log_info "Restoring secrets from: $backup_file"

    # Parse backup file and restore secrets
    jq -r '.[] | "\(.name) \(.value)"' "$backup_file" | while read -r name value; do
        log_info "Restoring secret: $name"
        az keyvault secret set \
            --vault-name "$KEY_VAULT_NAME" \
            --name "$name" \
            --value "$value" \
            --output none
        log_success "Secret restored: $name"
    done

    log_success "All secrets restored successfully"
}

# Function to show help
show_help() {
    cat << EOF
Key Vault Secrets Management for Orca Core

Usage: $0 [OPTIONS] ACTION

Actions:
  set       Set secrets in Key Vault from environment variables
  get       Get and display secrets from Key Vault
  delete    Delete all Orca Core secrets from Key Vault
  backup    Backup all secrets to a JSON file
  restore   Restore secrets from a backup file

Options:
  -e, --environment ENV    Environment name (dev, staging, prod) [default: dev]
  -v, --vault-name NAME    Key Vault name [default: orca-keyvault-ENVIRONMENT]
  -f, --file FILE          Backup file for restore action
  -h, --help              Show this help message

Examples:
  $0 set                                    # Set secrets from .env.local
  $0 get                                    # Display all secrets
  $0 delete                                 # Delete all secrets
  $0 backup                                 # Backup secrets to file
  $0 restore -f backup.json                 # Restore from backup
  $0 set -e staging                         # Set secrets for staging environment

Prerequisites:
  - Azure CLI installed and logged in
  - Environment file (.env.local) configured
  - Key Vault exists and accessible

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -v|--vault-name)
            KEY_VAULT_NAME="$2"
            shift 2
            ;;
        -f|--file)
            BACKUP_FILE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        set|get|delete|backup|restore)
            ACTION="$1"
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate action
if [ -z "$ACTION" ]; then
    log_error "No action specified"
    show_help
    exit 1
fi

# Main execution
main() {
    log_info "Starting Key Vault secrets management..."
    log_info "Action: $ACTION"
    log_info "Environment: $ENVIRONMENT"
    log_info "Key Vault: $KEY_VAULT_NAME"
    echo

    check_prerequisites
    load_environment
    validate_key_vault

    case $ACTION in
        set)
            set_secrets
            ;;
        get)
            get_secrets
            ;;
        delete)
            delete_secrets
            ;;
        backup)
            backup_secrets
            ;;
        restore)
            if [ -z "${BACKUP_FILE:-}" ]; then
                log_error "Backup file not specified for restore action"
                log_error "Use: $0 restore -f backup.json"
                exit 1
            fi
            restore_secrets "$BACKUP_FILE"
            ;;
        *)
            log_error "Invalid action: $ACTION"
            show_help
            exit 1
            ;;
    esac

    log_success "Key Vault secrets management completed successfully"
}

# Run main function
main "$@"


