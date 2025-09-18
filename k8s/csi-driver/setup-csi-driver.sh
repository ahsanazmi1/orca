#!/bin/bash

# Azure Key Vault CSI Driver Setup Script
# This script sets up the Azure Key Vault CSI driver for Orca Core

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    print_success "kubectl is available"
}

# Function to check if az CLI is available
check_az_cli() {
    if ! command -v az &> /dev/null; then
        print_error "Azure CLI is not installed or not in PATH"
        exit 1
    fi
    print_success "Azure CLI is available"
}

# Function to check if user is logged in to Azure
check_az_login() {
    if ! az account show &> /dev/null; then
        print_error "Not logged in to Azure. Please run 'az login'"
        exit 1
    fi
    print_success "Logged in to Azure"
}

# Function to install CSI driver
install_csi_driver() {
    print_status "Installing Azure Key Vault CSI driver..."

    if kubectl apply -f install-csi-driver.yaml; then
        print_success "CSI driver installed successfully"
    else
        print_error "Failed to install CSI driver"
        exit 1
    fi
}

# Function to create managed identity
create_managed_identity() {
    local environment=$1
    local resource_group="orcacore-rg"
    local identity_name="orca-keyvault-identity-$environment"

    print_status "Creating managed identity: $identity_name"

    # Check if identity already exists
    if az identity show --name "$identity_name" --resource-group "$resource_group" &> /dev/null; then
        print_warning "Managed identity $identity_name already exists"
    else
        if az identity create --name "$identity_name" --resource-group "$resource_group"; then
            print_success "Managed identity created: $identity_name"
        else
            print_error "Failed to create managed identity"
            exit 1
        fi
    fi

    # Get the identity details
    local client_id=$(az identity show --name "$identity_name" --resource-group "$resource_group" --query "clientId" -o tsv)
    local resource_id=$(az identity show --name "$identity_name" --resource-group "$resource_group" --query "id" -o tsv)

    print_status "Client ID: $client_id"
    print_status "Resource ID: $resource_id"

    # Update the Azure Identity manifest
    sed -i.bak "s|clientID: \"\"|clientID: \"$client_id\"|g" azure-identity.yaml
    sed -i.bak "s|resourceID: /subscriptions/.*|resourceID: $resource_id|g" azure-identity.yaml

    print_success "Updated Azure Identity manifest"
}

# Function to assign Key Vault permissions
assign_keyvault_permissions() {
    local environment=$1
    local resource_group="orcacore-rg"
    local identity_name="orca-keyvault-identity-$environment"
    local keyvault_name="orca-keyvault-$environment"

    print_status "Assigning Key Vault permissions to managed identity..."

    # Get the identity principal ID
    local principal_id=$(az identity show --name "$identity_name" --resource-group "$resource_group" --query "principalId" -o tsv)

    # Assign Key Vault Secrets User role
    if az role assignment create \
        --assignee "$principal_id" \
        --role "Key Vault Secrets User" \
        --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$resource_group/providers/Microsoft.KeyVault/vaults/$keyvault_name"; then
        print_success "Key Vault permissions assigned"
    else
        print_warning "Failed to assign Key Vault permissions (may already exist)"
    fi
}

# Function to apply manifests
apply_manifests() {
    local environment=$1

    print_status "Applying manifests for environment: $environment"

    # Apply Azure Identity
    if kubectl apply -f azure-identity.yaml; then
        print_success "Azure Identity applied"
    else
        print_error "Failed to apply Azure Identity"
        exit 1
    fi

    # Apply SecretProviderClass for the environment
    local secret_provider_file="secret-provider-class-$environment.yaml"
    if [ -f "$secret_provider_file" ]; then
        if kubectl apply -f "$secret_provider_file"; then
            print_success "SecretProviderClass applied for $environment"
        else
            print_error "Failed to apply SecretProviderClass for $environment"
            exit 1
        fi
    else
        print_error "SecretProviderClass file not found: $secret_provider_file"
        exit 1
    fi
}

# Function to verify installation
verify_installation() {
    print_status "Verifying CSI driver installation..."

    # Check if CSI driver pods are running
    if kubectl get pods -n kube-system | grep -q "secrets-store-csi-driver"; then
        print_success "CSI driver pods are running"
    else
        print_error "CSI driver pods are not running"
        exit 1
    fi

    # Check if SecretProviderClass is created
    if kubectl get secretproviderclass -n orca-core | grep -q "orca-keyvault-secrets"; then
        print_success "SecretProviderClass is created"
    else
        print_error "SecretProviderClass is not created"
        exit 1
    fi

    # Check if Azure Identity is created
    if kubectl get azureidentity -n orca-core | grep -q "orca-keyvault-identity"; then
        print_success "Azure Identity is created"
    else
        print_error "Azure Identity is not created"
        exit 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [environment]"
    echo ""
    echo "Environments:"
    echo "  dev       - Development environment"
    echo "  staging   - Staging environment"
    echo "  prod      - Production environment"
    echo ""
    echo "Examples:"
    echo "  $0 dev"
    echo "  $0 staging"
    echo "  $0 prod"
}

# Main function
main() {
    local environment=${1:-dev}

    print_status "Setting up Azure Key Vault CSI driver for environment: $environment"

    # Validate environment
    if [[ ! "$environment" =~ ^(dev|staging|prod)$ ]]; then
        print_error "Invalid environment: $environment"
        show_usage
        exit 1
    fi

    # Check prerequisites
    check_kubectl
    check_az_cli
    check_az_login

    # Install CSI driver
    install_csi_driver

    # Create managed identity
    create_managed_identity "$environment"

    # Assign Key Vault permissions
    assign_keyvault_permissions "$environment"

    # Apply manifests
    apply_manifests "$environment"

    # Verify installation
    verify_installation

    print_success "Azure Key Vault CSI driver setup completed for $environment"
    print_status "You can now deploy Orca Core with Key Vault integration"
}

# Run main function
main "$@"
