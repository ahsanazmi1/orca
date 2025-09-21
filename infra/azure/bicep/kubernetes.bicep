// Kubernetes Resources for Orca Core
// This template deploys Kubernetes manifests for Orca Core

@description('The name of the AKS cluster')
param aksName string

@description('The resource group name')
param resourceGroupName string

@description('The namespace for Orca Core')
param namespace string = 'orca-core'

@description('The image tag for Orca Core')
param imageTag string = 'latest'

@description('The ACR login server')
param acrLoginServer string

@description('The Key Vault URI')
param keyVaultUri string

@description('The Application Insights connection string')
@secure()
param appInsightsConnectionString string

@description('Environment name')
param environment string = 'dev'

// AKS cluster reference
resource aks 'Microsoft.ContainerService/managedClusters@2023-10-01' existing = {
  name: aksName
  scope: resourceGroup(resourceGroupName)
}

// Kubernetes Namespace
resource namespace 'Microsoft.ContainerService/managedClusters/agentPools@2023-10-01' = {
  parent: aks
  name: 'namespace'
  properties: {
    count: 0
    vmSize: 'Standard_D2s_v3'
    osType: 'Linux'
    mode: 'User'
  }
}

// Note: The actual Kubernetes resources (Deployment, Service, ConfigMap, etc.)
// would be deployed using kubectl or Helm after the infrastructure is provisioned.
// This Bicep template focuses on the Azure infrastructure components.

// Outputs for Kubernetes deployment
output aksName string = aksName
output resourceGroupName string = resourceGroupName
output namespace string = namespace
output imageTag string = imageTag
output acrLoginServer string = acrLoginServer
output keyVaultUri string = keyVaultUri
