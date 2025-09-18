#!/bin/bash
# Orca Core Azure Infrastructure Cleanup Script
# This script removes the Azure infrastructure for Orca Core

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
RESOURCE_GROUP_NAME="orcacore-rg"
CONFIRMATION_REQUIRED=true
DRY_RUN=false

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

    # Set variables from environment
    ENVIRONMENT="${ORCA_ENVIRONMENT:-dev}"
    RESOURCE_GROUP_NAME="$AZURE_RESOURCE_GROUP"

    log_success "Environment variables loaded successfully"
}

# Function to confirm deletion
confirm_deletion() {
    if [ "$CONFIRMATION_REQUIRED" = true ]; then
        log_warning "This will delete ALL Azure resources in the resource group: $RESOURCE_GROUP_NAME"
        log_warning "This action cannot be undone!"
        echo
        log_info "Resources that will be deleted:"

        # List resources in the resource group
        az resource list \
            --resource-group "$RESOURCE_GROUP_NAME" \
            --query "[].{Name:name, Type:type, Location:location}" \
            --output table

        echo
        read -p "Are you sure you want to delete all these resources? (yes/no): " -r
        echo

        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            log_info "Cleanup cancelled by user"
            exit 0
        fi
    fi
}

# Function to delete Kubernetes resources
delete_k8s_resources() {
    log_info "Deleting Kubernetes resources..."

    local namespace="orca-core"

    # Check if kubectl is available and cluster is accessible
    if command -v kubectl >/dev/null 2>&1; then
        # Try to get AKS credentials
        local aks_name="orca-aks-$ENVIRONMENT"
        if az aks show --resource-group "$RESOURCE_GROUP_NAME" --name "$aks_name" >/dev/null 2>&1; then
            log_info "Getting AKS credentials for cleanup..."
            az aks get-credentials \
                --resource-group "$RESOURCE_GROUP_NAME" \
                --name "$aks_name" \
                --overwrite-existing

            # Delete namespace (this will delete all resources in the namespace)
            if kubectl get namespace "$namespace" >/dev/null 2>&1; then
                log_info "Deleting Kubernetes namespace: $namespace"
                if [ "$DRY_RUN" = true ]; then
                    log_info "DRY RUN: Would delete namespace $namespace"
                else
                    kubectl delete namespace "$namespace" --ignore-not-found=true
                    log_success "Kubernetes namespace deleted"
                fi
            else
                log_warning "Kubernetes namespace '$namespace' not found"
            fi
        else
            log_warning "AKS cluster '$aks_name' not found, skipping Kubernetes cleanup"
        fi
    else
        log_warning "kubectl not available, skipping Kubernetes cleanup"
    fi
}

# Function to delete resource group
delete_resource_group() {
    log_info "Deleting resource group: $RESOURCE_GROUP_NAME"

    if az group show --name "$RESOURCE_GROUP_NAME" >/dev/null 2>&1; then
        if [ "$DRY_RUN" = true ]; then
            log_info "DRY RUN: Would delete resource group $RESOURCE_GROUP_NAME"
        else
            az group delete \
                --name "$RESOURCE_GROUP_NAME" \
                --yes \
                --no-wait
            log_success "Resource group deletion initiated"
            log_info "Note: Resource group deletion is asynchronous and may take several minutes"
        fi
    else
        log_warning "Resource group '$RESOURCE_GROUP_NAME' not found"
    fi
}

# Function to delete specific resources
delete_specific_resources() {
    log_info "Deleting specific Azure resources..."

    local resources=(
        "orca-aks-$ENVIRONMENT:Microsoft.ContainerService/managedClusters"
        "orca-keyvault-$ENVIRONMENT:Microsoft.KeyVault/vaults"
        "orca-ml-workspace-$ENVIRONMENT:Microsoft.MachineLearningServices/workspaces"
        "orcacoreacr$ENVIRONMENT:Microsoft.ContainerRegistry/registries"
        "orca-appinsights-$ENVIRONMENT:Microsoft.Insights/components"
        "orcacorestorage$ENVIRONMENT:Microsoft.Storage/storageAccounts"
        "orca-openai:Microsoft.CognitiveServices/accounts"
    )

    for resource in "${resources[@]}"; do
        local resource_name=$(echo "$resource" | cut -d: -f1)
        local resource_type=$(echo "$resource" | cut -d: -f2)

        if az resource show \
            --resource-group "$RESOURCE_GROUP_NAME" \
            --name "$resource_name" \
            --resource-type "$resource_type" >/dev/null 2>&1; then

            log_info "Deleting resource: $resource_name ($resource_type)"
            if [ "$DRY_RUN" = true ]; then
                log_info "DRY RUN: Would delete $resource_name"
            else
                az resource delete \
                    --resource-group "$RESOURCE_GROUP_NAME" \
                    --name "$resource_name" \
                    --resource-type "$resource_type" \
                    --output none
                log_success "Resource deleted: $resource_name"
            fi
        else
            log_warning "Resource not found: $resource_name"
        fi
    done
}

