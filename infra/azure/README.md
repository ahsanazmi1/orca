# Orca Core Azure Infrastructure

This directory contains the complete Azure infrastructure setup for Orca Core, including Bicep templates, Terraform configurations, and deployment scripts.

## 📁 Directory Structure

```
infra/azure/
├── bicep/                    # Bicep templates for Azure resources
│   ├── main.bicep           # Main infrastructure template
│   ├── keyvault-secrets.bicep # Key Vault secrets management
│   └── kubernetes.bicep     # Kubernetes resources template
├── terraform/               # Terraform configurations (alternative)
│   ├── main.tf             # Main Terraform configuration
│   ├── variables.tf        # Variable definitions
│   ├── outputs.tf          # Output definitions
│   └── terraform.tfvars.example # Example variables file
├── scripts/                 # Deployment and management scripts
│   ├── bootstrap.sh        # Infrastructure bootstrap script
│   ├── deploy.sh           # Application deployment script
│   ├── cleanup.sh          # Infrastructure cleanup script
│   └── keyvault-secrets.sh # Key Vault secrets management
├── params/                  # Parameter files for different environments
│   ├── dev.json            # Development environment parameters
│   ├── staging.json        # Staging environment parameters
│   └── prod.json           # Production environment parameters
└── README.md               # This file
```

## 🚀 Quick Start

### Prerequisites

1. **Azure CLI** installed and logged in:
   ```bash
   az login
   az account set --subscription "your-subscription-id"
   ```

2. **Environment Configuration**:
   ```bash
   make configure-azure-openai
   ```

3. **Required Tools** (for Bicep):
   ```bash
   az bicep install
   ```

4. **Required Tools** (for Terraform):
   ```bash
   # Install Terraform from https://www.terraform.io/downloads.html
   terraform --version
   ```

### Deploy Infrastructure

#### Option 1: Using Bicep (Recommended)

```bash
# Deploy development environment
./infra/azure/scripts/bootstrap.sh

# Deploy staging environment
./infra/azure/scripts/bootstrap.sh -e staging -l "West US 2"

# Deploy production environment
./infra/azure/scripts/bootstrap.sh -e prod -l "East US"
```

#### Option 2: Using Terraform

```bash
# Deploy development environment
./infra/azure/scripts/bootstrap.sh -m terraform

# Deploy staging environment
./infra/azure/scripts/bootstrap.sh -e staging -m terraform
```

### Deploy Application

```bash
# Deploy to development
./infra/azure/scripts/deploy.sh

# Deploy to staging with specific tag
./infra/azure/scripts/deploy.sh -e staging -t v1.0.0

# Dry run deployment
./infra/azure/scripts/deploy.sh --dry-run
```

## 🏗️ Infrastructure Components

### Core Services

- **Azure OpenAI**: GPT-4o-mini deployment for LLM explanations
- **Azure ML Workspace**: Machine learning model training and deployment
- **Azure Container Registry (ACR)**: Docker image storage
- **Azure Kubernetes Service (AKS)**: Container orchestration
- **Azure Key Vault**: Secrets and configuration management
- **Application Insights**: Application monitoring and logging
- **Storage Account**: ML data and model artifacts storage

### Network and Security

- **Resource Group**: Isolated environment for all resources
- **Key Vault Access Policies**: Secure access to secrets
- **AKS RBAC**: Role-based access control for Kubernetes
- **Network Policies**: Secure network communication
- **Managed Identities**: Secure service-to-service authentication

### Monitoring and Observability

- **Application Insights**: Application performance monitoring
- **Log Analytics Workspace**: Centralized logging
- **Azure Monitor**: Infrastructure monitoring
- **Health Checks**: Application health monitoring

## 🔧 Configuration

### Environment Variables

The infrastructure uses environment variables from `.env.local`:

```bash
# Azure Configuration
AZURE_SUBSCRIPTION_ID="your-subscription-id"
AZURE_TENANT_ID="your-tenant-id"
AZURE_RESOURCE_GROUP="orcacore-rg"
AZURE_LOCATION="East US"

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT="https://your-openai.openai.azure.com/"
AZURE_OPENAI_API_KEY="your-api-key"
AZURE_OPENAI_DEPLOYMENT="gpt-4o-mini"

# Orca Core Configuration
ORCA_ENVIRONMENT="dev"
ORCA_DECISION_MODE="RULES_PLUS_AI"
ORCA_USE_XGB="true"
ORCA_EXPLAIN_ENABLED="true"
```

### Parameter Files

Environment-specific parameters are defined in JSON files:

- `params/dev.json`: Development environment
- `params/staging.json`: Staging environment
- `params/prod.json`: Production environment

## 📋 Deployment Scripts

### Bootstrap Script (`bootstrap.sh`)

Deploys the complete Azure infrastructure:

```bash
# Basic usage
./infra/azure/scripts/bootstrap.sh

# With options
./infra/azure/scripts/bootstrap.sh -e staging -l "West US 2" -m terraform

# Help
./infra/azure/scripts/bootstrap.sh --help
```

