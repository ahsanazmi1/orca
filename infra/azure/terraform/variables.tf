# Variables for Orca Core Azure Infrastructure

variable "resource_group_name" {
  description = "The name of the resource group"
  type        = string
  default     = "orcacore-rg"
}

variable "location" {
  description = "The location for all resources"
  type        = string
  default     = "East US"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "openai_service_name" {
  description = "Azure OpenAI service name"
  type        = string
  default     = "orca-openai"
}

variable "openai_deployment_name" {
  description = "Azure OpenAI deployment name"
  type        = string
  default     = "gpt-4o-mini"
}

variable "ml_workspace_name" {
  description = "Azure ML workspace name"
  type        = string
  default     = "orca-ml-workspace"
}

variable "acr_name" {
  description = "Azure Container Registry name"
  type        = string
  default     = "orcacoreacr"
}

variable "aks_name" {
  description = "Azure Kubernetes Service cluster name"
  type        = string
  default     = "orca-aks"
}

variable "key_vault_name" {
  description = "Azure Key Vault name"
  type        = string
  default     = "orca-keyvault"
}

variable "app_insights_name" {
  description = "Application Insights name"
  type        = string
  default     = "orca-appinsights"
}

variable "storage_account_name" {
  description = "Storage account name for ML data"
  type        = string
  default     = "orcacorestorage"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "OrcaCore"
    Environment = "dev"
    ManagedBy   = "Terraform"
  }
}
