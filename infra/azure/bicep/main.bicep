// Orca Core Azure Infrastructure - Main Bicep Template
// This template deploys the complete Azure infrastructure for Orca Core

@description('The name of the resource group')
param resourceGroupName string = 'orcacore-rg'

@description('The location for all resources')
param location string = resourceGroup().location

@description('Environment name (dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('Azure OpenAI service name')
param openaiServiceName string = 'orca-openai'

@description('Azure ML workspace name')
param mlWorkspaceName string = 'orca-ml-workspace'

@description('Azure Container Registry name')
param acrName string = 'orcacoreacr'

@description('Azure Kubernetes Service cluster name')
param aksName string = 'orca-aks'

@description('Azure Key Vault name')
param keyVaultName string = 'orca-keyvault'

@description('Application Insights name')
param appInsightsName string = 'orca-appinsights'

@description('Storage account name for ML data')
param storageAccountName string = 'orcacorestorage'

@description('Tags to apply to all resources')
param tags object = {
  Project: 'OrcaCore'
  Environment: environment
  ManagedBy: 'Bicep'
}

// Variables
var resourcePrefix = 'orca-${environment}'
var timestamp = utcNow('yyyyMMddHHmmss')

// Resource Group (assumes it exists)
resource resourceGroup 'Microsoft.Resources/resourceGroups@2023-07-01' existing = {
  name: resourceGroupName
}

// Azure OpenAI Service
resource openaiService 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: openaiServiceName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: openaiServiceName
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
  tags: tags
}

// Azure ML Workspace
resource mlWorkspace 'Microsoft.MachineLearningServices/workspaces@2023-04-01' = {
  name: mlWorkspaceName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: 'Orca Core ML Workspace'
    description: 'Machine Learning workspace for Orca Core decision engine'
    storageAccount: storageAccount.id
    keyVault: keyVault.id
    applicationInsights: appInsights.id
    containerRegistry: acr.id
  }
  tags: tags
}

// Storage Account for ML data
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
  tags: tags
}

// Azure Container Registry
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
    publicNetworkAccess: 'Enabled'
  }
  tags: tags
}

// Azure Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: mlWorkspace.identity.principalId
        permissions: {
          keys: ['all']
          secrets: ['all']
          certificates: ['all']
        }
      }
    ]
    enabledForDeployment: true
    enabledForDiskEncryption: true
    enabledForTemplateDeployment: true
    enableRbacAuthorization: false
    publicNetworkAccess: 'Enabled'
  }
  tags: tags
}

// Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    IngestionMode: 'LogAnalytics'
  }
  tags: tags
}

// Log Analytics Workspace
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${resourcePrefix}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
  tags: tags
}

// Azure Kubernetes Service
resource aks 'Microsoft.ContainerService/managedClusters@2023-10-01' = {
  name: aksName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    kubernetesVersion: '1.28'
    dnsPrefix: aksName
    agentPoolProfiles: [
      {
        name: 'system'
        count: 2
        vmSize: 'Standard_D2s_v3'
        osType: 'Linux'
        mode: 'System'
        enableAutoScaling: true
        minCount: 1
        maxCount: 3
      }
      {
        name: 'user'
        count: 1
        vmSize: 'Standard_D4s_v3'
        osType: 'Linux'
        mode: 'User'
        enableAutoScaling: true
        minCount: 1
        maxCount: 5
      }
    ]
    networkProfile: {
      networkPlugin: 'azure'
      serviceCidr: '10.0.0.0/16'
      dnsServiceIP: '10.0.0.10'
    }
    addonProfiles: {
      httpApplicationRouting: {
        enabled: false
      }
      monitoring: {
        enabled: true
        config: {
          logAnalyticsWorkspaceResourceID: logAnalyticsWorkspace.id
        }
      }
    }
  }
  tags: tags
}

// AKS Node Pool for ML workloads
resource mlNodePool 'Microsoft.ContainerService/managedClusters/agentPools@2023-10-01' = {
  parent: aks
  name: 'ml'
  properties: {
    count: 1
    vmSize: 'Standard_NC6s_v3' // GPU-enabled for ML workloads
    osType: 'Linux'
    mode: 'User'
    enableAutoScaling: true
    minCount: 0
    maxCount: 3
    nodeLabels: {
      workload: 'ml'
      gpu: 'true'
    }
    nodeTaints: [
      'gpu=true:NoSchedule'
    ]
  }
}

// Role assignments for AKS to access other resources
resource aksAcrRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aks.id, acr.id, 'AcrPull')
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: aks.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource aksKeyVaultRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aks.id, keyVault.id, 'KeyVaultSecretsUser')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
    principalId: aks.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output resourceGroupName string = resourceGroupName
output location string = location
output environment string = environment

output openaiServiceName string = openaiService.name
output openaiEndpoint string = openaiService.properties.endpoint
output openaiKey string = openaiService.listKeys().key1

output mlWorkspaceName string = mlWorkspace.name
output mlWorkspaceId string = mlWorkspace.id

output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
output acrUsername string = acr.listCredentials().username
output acrPassword string = acr.listCredentials().passwords[0].value

output aksName string = aks.name
output aksResourceGroup string = resourceGroupName
output aksClusterId string = aks.id

output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri

output appInsightsName string = appInsights.name
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
output appInsightsConnectionString string = appInsights.properties.ConnectionString

output storageAccountName string = storageAccount.name
output storageAccountKey string = storageAccount.listKeys().keys[0].value
