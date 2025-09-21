# GitHub Actions OIDC Setup for Azure

This document explains how to set up OpenID Connect (OIDC) authentication between GitHub Actions and Azure for secure, credential-free deployments.

## 🔐 Overview

OIDC allows GitHub Actions to authenticate with Azure without storing long-lived credentials as secrets. Instead, GitHub generates short-lived tokens that Azure can verify.

## 🏗️ Azure Setup

### 1. Create Azure AD Application

```bash
# Create Azure AD application
az ad app create --display-name "OrcaCore-GitHub-Actions"

# Get the application ID (client ID)
APP_ID=$(az ad app list --display-name "OrcaCore-GitHub-Actions" --query "[0].appId" -o tsv)
echo "Application ID: $APP_ID"

# Create service principal
az ad sp create --id $APP_ID

# Get the object ID
OBJECT_ID=$(az ad sp show --id $APP_ID --query "id" -o tsv)
echo "Object ID: $OBJECT_ID"
```

### 2. Create Federated Identity Credential

```bash
# Set variables
RESOURCE_GROUP="orcacore-rg"
SUBSCRIPTION_ID="your-subscription-id"
TENANT_ID="your-tenant-id"
REPO="your-org/orca-core"  # GitHub repository in format owner/repo

# Create federated identity credential for main branch
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "orca-core-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'$REPO':ref:refs/heads/main",
    "description": "GitHub Actions for main branch",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# Create federated identity credential for develop branch
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "orca-core-develop",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'$REPO':ref:refs/heads/develop",
    "description": "GitHub Actions for develop branch",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# Create federated identity credential for pull requests
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "orca-core-pr",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'$REPO':pull_request",
    "description": "GitHub Actions for pull requests",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# Create federated identity credential for tags
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "orca-core-tags",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'$REPO':ref:refs/tags/*",
    "description": "GitHub Actions for tags",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

### 3. Assign Permissions

```bash
# Assign Contributor role to the service principal
az role assignment create \
  --assignee $APP_ID \
  --role "Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP"

# Assign additional roles for specific services
az role assignment create \
  --assignee $APP_ID \
  --role "AcrPush" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ContainerRegistry/registries/orcacoreacrdev"

az role assignment create \
  --assignee $APP_ID \
  --role "Key Vault Secrets User" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.KeyVault/vaults/orca-keyvault-dev"
```

## 🔧 GitHub Setup

### 1. Add Repository Secrets

Add the following secrets to your GitHub repository:

```bash
# Required secrets
AZURE_CLIENT_ID="your-application-id"
AZURE_TENANT_ID="your-tenant-id"
AZURE_SUBSCRIPTION_ID="your-subscription-id"

# Azure resource names
AZURE_RESOURCE_GROUP="orcacore-rg"
ACR_NAME="orcacoreacrdev"
AKS_NAME="orca-aks-dev"

# ACR credentials (for Docker login)
ACR_USERNAME="your-acr-username"
ACR_PASSWORD="your-acr-password"

# Azure OpenAI secrets (for Key Vault)
AZURE_OPENAI_API_KEY="your-openai-api-key"
AZURE_OPENAI_ENDPOINT="your-openai-endpoint"
AZURE_OPENAI_DEPLOYMENT="gpt-4o-mini"
```

### 2. Set up Environment Protection Rules

1. Go to your repository settings
2. Navigate to "Environments"
3. Create environments: `dev`, `staging`, `prod`
4. For each environment:
   - Add required reviewers (for staging/prod)
   - Set deployment branches (main for prod, develop for staging)
   - Add environment secrets if needed

## 🚀 Usage

### Automatic Deployments

- **Push to `main`**: Deploys to production
- **Push to `develop`**: Deploys to staging
- **Pull Request**: Runs tests and validation
- **Tag push**: Creates release and deploys to production

### Manual Deployments

Use the "Actions" tab in GitHub to manually trigger deployments:

1. Go to "Actions" → "Deploy Orca Core to Azure"
2. Click "Run workflow"
3. Select environment and options
4. Click "Run workflow"

### Workflow Dispatch

```bash
# Trigger deployment via GitHub CLI
gh workflow run deploy.yml -f environment=staging
gh workflow run deploy.yml -f environment=prod
```

## 🔍 Verification

### Test OIDC Authentication

```bash
# Test the OIDC setup
az login --service-principal \
  --username $APP_ID \
  --tenant $TENANT_ID \
  --federated-token $(gh auth token)
```

### Verify Permissions

```bash
# Check role assignments
az role assignment list --assignee $APP_ID --all

# Test ACR access
az acr login --name orcacoreacrdev

# Test AKS access
az aks get-credentials --resource-group orcacore-rg --name orca-aks-dev
```

## 🛡️ Security Best Practices

### 1. Least Privilege

- Only assign necessary permissions
- Use specific resource scopes
- Regularly review and rotate credentials

### 2. Environment Isolation

- Separate service principals for different environments
- Use different Azure subscriptions for prod/staging
- Implement network isolation

### 3. Monitoring

- Enable Azure AD audit logs
- Monitor GitHub Actions usage
- Set up alerts for unusual activity

### 4. Secret Management

- Use Azure Key Vault for sensitive data
- Rotate secrets regularly
- Use short-lived tokens

## 🔧 Troubleshooting

### Common Issues

1. **Authentication Failed**
   ```
   Error: AADSTS70021: No matching federated identity record found
   ```
   - Check federated identity credential configuration
   - Verify repository name and branch names
   - Ensure issuer URL is correct

2. **Insufficient Permissions**
   ```
   Error: The client does not have authorization to perform action
   ```
   - Check role assignments
   - Verify resource scopes
   - Ensure service principal has necessary permissions

3. **Key Vault Access Denied**
   ```
   Error: Access denied to Key Vault
   ```
   - Check Key Vault access policies
   - Verify "Key Vault Secrets User" role
   - Ensure managed identity is configured

### Debug Commands

```bash
# Check federated credentials
az ad app federated-credential list --id $APP_ID

# Check role assignments
az role assignment list --assignee $APP_ID --all

# Check Key Vault access
az keyvault show --name orca-keyvault-dev

# Test AKS access
az aks get-credentials --resource-group orcacore-rg --name orca-aks-dev
kubectl cluster-info
```

## 📚 Additional Resources

- [GitHub Actions OIDC Documentation](https://docs.github.com/en/actions/deployment/security/hardening-your-deployments/about-security-hardening-with-openid-connect)
- [Azure AD App Registration](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)
- [Azure RBAC](https://docs.microsoft.com/en-us/azure/role-based-access-control/)
- [GitHub Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)


