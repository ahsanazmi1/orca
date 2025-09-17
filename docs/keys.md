# Keys & Secrets Management

This document describes how to manage cryptographic keys, model artifacts, and Azure credentials for the Orca Core decision engine across different environments.

## Overview

The Orca Core system uses three main types of secrets:

1. **Cryptographic Keys**: For decision signing and verifiable credentials
2. **Model Artifacts**: ML model files and metadata
3. **Azure Credentials**: OpenAI API keys and cloud service credentials

## Environment Configuration

### Local Development

Copy `.env.example` to `.env` and configure for your local environment:

```bash
cp .env.example .env
# Edit .env with your local configuration
```

**Never commit `.env` files to version control.**

### Production Deployment

Use Azure Key Vault and environment-specific configuration:

```bash
# Production environment variables
export ORCA_KEY_VAULT_URI="https://your-keyvault.vault.azure.net/"
export ORCA_SIGN_DECISIONS="true"
export ORCA_USE_XGB="true"
```

## 1. Cryptographic Keys

### Local Development

#### Generate Test Keys

Use the provided script to generate test keys for local development:

```bash
python scripts/generate_test_keys.py
```

This creates:
- `keys/test_signing_key.pem` - Ed25519 private key for signing
- `keys/test_public_key.pem` - Corresponding public key
- `keys/test_key_info.json` - Key metadata and fingerprints

#### Test Key Usage

```bash
# Enable signing with test keys
export ORCA_SIGN_DECISIONS="true"
export ORCA_SIGNING_KEY_PATH="./keys/test_signing_key.pem"
export ORCA_RECEIPT_HASH_ONLY="false"
```

#### Key Storage Best Practices

- **Never commit real keys** to version control
- Store test keys in `keys/` directory (gitignored)
- Use different keys for each developer
- Rotate test keys regularly
- Document key generation process

### Production Deployment

#### Azure Key Vault Integration

For production, use Azure Key Vault for secure key management:

```bash
# Configure Azure Key Vault
export ORCA_KEY_VAULT_URI="https://your-keyvault.vault.azure.net/"
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
```

#### Key Vault Setup

1. **Create Key Vault**:
   ```bash
   az keyvault create \
     --name "your-keyvault" \
     --resource-group "your-rg" \
     --location "eastus"
   ```

2. **Store Signing Key**:
   ```bash
   az keyvault secret set \
     --vault-name "your-keyvault" \
     --name "signing-key" \
     --file "keys/production_signing_key.pem"
   ```

3. **Configure Access Policies**:
   ```bash
   az keyvault set-policy \
     --name "your-keyvault" \
     --spn "your-service-principal" \
     --secret-permissions get list
   ```

#### Production Key Management

- Use Azure Key Vault for all production keys
- Implement key rotation policies
- Use managed identities where possible
- Monitor key access and usage
- Implement audit logging

## 2. Model Artifacts

### Local Development

#### Model Directory Structure

```
models/xgb/
├── 1.0.0/
│   ├── model.json          # XGBoost model
│   ├── calibrator.pkl      # Calibrated classifier
│   ├── scaler.pkl          # Feature scaler
│   ├── feature_spec.json   # Feature specification
│   └── metadata.json       # Model metadata
└── 1.1.0/                  # New version
    └── ...
```

#### Local Model Configuration

```bash
# Use local model directory
export ORCA_MODEL_DIR="./models/xgb"
export ORCA_USE_XGB="true"
export ORCA_ENABLE_SHAP="true"
```

#### Model Generation

Generate model artifacts for local development:

```bash
python scripts/create_model_artifacts.py
```

### Production Deployment

#### Azure Kubernetes Service (AKS) Model Mounting

For production AKS deployment, mount model artifacts as persistent volumes:

#### 1. Create Azure File Share

```bash
# Create storage account
az storage account create \
  --name "yourstorageaccount" \
  --resource-group "your-rg" \
  --location "eastus" \
  --sku "Standard_LRS"

# Create file share
az storage share create \
  --name "orca-models" \
  --account-name "yourstorageaccount"
```

#### 2. Create Kubernetes Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: azure-storage-secret
type: Opaque
data:
  azurestorageaccountname: <base64-encoded-storage-account-name>
  azurestorageaccountkey: <base64-encoded-storage-account-key>
```

#### 3. Create Persistent Volume

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: orca-models-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  azureFile:
    secretName: azure-storage-secret
    shareName: orca-models
    readOnly: false
```

#### 4. Create Persistent Volume Claim

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: orca-models-pvc
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 10Gi
  volumeName: orca-models-pv
```

#### 5. Mount in Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orca-core
spec:
  template:
    spec:
      containers:
      - name: orca-core
        image: orca-core:latest
        env:
        - name: ORCA_MODEL_DIR
          value: "/models"
        volumeMounts:
        - name: models-volume
          mountPath: /models
      volumes:
      - name: models-volume
        persistentVolumeClaim:
          claimName: orca-models-pvc
```

#### Model Versioning in Production

- Use semantic versioning for model artifacts
- Implement model rollback capabilities
- Monitor model performance and drift
- Implement A/B testing for model versions
- Use feature flags for model deployment

## 3. Azure Credentials

