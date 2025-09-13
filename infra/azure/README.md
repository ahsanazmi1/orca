# Azure Infrastructure for Orca Core

This directory contains Azure infrastructure as code templates for deploying Orca Core.

## Prerequisites

- Azure CLI installed and configured
- Azure subscription with appropriate permissions
- Bicep CLI (included with Azure CLI 2.20.0+)

## Resources

This template creates the following Azure resources:

- **Resource Group**: Container for all resources
- **Azure Container Registry (ACR)**: For storing Docker images
- **Azure Key Vault**: For storing secrets and certificates
- **Azure Kubernetes Service (AKS)**: For running the application

## Deployment

### 1. Login to Azure

```bash
az login
az account set --subscription "your-subscription-id"
```

### 2. Deploy Infrastructure

```bash
# Deploy to development environment
az deployment group create \
  --resource-group rg-orca-core-dev \
  --template-file main.bicep \
  --parameters @parameters.json
```

### 3. Configure AKS Access

```bash
# Get AKS credentials
az aks get-credentials --resource-group rg-orca-core-dev --name aks-orca-core-dev

# Verify connection
kubectl get nodes
```

## Configuration

### Service Principal Setup

Before deploying, you need to create a service principal for AKS:

```bash
# Create service principal
az ad sp create-for-rbac --name "sp-orca-core-aks" --role contributor --scopes /subscriptions/{subscription-id}/resourceGroups/rg-orca-core-dev

# Note the appId and password for the Bicep template
```

### Key Vault Access

Configure access policies for Key Vault:

```bash
# Get your user object ID
az ad signed-in-user show --query objectId -o tsv

# Add access policy (replace with your object ID)
az keyvault set-policy \
  --name kv-orca-core-dev-{unique-id} \
  --object-id {your-object-id} \
  --secret-permissions get list set delete
```

## Security Considerations

- All resources use RBAC for access control
- Key Vault has soft delete enabled
- AKS uses managed identity
- Network policies are configured for AKS

## Cost Optimization

- AKS uses auto-scaling node pools
- ACR uses Basic SKU (suitable for development)
- Key Vault uses Standard SKU

## Monitoring

Consider adding:
- Azure Monitor
- Application Insights
- Log Analytics workspace
- Azure Security Center

## Cleanup

To remove all resources:

```bash
az group delete --name rg-orca-core-dev --yes --no-wait
```

## TODO

- [ ] Add monitoring and logging resources
- [ ] Configure network security groups
- [ ] Set up backup policies
- [ ] Add production environment parameters
- [ ] Configure SSL/TLS certificates
- [ ] Set up CI/CD pipeline integration
