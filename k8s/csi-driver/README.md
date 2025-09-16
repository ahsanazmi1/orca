# Azure Key Vault CSI Driver for Orca Core

This directory contains Kubernetes manifests and scripts for integrating Azure Key Vault with Orca Core using the Azure Key Vault CSI driver.

## 🔐 Overview

The Azure Key Vault CSI driver allows Kubernetes pods to securely access secrets stored in Azure Key Vault without storing credentials in the cluster. This provides:

- **Secure Secret Management**: Secrets are stored in Azure Key Vault, not in Kubernetes
- **Automatic Rotation**: Secrets can be rotated in Key Vault without pod restarts
- **Audit Trail**: All secret access is logged in Azure Key Vault
- **Fine-grained Access Control**: Managed identity-based authentication

## 📁 Files

### Core Manifests
- **`install-csi-driver.yaml`**: Installs the Azure Key Vault CSI driver and related components
- **`azure-identity.yaml`**: Defines the Azure managed identity for Key Vault access
- **`secret-provider-class.yaml`**: Generic SecretProviderClass template
- **`deployment-with-csi.yaml`**: Example deployment with CSI driver integration

### Environment-Specific Manifests
- **`secret-provider-class-dev.yaml`**: Development environment configuration
- **`secret-provider-class-staging.yaml`**: Staging environment configuration
- **`secret-provider-class-prod.yaml`**: Production environment configuration

### Scripts
- **`setup-csi-driver.sh`**: Automated setup script for CSI driver installation

## 🚀 Quick Start

### 1. Install CSI Driver

```bash
# Install the Azure Key Vault CSI driver
make csi-driver-install
```

### 2. Setup for Development

```bash
# Setup CSI driver for development environment
make csi-driver-setup-dev
```

### 3. Verify Installation

```bash
# Check CSI driver status
make csi-driver-status
```

### 4. Test Integration

```bash
# Test CSI driver integration
make csi-driver-test
```

## 🔧 Manual Setup

### Prerequisites

1. **Azure CLI**: Installed and logged in
2. **kubectl**: Configured to access your AKS cluster
3. **Azure Key Vault**: Created with secrets
4. **Managed Identity**: Created for Key Vault access

### Step 1: Install CSI Driver

```bash
kubectl apply -f install-csi-driver.yaml
```

### Step 2: Create Managed Identity

```bash
# Create managed identity
az identity create \
  --name orca-keyvault-identity-dev \
  --resource-group orcacore-rg

# Get identity details
CLIENT_ID=$(az identity show \
  --name orca-keyvault-identity-dev \
  --resource-group orcacore-rg \
  --query "clientId" -o tsv)

RESOURCE_ID=$(az identity show \
  --name orca-keyvault-identity-dev \
  --resource-group orcacore-rg \
  --query "id" -o tsv)
```

### Step 3: Assign Key Vault Permissions

```bash
# Get principal ID
PRINCIPAL_ID=$(az identity show \
  --name orca-keyvault-identity-dev \
  --resource-group orcacore-rg \
  --query "principalId" -o tsv)

# Assign Key Vault Secrets User role
az role assignment create \
  --assignee "$PRINCIPAL_ID" \
  --role "Key Vault Secrets User" \
  --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/orcacore-rg/providers/Microsoft.KeyVault/vaults/orca-keyvault-dev"
```

### Step 4: Update Manifests

Update `azure-identity.yaml` with your identity details:

```yaml
apiVersion: aadpodidentity.k8s.io/v1
kind: AzureIdentity
metadata:
  name: orca-keyvault-identity
  namespace: orca-core
spec:
  type: 0
  resourceID: /subscriptions/.../resourceGroups/.../providers/Microsoft.ManagedIdentity/userAssignedIdentities/orca-keyvault-identity-dev
  clientID: "your-client-id"
```

### Step 5: Apply Manifests

```bash
# Apply Azure Identity
kubectl apply -f azure-identity.yaml

# Apply SecretProviderClass for your environment
kubectl apply -f secret-provider-class-dev.yaml
```

## 🔍 Verification

### Check CSI Driver Status

```bash
# Check CSI driver pods
kubectl get pods -n kube-system | grep secrets-store-csi-driver

# Check SecretProviderClass
kubectl get secretproviderclass -n orca-core

# Check Azure Identity
kubectl get azureidentity -n orca-core
```