# Function to cleanup local files
cleanup_local_files() {
    log_info "Cleaning up local files..."

    local files_to_cleanup=(
        "$PROJECT_ROOT/.env.local"
        "$PROJECT_ROOT/k8s"
        "$PROJECT_ROOT/models"
        "$PROJECT_ROOT/.artifacts"
    )

    for file in "${files_to_cleanup[@]}"; do
        if [ -e "$file" ]; then
            log_info "Removing: $file"
            if [ "$DRY_RUN" = true ]; then
                log_info "DRY RUN: Would remove $file"
            else
                rm -rf "$file"
                log_success "Removed: $file"
            fi
        else
            log_warning "File not found: $file"
        fi
    done
}

# Function to show cleanup summary
show_cleanup_summary() {
    log_info "Cleanup Summary:"
    echo "  Environment: $ENVIRONMENT"
    echo "  Resource Group: $RESOURCE_GROUP_NAME"
    echo "  Dry Run: $DRY_RUN"
    echo

    if [ "$DRY_RUN" = true ]; then
        log_info "This was a dry run. No resources were actually deleted."
        log_info "To perform the actual cleanup, run the script without --dry-run"
    else
        log_success "Cleanup completed successfully!"
        echo
        log_info "Next Steps:"
        echo "  1. Verify resource group deletion: az group show --name $RESOURCE_GROUP_NAME"
        echo "  2. Check for any remaining resources: az resource list --resource-group $RESOURCE_GROUP_NAME"
        echo "  3. Clean up any local configuration files if needed"
        echo
        log_warning "Note: Some resources may take time to be fully deleted"
        log_warning "You can monitor the deletion progress in the Azure portal"
    fi
}

# Function to show help
show_help() {
    cat << EOF
Orca Core Azure Infrastructure Cleanup Script

Usage: $0 [OPTIONS]

Options:
  -e, --environment ENV    Environment name (dev, staging, prod) [default: dev]
  --no-confirm            Skip confirmation prompt
  --dry-run               Show what would be deleted without actually deleting
  --k8s-only              Only delete Kubernetes resources
  --local-only            Only delete local files
  -h, --help              Show this help message

Examples:
  $0                                    # Clean up with confirmation
  $0 --no-confirm                       # Clean up without confirmation
  $0 --dry-run                          # Show what would be deleted
  $0 --k8s-only                         # Only delete Kubernetes resources
  $0 --local-only                       # Only delete local files

WARNING: This script will delete ALL Azure resources in the resource group!
Make sure you have backups of any important data before running this script.

EOF
}

# Parse command line arguments
K8S_ONLY=false
LOCAL_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --no-confirm)
            CONFIRMATION_REQUIRED=false
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --k8s-only)
            K8S_ONLY=true
            shift
            ;;
        --local-only)
            LOCAL_ONLY=true
            shift
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

# Main execution
main() {
    log_info "Starting Orca Core Azure infrastructure cleanup..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Resource Group: $RESOURCE_GROUP_NAME"
    log_info "Dry Run: $DRY_RUN"
    echo

    check_prerequisites
    load_environment

    if [ "$LOCAL_ONLY" = true ]; then
        cleanup_local_files
    elif [ "$K8S_ONLY" = true ]; then
        delete_k8s_resources
    else
        confirm_deletion
        delete_k8s_resources
        delete_specific_resources
        delete_resource_group
        cleanup_local_files
    fi

    show_cleanup_summary
}

# Run main function
main "$@"