**Features:**
- Prerequisites validation
- Environment variable loading
- Resource group creation
- Infrastructure deployment (Bicep or Terraform)
- kubectl configuration
- Deployment summary

### Deploy Script (`deploy.sh`)

Deploys the Orca Core application to AKS:

```bash
# Basic usage
./infra/azure/scripts/deploy.sh

# With options
./infra/azure/scripts/deploy.sh -e staging -t v1.0.0 --skip-build

# Help
./infra/azure/scripts/deploy.sh --help
```

**Features:**
- Docker image building and pushing
- Kubernetes namespace creation
- Secrets management
- Application deployment
- Health checks
- Status monitoring

### Cleanup Script (`cleanup.sh`)

Removes Azure infrastructure:

```bash
# Basic usage (with confirmation)
./infra/azure/scripts/cleanup.sh

# Without confirmation
./infra/azure/scripts/cleanup.sh --no-confirm

# Dry run
./infra/azure/scripts/cleanup.sh --dry-run

# Help
./infra/azure/scripts/cleanup.sh --help
```

**Features:**
- Kubernetes resource cleanup
- Azure resource deletion
- Local file cleanup
- Confirmation prompts
- Dry run mode

### Key Vault Secrets Script (`keyvault-secrets.sh`)

Manages secrets in Azure Key Vault:

```bash
# Set secrets from environment
./infra/azure/scripts/keyvault-secrets.sh set

# Get secrets
./infra/azure/scripts/keyvault-secrets.sh get

# Delete secrets
./infra/azure/scripts/keyvault-secrets.sh delete

# Backup secrets
./infra/azure/scripts/keyvault-secrets.sh backup

# Restore from backup
./infra/azure/scripts/keyvault-secrets.sh restore -f backup.json

# Help
./infra/azure/scripts/keyvault-secrets.sh --help
```

## 🔐 Security

### Key Vault Integration

All sensitive configuration is stored in Azure Key Vault:

- **Azure OpenAI API Key**: Secure API access
- **Azure OpenAI Endpoint**: Service endpoint
- **Azure OpenAI Deployment**: Model deployment name
- **ACR Credentials**: Container registry access
- **Storage Account Keys**: Data access
- **Application Insights Connection String**: Monitoring access

### Access Control

- **RBAC**: Role-based access control for all resources
- **Managed Identities**: Secure service-to-service authentication
- **Network Policies**: Restricted network access
- **Key Vault Access Policies**: Granular secret access control

### Best Practices

- **Least Privilege**: Minimal required permissions
- **Secret Rotation**: Regular secret updates
- **Audit Logging**: All access logged
- **Encryption**: Data encrypted at rest and in transit

## 📊 Monitoring

### Application Insights

- **Performance Monitoring**: Response times, throughput
- **Error Tracking**: Exception monitoring and alerting
- **Custom Metrics**: Business-specific metrics
- **Distributed Tracing**: Request flow tracking

### Log Analytics

- **Centralized Logging**: All application and infrastructure logs
- **Query and Analysis**: KQL queries for log analysis
- **Alerting**: Automated alerts for critical issues
- **Dashboards**: Visual monitoring dashboards

### Health Checks

- **Liveness Probes**: Application health monitoring
- **Readiness Probes**: Service availability checks
- **Startup Probes**: Application startup monitoring

## 🚨 Troubleshooting

### Common Issues

1. **Azure CLI Not Logged In**:
   ```bash
   az login
   az account set --subscription "your-subscription-id"
   ```

2. **Resource Group Not Found**:
   ```bash
   # Create resource group first
   az group create --name "orcacore-rg" --location "East US"
   ```

3. **Key Vault Access Denied**:
   ```bash
   # Check access policies
   az keyvault show --name "orca-keyvault-dev"
   ```

4. **AKS Cluster Not Accessible**:
   ```bash
   # Get credentials
   az aks get-credentials --resource-group "orcacore-rg" --name "orca-aks-dev"
   ```

5. **Docker Build Fails**:
   ```bash
   # Check ACR login
   az acr login --name "orcacoreacrdev"
   ```

### Debug Commands

```bash
# Check Azure resources
az resource list --resource-group "orcacore-rg"

# Check AKS cluster status
az aks show --resource-group "orcacore-rg" --name "orca-aks-dev"

# Check Key Vault secrets
az keyvault secret list --vault-name "orca-keyvault-dev"

# Check Kubernetes resources
kubectl get all --namespace "orca-core"

# Check application logs
kubectl logs -f deployment/orca-core-api --namespace "orca-core"
```

## 📚 Additional Resources

- [Azure Bicep Documentation](https://docs.microsoft.com/en-us/azure/azure-resource-manager/bicep/)
- [Azure Terraform Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Azure Kubernetes Service](https://docs.microsoft.com/en-us/azure/aks/)
- [Azure Key Vault](https://docs.microsoft.com/en-us/azure/key-vault/)
- [Azure OpenAI Service](https://docs.microsoft.com/en-us/azure/cognitive-services/openai/)

## 🤝 Support

For issues or questions:

1. Check the troubleshooting section above
2. Review Azure resource logs and metrics
3. Check the main project README for general setup
4. Run the debug UI for application testing: `make debug-ui`