### Test Secret Access

```bash
# Deploy test pod
kubectl apply -f deployment-with-csi.yaml

# Check pod status
kubectl get pods -n orca-core -l app=orca-core-api

# Check mounted secrets
kubectl exec -n orca-core deployment/orca-core-api -- ls -la /mnt/secrets-store/

# Check environment variables
kubectl exec -n orca-core deployment/orca-core-api -- env | grep AZURE_OPENAI
```

## 🛡️ Security Features

### Managed Identity Authentication
- Uses Azure managed identity for authentication
- No secrets stored in Kubernetes
- Automatic token rotation

### Fine-grained Access Control
- Key Vault access policies
- Azure RBAC integration
- Environment-specific identities

### Audit and Monitoring
- All secret access logged in Key Vault
- Azure Monitor integration
- Kubernetes audit logs

## 🔧 Configuration

### SecretProviderClass Parameters

```yaml
spec:
  provider: azure
  parameters:
    usePodIdentity: "false"
    useVMManagedIdentity: "true"
    userAssignedIdentityID: ""
    keyvaultName: "orca-keyvault-dev"
    tenantId: "your-tenant-id"
    objects: |
      array:
        - |
          objectName: azure-openai-api-key
          objectType: secret
          objectVersion: ""
```

### Environment Variables

The CSI driver automatically creates Kubernetes secrets that can be referenced as environment variables:

```yaml
env:
- name: AZURE_OPENAI_API_KEY
  valueFrom:
    secretKeyRef:
      name: orca-secrets
      key: AZURE_OPENAI_API_KEY
      optional: true
```

## 🚨 Troubleshooting

### Common Issues

1. **CSI Driver Pods Not Running**
   ```bash
   kubectl get pods -n kube-system | grep secrets-store-csi-driver
   kubectl describe pod -n kube-system <pod-name>
   ```

2. **SecretProviderClass Not Created**
   ```bash
   kubectl get secretproviderclass -n orca-core
   kubectl describe secretproviderclass -n orca-core orca-keyvault-secrets
   ```

3. **Azure Identity Not Created**
   ```bash
   kubectl get azureidentity -n orca-core
   kubectl describe azureidentity -n orca-core orca-keyvault-identity
   ```

4. **Key Vault Access Denied**
   ```bash
   # Check role assignments
   az role assignment list --assignee <principal-id>

   # Check Key Vault access policies
   az keyvault show --name orca-keyvault-dev
   ```

5. **Secrets Not Mounted**
   ```bash
   # Check pod events
   kubectl describe pod -n orca-core <pod-name>

   # Check CSI driver logs
   kubectl logs -n kube-system -l app=secrets-store-csi-driver
   ```

### Debug Commands

```bash
# Check all CSI driver resources
kubectl get all -n kube-system | grep secrets-store

# Check SecretProviderClass status
kubectl get secretproviderclass -n orca-core -o yaml

# Check Azure Identity status
kubectl get azureidentity -n orca-core -o yaml

# Check pod volume mounts
kubectl describe pod -n orca-core <pod-name> | grep -A 10 "Mounts:"
```

## 📚 Additional Resources

- [Azure Key Vault CSI Driver Documentation](https://docs.microsoft.com/en-us/azure/aks/csi-secrets-store-driver)
- [Azure Key Vault Documentation](https://docs.microsoft.com/en-us/azure/key-vault/)
- [Kubernetes CSI Documentation](https://kubernetes-csi.github.io/docs/)
- [Azure Managed Identity Documentation](https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/)

## 🔄 Maintenance

### Updating Secrets

Secrets can be updated in Azure Key Vault without restarting pods:

1. Update secret in Azure Key Vault
2. Restart pods to pick up new secret values:
   ```bash
   kubectl rollout restart deployment/orca-core-api -n orca-core
   ```

### Rotating Credentials

1. Create new secret in Azure Key Vault
2. Update SecretProviderClass to reference new secret version
3. Apply updated manifest
4. Restart pods

### Monitoring

- Monitor Key Vault access logs
- Set up alerts for failed secret access
- Monitor CSI driver pod health
- Track secret rotation events
