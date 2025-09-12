// Azure Bicep template for Orca Core infrastructure
// This is a placeholder template for AKS, ACR, Key Vault, and Resource Group

@description('The name of the resource group')
param resourceGroupName string = 'rg-orca-core-${uniqueString(resourceGroup().id)}'

@description('The location for all resources')
param location string = resourceGroup().location

@description('The environment (dev, staging, prod)')
param environment string = 'dev'

@description('The application name')
param appName string = 'orca-core'

// Resource Group
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName
  location: location
  tags: {
    Environment: environment
    Application: appName
    ManagedBy: 'Bicep'
  }
}

// Container Registry
resource acr 'Microsoft.ContainerRegistry/registries@2021-09-01' = {
  name: 'acr${appName}${environment}${uniqueString(resourceGroup().id)}'
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
  tags: {
    Environment: environment
    Application: appName
  }
}

// Key Vault
resource kv 'Microsoft.KeyVault/vaults@2021-10-01' = {
  name: 'kv-${appName}-${environment}-${uniqueString(resourceGroup().id)}'
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    accessPolicies: []
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
  }
  tags: {
    Environment: environment
    Application: appName
  }
}

// AKS Cluster
resource aks 'Microsoft.ContainerService/managedClusters@2022-05-02-preview' = {
  name: 'aks-${appName}-${environment}'
  location: location
  properties: {
    kubernetesVersion: '1.28'
    dnsPrefix: 'aks-${appName}-${environment}'
    agentPoolProfiles: [
      {
        name: 'systempool'
        count: 2
        vmSize: 'Standard_D2s_v3'
        osType: 'Linux'
        mode: 'System'
        enableAutoScaling: true
        minCount: 1
        maxCount: 3
      }
      {
        name: 'userpool'
        count: 1
        vmSize: 'Standard_D4s_v3'
        osType: 'Linux'
        mode: 'User'
        enableAutoScaling: true
        minCount: 1
        maxCount: 5
      }
    ]
    servicePrincipalProfile: {
      clientId: 'TODO: Replace with service principal client ID'
      secret: 'TODO: Replace with service principal secret'
    }
    addonProfiles: {
      httpApplicationRouting: {
        enabled: false
      }
      kubeDashboard: {
        enabled: false
      }
      azurePolicy: {
        enabled: true
      }
    }
    networkProfile: {
      networkPlugin: 'azure'
      serviceCidr: '10.0.0.0/16'
      dnsServiceIP: '10.0.0.10'
    }
  }
  tags: {
    Environment: environment
    Application: appName
  }
}

// Outputs
output resourceGroupName string = rg.name
output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
output keyVaultName string = kv.name
output keyVaultUri string = kv.properties.vaultUri
output aksName string = aks.name
output aksFqdn string = aks.properties.fqdn
