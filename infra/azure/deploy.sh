#!/bin/bash
# Azure deployment script for Orca Core Phase 2

set -e

# Configuration
RESOURCE_GROUP="orcacore-rg"
ACR_NAME="orcaregistry"
AKS_NAME="orca-aks"
KEYVAULT_NAME="orca-kv"
ML_WORKSPACE="orca-ml-workspace"
LOCATION="eastus"

echo "🚀 Deploying Orca Core Phase 2 to Azure..."

# Check if logged in to Azure
if ! az account show &> /dev/null; then
    echo "❌ Please login to Azure first: az login"
    exit 1
fi

# Create resource group if it doesn't exist
echo "📦 Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Azure Container Registry
echo "🐳 Creating Azure Container Registry..."
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Basic \
    --admin-enabled true

# Get ACR login server
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query loginServer --output tsv)
echo "📋 ACR Login Server: $ACR_LOGIN_SERVER"

# Build and push Docker image
echo "🔨 Building and pushing Docker image..."
az acr build --registry $ACR_NAME --image orca-core:latest .

# Create Azure Kubernetes Service
echo "☸️ Creating Azure Kubernetes Service..."
az aks create \
    --resource-group $RESOURCE_GROUP \
    --name $AKS_NAME \
    --node-count 2 \
    --node-vm-size Standard_B2s \
    --attach-acr $ACR_NAME \
    --generate-ssh-keys

# Get AKS credentials
echo "🔑 Getting AKS credentials..."
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_NAME

# Create Azure Key Vault
echo "🔐 Creating Azure Key Vault..."
az keyvault create \
    --name $KEYVAULT_NAME \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION

# Store secrets in Key Vault
echo "🔑 Storing secrets in Key Vault..."
# Note: Replace with actual values
az keyvault secret set --vault-name $KEYVAULT_NAME --name "azure-openai-api-key" --value "your-openai-api-key"
az keyvault secret set --vault-name $KEYVAULT_NAME --name "azure-openai-endpoint" --value "https://orca-openai.openai.azure.com/"

# Create Kubernetes namespace
echo "📁 Creating Kubernetes namespace..."
kubectl create namespace orca-core

# Create Kubernetes secrets
echo "🔐 Creating Kubernetes secrets..."
kubectl create secret generic orca-secrets \
    --from-literal=azure-openai-endpoint="https://orca-openai.openai.azure.com/" \
    --from-literal=azure-openai-api-key="your-openai-api-key" \
    --namespace=orca-core

# Deploy application
echo "🚀 Deploying application to Kubernetes..."
kubectl apply -f infra/azure/k8s/ -n orca-core

# Wait for deployment
echo "⏳ Waiting for deployment to complete..."
kubectl wait --for=condition=available --timeout=300s deployment/orca-core -n orca-core

# Get service URL
echo "🌐 Getting service URL..."
kubectl get service orca-core -n orca-core

echo "✅ Deployment completed successfully!"
echo "🔗 Access your application at the external IP shown above"
