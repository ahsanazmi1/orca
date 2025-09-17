// Key Vault Secrets Management for Orca Core
// This template manages secrets in Azure Key Vault

@description('The name of the Key Vault')
param keyVaultName string

@description('Azure OpenAI API Key')
@secure()
param azureOpenaiApiKey string

@description('Azure OpenAI Endpoint')
param azureOpenaiEndpoint string

@description('Azure OpenAI Deployment Name')
param azureOpenaiDeployment string = 'gpt-4o-mini'

@description('Azure ML Workspace Key')
@secure()
param azureMlWorkspaceKey string

@description('Azure ML Workspace Endpoint')
param azureMlWorkspaceEndpoint string

@description('ACR Username')
param acrUsername string

@description('ACR Password')
@secure()
param acrPassword string

@description('Storage Account Key')
@secure()
param storageAccountKey string

@description('Application Insights Connection String')
@secure()
param appInsightsConnectionString string

@description('Environment name')
param environment string = 'dev'

// Key Vault reference
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

// Azure OpenAI Secrets
resource azureOpenaiApiKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'azure-openai-api-key'
  properties: {
    value: azureOpenaiApiKey
    contentType: 'text/plain'
    attributes: {
      enabled: true
    }
  }
}

resource azureOpenaiEndpointSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'azure-openai-endpoint'
  properties: {
    value: azureOpenaiEndpoint
    contentType: 'text/plain'
    attributes: {
      enabled: true
    }
  }
}

resource azureOpenaiDeploymentSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'azure-openai-deployment'
  properties: {
    value: azureOpenaiDeployment
    contentType: 'text/plain'
    attributes: {
      enabled: true
    }
  }
}

// Azure ML Secrets
resource azureMlWorkspaceKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'azure-ml-workspace-key'
  properties: {
    value: azureMlWorkspaceKey
    contentType: 'text/plain'
    attributes: {
      enabled: true
    }
  }
}

resource azureMlWorkspaceEndpointSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'azure-ml-workspace-endpoint'
  properties: {
    value: azureMlWorkspaceEndpoint
    contentType: 'text/plain'
    attributes: {
      enabled: true
    }
  }
}

// Container Registry Secrets
resource acrUsernameSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'acr-username'
  properties: {
    value: acrUsername
    contentType: 'text/plain'
    attributes: {
      enabled: true
    }
  }
}

resource acrPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'acr-password'
  properties: {
    value: acrPassword
    contentType: 'text/plain'
    attributes: {
      enabled: true
    }
  }
}

// Storage Account Secret
resource storageAccountKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'storage-account-key'
  properties: {
    value: storageAccountKey
    contentType: 'text/plain'
    attributes: {
      enabled: true
    }
  }
}

// Application Insights Secret
resource appInsightsConnectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'app-insights-connection-string'
  properties: {
    value: appInsightsConnectionString
    contentType: 'text/plain'
    attributes: {
      enabled: true
    }
  }
}

// Environment-specific secrets
resource environmentSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'environment'
  properties: {
    value: environment
    contentType: 'text/plain'
    attributes: {
      enabled: true
    }
  }
}

// Orca Core specific secrets
resource orcaDecisionModeSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'orca-decision-mode'
  properties: {
    value: 'RULES_PLUS_AI'
    contentType: 'text/plain'
    attributes: {
      enabled: true
    }
  }
}

resource orcaUseXgbSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'orca-use-xgb'
  properties: {
    value: 'true'
    contentType: 'text/plain'
    attributes: {
      enabled: true
    }
  }
}

resource orcaExplainEnabledSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'orca-explain-enabled'
  properties: {
    value: 'true'
    contentType: 'text/plain'
    attributes: {
      enabled: true
    }
  }
}

// Outputs
output keyVaultName string = keyVaultName
output keyVaultUri string = keyVault.properties.vaultUri


