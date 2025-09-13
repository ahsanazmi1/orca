# Azure OIDC Setup for GitHub Actions

This guide explains how to set up federated credentials in Azure Entra (formerly Azure Active Directory) and GitHub for secure, keyless authentication.

## Overview

OpenID Connect (OIDC) allows GitHub Actions to authenticate with Azure without storing secrets. This is more secure than using service principal secrets and follows the principle of least privilege.

## Prerequisites

- Azure subscription with Owner or User Access Administrator permissions
- GitHub repository with admin access
- Azure CLI installed and configured

## Step 1: Create Azure App Registration

1. **Create App Registration in Azure Portal:**

   ```bash
   # Login to Azure
   az login

   # Create app registration
   az ad app create --display-name "orca-core-github-actions"
   ```

   Note the `appId` from the output - this is your `AZURE_CLIENT_ID`.

2. **Get Tenant ID:**

   ```bash
   az account show --query tenantId -o tsv
   ```

   This is your `AZURE_TENANT_ID`.

3. **Get Subscription ID:**

   ```bash
   az account show --query id -o tsv
   ```

   This is your `AZURE_SUBSCRIPTION_ID`.

## Step 2: Create Federated Credential

1. **Create federated credential for main branch:**

   ```bash
   # Replace with your actual values
   APP_ID="your-app-id"
   RESOURCE_GROUP="rg-orca-core-dev"
   REPO="your-org/orca-core"  # Format: owner/repo

   az ad app federated-credential create \
     --id $APP_ID \
     --parameters '{
       "name": "orca-core-main",
       "issuer": "https://token.actions.githubusercontent.com",
       "subject": "repo:'$REPO':ref:refs/heads/main",
       "description": "GitHub Actions for main branch",
       "audiences": ["api://AzureADTokenExchange"]
     }'
   ```

2. **Create federated credential for pull requests:**

   ```bash
   az ad app federated-credential create \
     --id $APP_ID \
     --parameters '{
       "name": "orca-core-pr",
       "issuer": "https://token.actions.githubusercontent.com",
       "subject": "repo:'$REPO':pull_request",
       "description": "GitHub Actions for pull requests",
       "audiences": ["api://AzureADTokenExchange"]
     }'
   ```

## Step 3: Assign Roles

1. **Assign Contributor role to resource group:**

   ```bash
   # Get the object ID of the app registration
   APP_OBJECT_ID=$(az ad app show --id $APP_ID --query id -o tsv)

   # Assign Contributor role to resource group
   az role assignment create \
     --assignee $APP_OBJECT_ID \
     --role "Contributor" \
     --scope "/subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP"
   ```

2. **Assign ACR Push role (for container registry):**

   ```bash
   # Get ACR resource ID
   ACR_ID=$(az acr show --name acrorcacoredev{unique-id} --resource-group $RESOURCE_GROUP --query id -o tsv)

   # Assign AcrPush role
   az role assignment create \
     --assignee $APP_OBJECT_ID \
     --role "AcrPush" \
     --scope $ACR_ID
   ```

## Step 4: Configure GitHub Secrets

Add the following secrets to your GitHub repository:

1. Go to your repository → Settings → Secrets and variables → Actions
2. Add these repository secrets:

   - `AZURE_CLIENT_ID`: The app registration ID from Step 1
   - `AZURE_TENANT_ID`: Your Azure tenant ID
   - `AZURE_SUBSCRIPTION_ID`: Your Azure subscription ID

## Step 5: Test the Setup

1. **Create a test workflow:**

   ```yaml
   name: Test OIDC
   on: [push]

   jobs:
     test:
       runs-on: ubuntu-latest
       permissions:
         id-token: write
         contents: read

       steps:
       - name: Azure Login
         uses: azure/login@v1
         with:
           client-id: ${{ secrets.AZURE_CLIENT_ID }}
           tenant-id: ${{ secrets.AZURE_TENANT_ID }}
           subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

       - name: Test Azure CLI
         run: |
           az account show
           az group list --query "[].name" -o table
   ```

2. **Push to main branch and verify the workflow runs successfully.**

## Security Best Practices

### Least Privilege Access

- Only assign the minimum required roles
- Use resource group or resource-level scopes instead of subscription-level
- Regularly review and audit role assignments

### Role Recommendations

For Orca Core deployment, the following roles are typically needed:

- **Contributor**: For deploying resources to the resource group
- **AcrPush**: For pushing container images to ACR
- **Key Vault Secrets User**: For accessing secrets (if needed)

### Monitoring

- Enable Azure AD audit logs
- Monitor GitHub Actions logs for authentication issues
- Set up alerts for failed authentication attempts

## Troubleshooting

### Common Issues

1. **"AADSTS50199: CdsiClientException"**
   - Check that the federated credential subject matches your repository and branch
   - Verify the issuer URL is correct

2. **"Insufficient privileges"**
   - Verify role assignments are correct
   - Check that the app registration has the right permissions

3. **"Invalid audience"**
   - Ensure the audience is set to `api://AzureADTokenExchange`

### Debug Commands

```bash
# Check app registration
az ad app show --id $APP_ID

# List federated credentials
az ad app federated-credential list --id $APP_ID

# Check role assignments
az role assignment list --assignee $APP_OBJECT_ID --all

# Test authentication
az login --service-principal --username $APP_ID --tenant $AZURE_TENANT_ID
```

## Next Steps

1. Set up monitoring and alerting
2. Configure backup policies
3. Implement network security groups
4. Set up SSL/TLS certificates
5. Configure CI/CD pipeline for automated deployments

## References

- [Azure AD App Registration](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)
- [GitHub OIDC with Azure](https://docs.github.com/en/actions/deployment/security/hardening-your-deployments/configuring-openid-connect-in-azure)
- [Azure RBAC](https://docs.microsoft.com/en-us/azure/role-based-access-control/)