### Azure OpenAI Integration

#### Local Development

```bash
# Azure OpenAI configuration
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_API_KEY="your-api-key"
export AZURE_OPENAI_DEPLOYMENT="gpt-4o-mini"
export AZURE_OPENAI_API_VERSION="2024-02-15-preview"
```

#### Production Deployment

Use Azure Key Vault for OpenAI credentials:

```bash
# Store OpenAI API key in Key Vault
az keyvault secret set \
  --vault-name "your-keyvault" \
  --name "openai-api-key" \
  --value "your-api-key"
```

#### Service Principal Configuration

```bash
# Azure service principal
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_RESOURCE_GROUP="your-resource-group"
export AZURE_LOCATION="eastus"
```

### Azure Resource Management

#### Create Service Principal

```bash
# Create service principal
az ad sp create-for-rbac \
  --name "orca-core-sp" \
  --role "Contributor" \
  --scopes "/subscriptions/your-subscription-id"
```

#### Assign Key Vault Permissions

```bash
# Grant Key Vault access
az keyvault set-policy \
  --name "your-keyvault" \
  --spn "your-client-id" \
  --secret-permissions get list
```

## Security Best Practices

### Development Environment

1. **Never commit secrets** to version control
2. **Use test keys** for local development
3. **Rotate test keys** regularly
4. **Document key generation** process
5. **Use environment variables** for configuration
6. **Implement secret scanning** in CI/CD

### Production Environment

1. **Use Azure Key Vault** for all secrets
2. **Implement least privilege** access
3. **Enable audit logging** for all secret access
4. **Use managed identities** where possible
5. **Implement key rotation** policies
6. **Monitor secret usage** and access patterns
7. **Use network security groups** to restrict access
8. **Implement multi-factor authentication** for admin access

### Key Rotation

#### Automated Key Rotation

Implement automated key rotation for production:

```bash
# Rotate signing keys monthly
az keyvault secret set \
  --vault-name "your-keyvault" \
  --name "signing-key-$(date +%Y%m)" \
  --file "keys/new_signing_key.pem"
```

#### Model Artifact Updates

```bash
# Update model artifacts
az storage file upload-batch \
  --source "models/xgb/1.1.0" \
  --destination "orca-models/1.1.0" \
  --account-name "yourstorageaccount"
```

## Troubleshooting

### Common Issues

#### 1. Key Not Found

```bash
# Check key file exists
ls -la keys/test_signing_key.pem

# Verify key permissions
chmod 600 keys/test_signing_key.pem
```

#### 2. Model Loading Failed

```bash
# Check model directory
ls -la models/xgb/1.0.0/

# Verify model files
python -c "import joblib; print(joblib.load('models/xgb/1.0.0/calibrator.pkl'))"
```

#### 3. Azure Authentication Failed

```bash
# Login to Azure
az login

# Verify service principal
az ad sp show --id "your-client-id"
```

#### 4. Key Vault Access Denied

```bash
# Check Key Vault permissions
az keyvault show --name "your-keyvault"

# Verify access policy
az keyvault show-policy --name "your-keyvault"
```

### Debug Mode

Enable debug mode for troubleshooting:

```bash
export ORCA_DEBUG="true"
export ORCA_LOG_LEVEL="DEBUG"
export ORCA_VERBOSE="true"
```

## Migration Guide

### From Local to Production

1. **Export local configuration**:
   ```bash
   env | grep ORCA_ > local-config.env
   ```

2. **Create production Key Vault**:
   ```bash
   az keyvault create --name "your-keyvault" --resource-group "your-rg"
   ```

3. **Migrate secrets**:
   ```bash
   # Upload signing key
   az keyvault secret set --vault-name "your-keyvault" --name "signing-key" --file "keys/test_signing_key.pem"

   # Upload OpenAI API key
   az keyvault secret set --vault-name "your-keyvault" --name "openai-api-key" --value "your-api-key"
   ```

4. **Update environment variables**:
   ```bash
   export ORCA_KEY_VAULT_URI="https://your-keyvault.vault.azure.net/"
   export ORCA_SIGN_DECISIONS="true"
   ```

5. **Deploy to AKS** with mounted model artifacts

## Compliance & Audit

### Audit Logging

Enable audit logging for all secret access:

```bash
# Enable Key Vault logging
az monitor diagnostic-settings create \
  --name "keyvault-audit" \
  --resource "your-keyvault" \
  --logs '[{"category": "AuditEvent", "enabled": true}]'
```

### Compliance Requirements

- **SOC 2**: Implement access controls and audit logging
- **GDPR**: Ensure data encryption and access controls
- **HIPAA**: Use Azure Key Vault with HSM-backed keys
- **PCI DSS**: Implement key rotation and access monitoring

## Support

For questions or issues with key management:

1. Check this documentation
2. Review the troubleshooting section
3. Check Azure Key Vault logs
4. Contact the Orca Core team
5. Create an issue in the repository

## Changelog

### v0.1.0 (Initial Release)
- ✅ Local development key generation
- ✅ Azure Key Vault integration
- ✅ Model artifact mounting for AKS
- ✅ Azure OpenAI configuration
- ✅ Security best practices documentation
- ✅ Troubleshooting guide
