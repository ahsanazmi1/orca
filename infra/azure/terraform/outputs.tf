# Outputs for Orca Core Azure Infrastructure

output "resource_group_name" {
  description = "The name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "location" {
  description = "The location of the resources"
  value       = azurerm_resource_group.main.location
}

output "environment" {
  description = "The environment name"
  value       = var.environment
}

# Azure OpenAI outputs
output "openai_service_name" {
  description = "The name of the Azure OpenAI service"
  value       = azurerm_cognitive_account.openai.name
}

output "openai_endpoint" {
  description = "The endpoint of the Azure OpenAI service"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "openai_key" {
  description = "The primary key of the Azure OpenAI service"
  value       = azurerm_cognitive_account.openai.primary_access_key
  sensitive   = true
}

# Azure ML outputs
output "ml_workspace_name" {
  description = "The name of the Azure ML workspace"
  value       = azurerm_machine_learning_workspace.main.name
}

output "ml_workspace_id" {
  description = "The ID of the Azure ML workspace"
  value       = azurerm_machine_learning_workspace.main.id
}

# ACR outputs
output "acr_name" {
  description = "The name of the Azure Container Registry"
  value       = azurerm_container_registry.acr.name
}

output "acr_login_server" {
  description = "The login server of the Azure Container Registry"
  value       = azurerm_container_registry.acr.login_server
}

output "acr_username" {
  description = "The admin username of the Azure Container Registry"
  value       = azurerm_container_registry.acr.admin_username
}

output "acr_password" {
  description = "The admin password of the Azure Container Registry"
  value       = azurerm_container_registry.acr.admin_password
  sensitive   = true
}

# AKS outputs
output "aks_name" {
  description = "The name of the Azure Kubernetes Service cluster"
  value       = azurerm_kubernetes_cluster.main.name
}

output "aks_resource_group" {
  description = "The resource group of the AKS cluster"
  value       = azurerm_resource_group.main.name
}

output "aks_cluster_id" {
  description = "The ID of the AKS cluster"
  value       = azurerm_kubernetes_cluster.main.id
}

output "aks_kube_config" {
  description = "The kubeconfig for the AKS cluster"
  value       = azurerm_kubernetes_cluster.main.kube_config_raw
  sensitive   = true
}

output "aks_host" {
  description = "The host of the AKS cluster"
  value       = azurerm_kubernetes_cluster.main.kube_config[0].host
  sensitive   = true
}

# Key Vault outputs
output "key_vault_name" {
  description = "The name of the Azure Key Vault"
  value       = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  description = "The URI of the Azure Key Vault"
  value       = azurerm_key_vault.main.vault_uri
}

# Application Insights outputs
output "app_insights_name" {
  description = "The name of the Application Insights"
  value       = azurerm_application_insights.main.name
}

output "app_insights_instrumentation_key" {
  description = "The instrumentation key of the Application Insights"
  value       = azurerm_application_insights.main.instrumentation_key
  sensitive   = true
}

output "app_insights_connection_string" {
  description = "The connection string of the Application Insights"
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
}

# Storage Account outputs
output "storage_account_name" {
  description = "The name of the storage account"
  value       = azurerm_storage_account.ml_storage.name
}

output "storage_account_key" {
  description = "The primary key of the storage account"
  value       = azurerm_storage_account.ml_storage.primary_access_key
  sensitive   = true
}

# Log Analytics outputs
output "log_analytics_workspace_id" {
  description = "The ID of the Log Analytics workspace"
  value       = azurerm_log_analytics_workspace.main.id
}

output "log_analytics_workspace_name" {
  description = "The name of the Log Analytics workspace"
  value       = azurerm_log_analytics_workspace.main.name
}
