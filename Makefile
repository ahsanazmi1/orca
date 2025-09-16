# Orca Development Makefile
# Provides common development tasks and shortcuts

.PHONY: help doctor init install install-mac install-win clean test lint format type-check security-check run fmt type configure-azure-openai test-config

# Default target
help: ## Show this help message
	@echo "Orca Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development environment setup
doctor: ## Run development environment health check
	@echo "🔍 Running development environment check..."
	python scripts/doctor.py

init: ## Initialize the development environment (uv sync + pre-commit + doctor)
	@echo "🚀 Initializing Orca development environment..."
	@echo "📦 Syncing dependencies with uv..."
	uv sync --dev
	@echo "🔧 Installing pre-commit hooks..."
	uv run pre-commit install
	@echo "🔍 Running final health check..."
	$(MAKE) doctor
	@echo "✅ Development environment initialized!"

# Installation scripts
install-mac: ## Run macOS installation script
	@echo "🍎 Running macOS installation script..."
	chmod +x scripts/install_mac.sh
	./scripts/install_mac.sh

install-win: ## Run Windows installation script
	@echo "🪟 Running Windows installation script..."
	powershell -ExecutionPolicy Bypass -File scripts/install_win.ps1

install: ## Run appropriate installation script based on OS
	@echo "🔧 Detecting operating system..."
ifeq ($(OS),Windows_NT)
	@echo "Windows detected, running Windows installer..."
	$(MAKE) install-win
else
	@echo "Unix-like system detected, running macOS installer..."
	$(MAKE) install-mac
endif

# API and development
run: ## Run the FastAPI server
	@echo "🚀 Starting FastAPI server..."
	PYTHONPATH=src uv run uvicorn orca_api.main:app --reload --port 8080

# Code quality and testing
test: ## Run tests with pytest
	@echo "🧪 Running tests..."
	PYTHONPATH=src uv run pytest

lint: ## Run linting with ruff
	@echo "🔍 Running linter..."
	uv run ruff check .

fmt: ## Format code with ruff and black
	@echo "✨ Formatting code..."
	uv run ruff format .
	uv run black .

format: fmt ## Alias for fmt

type: ## Run type checking with mypy on src/
	@echo "🔍 Running type checker..."
	uv run mypy src/

type-check: type ## Alias for type

security-check: ## Run security check with bandit
	@echo "🔒 Running security check..."
	uv run bandit -r src/ -x tests,demos,scripts

check-all: lint type-check security-check test ## Run all checks (lint, type-check, security, test)

# Pre-commit hooks
pre-commit-run: ## Run pre-commit on all files
	@echo "🔧 Running pre-commit hooks..."
	pre-commit run --all-files

pre-commit-update: ## Update pre-commit hooks
	@echo "🔄 Updating pre-commit hooks..."
	pre-commit autoupdate

# Development utilities
clean: ## Clean up temporary files and caches
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete!"

# Streamlit development
streamlit: ## Run Streamlit app
	@echo "🌊 Starting Streamlit app..."
	uv run streamlit run app.py

streamlit-dev: ## Run Streamlit in development mode
	@echo "🌊 Starting Streamlit in development mode..."
	uv run streamlit run app.py --server.runOnSave true

demo: ## Run Streamlit demo
	@echo "🌊 Starting Orca Core demo..."
	uv run streamlit run demos/app.py

demo-phase2: ## Run comprehensive Phase 2 AI/LLM demo
	@echo "🚀 Starting Orca Core Phase 2 demo..."
	@chmod +x scripts/demo_phase2.sh
	./scripts/demo_phase2.sh

# ML Training commands
train-model: ## Train Random Forest risk prediction model
	@echo "🤖 Training Random Forest model..."
	PYTHONPATH=src uv run python -m orca_core.cli train --samples 2000


train-script: ## Run standalone training script
	@echo "🚀 Running training script..."
	PYTHONPATH=src uv run python scripts/train_model.py

# Git utilities
git-setup: ## Set up Git configuration
	@echo "🔧 Setting up Git configuration..."
	git config user.name "Mohsin"
	git config user.email "ahsanazmi@icloud.com"
	@echo "✅ Git configuration complete!"

# Docker utilities (if Docker is available)
docker-build: ## Build Docker image
	@echo "🐳 Building Docker image..."
	docker build -t orca .

docker-run: ## Run Docker container
	@echo "🐳 Running Docker container..."
	docker run -p 8501:8501 orca

# Azure Configuration (Phase 2)
configure-azure-openai: ## Configure Azure OpenAI and Azure infrastructure settings
	@echo "🔧 Configuring Azure OpenAI for Phase 2..."
	PYTHONPATH=src uv run python scripts/configure_azure_openai.py

test-config: ## Test current configuration and show status
	@echo "🔍 Testing current configuration..."
	PYTHONPATH=src uv run python -m orca_core.cli config

# Azure Deployment (Phase 2) - Moved to Azure Infrastructure Management section

build-docker: ## Build Docker image for Orca Core
	@echo "🐳 Building Docker image..."
	docker build -t orca-core:latest .

push-docker: ## Push Docker image to Azure Container Registry
	@echo "📤 Pushing Docker image to ACR..."
	az acr login --name orcaregistry
	docker tag orca-core:latest orcaregistry.azurecr.io/orca-core:latest
	docker push orcaregistry.azurecr.io/orca-core:latest

create-ml-data: ## Create ML training data
	@echo "🤖 Creating ML training data..."
	PYTHONPATH=src uv run python scripts/create_ml_model.py

train-xgb: ## Train XGBoost model for risk prediction
	@echo "🤖 Training XGBoost model..."
	PYTHONPATH=src uv run python -m orca_core.cli train-xgb --samples 10000

model-info: ## Show current ML model information
	@echo "📊 ML Model Information:"
	PYTHONPATH=src uv run python -m orca_core.cli model-info

test-xgb: ## Test XGBoost model with sample data
	@echo "🧪 Testing XGBoost model..."
	ORCA_USE_XGB=true PYTHONPATH=src uv run python -m orca_core.cli decide '{"cart_total": 100.0, "currency": "USD", "rail": "Card", "channel": "online", "features": {"amount": 600.0, "velocity_24h": 3.0, "cross_border": 1.0}}'

test-llm: ## Test LLM explanations with AI mode
	@echo "🤖 Testing LLM explanations..."
	ORCA_MODE=RULES_PLUS_AI ORCA_USE_XGB=true PYTHONPATH=src uv run python -m orca_core.cli decide '{"cart_total": 100.0, "currency": "USD", "rail": "Card", "channel": "online", "features": {"amount": 600.0, "velocity_24h": 3.0, "cross_border": 1.0}}'

test-llm-stub: ## Test LLM explanations with stub model
	@echo "🤖 Testing LLM explanations with stub model..."
	ORCA_MODE=RULES_PLUS_AI PYTHONPATH=src uv run python -m orca_core.cli decide '{"cart_total": 100.0, "currency": "USD", "rail": "Card", "channel": "online", "features": {"amount": 600.0, "velocity_24h": 3.0, "cross_border": 1.0}}'

debug-ui: ## Launch Streamlit debug UI
	@echo "🚀 Launching Orca Core Debug UI..."
	PYTHONPATH=src uv run python -m orca_core.cli debug-ui

generate-plots: ## Generate ML model evaluation plots
	@echo "📊 Generating ML model evaluation plots..."
	PYTHONPATH=src uv run python -m orca_core.cli generate-plots

validate-fixtures: ## Test all validation fixtures
	@echo "🧪 Testing validation fixtures..."
	PYTHONPATH=src uv run python -m orca_core.cli decide-batch --glob "validation/phase2/fixtures/*.json" --format csv --output validation/phase2/data/fixture_results.csv

validate-comparison: ## Analyze Radar comparison data
	@echo "📊 Analyzing Radar comparison data..."
	@python -c "import pandas as pd; df = pd.read_csv('validation/phase2/data/radar_compare.csv'); print(f'Decision Agreement: {df[\"decision_match\"].mean():.1%}'); print(f'Risk Correlation: {df[\"orca_risk_score\"].corr(df[\"radar_risk_score\"]):.3f}')"

# Azure Infrastructure Management
bootstrap-azure: ## Bootstrap Azure infrastructure
	@echo "🚀 Bootstrapping Azure infrastructure..."
	./infra/azure/scripts/bootstrap.sh

bootstrap-azure-staging: ## Bootstrap Azure infrastructure for staging
	@echo "🚀 Bootstrapping Azure infrastructure for staging..."
	./infra/azure/scripts/bootstrap.sh -e staging

bootstrap-azure-prod: ## Bootstrap Azure infrastructure for production
	@echo "🚀 Bootstrapping Azure infrastructure for production..."
	./infra/azure/scripts/bootstrap.sh -e prod

deploy-azure: ## Deploy Orca Core to Azure
	@echo "🚀 Deploying Orca Core to Azure..."
	./infra/azure/scripts/deploy.sh

deploy-azure-staging: ## Deploy Orca Core to Azure staging
	@echo "🚀 Deploying Orca Core to Azure staging..."
	./infra/azure/scripts/deploy.sh -e staging

deploy-azure-prod: ## Deploy Orca Core to Azure production
	@echo "🚀 Deploying Orca Core to Azure production..."
	./infra/azure/scripts/deploy.sh -e prod

cleanup-azure: ## Clean up Azure infrastructure
	@echo "🧹 Cleaning up Azure infrastructure..."
	./infra/azure/scripts/cleanup.sh

cleanup-azure-staging: ## Clean up Azure staging infrastructure
	@echo "🧹 Cleaning up Azure staging infrastructure..."
	./infra/azure/scripts/cleanup.sh -e staging

cleanup-azure-prod: ## Clean up Azure production infrastructure
	@echo "🧹 Cleaning up Azure production infrastructure..."
	./infra/azure/scripts/cleanup.sh -e prod

keyvault-set: ## Set secrets in Azure Key Vault
	@echo "🔐 Setting secrets in Azure Key Vault..."
	./infra/azure/scripts/keyvault-secrets.sh set

keyvault-get: ## Get secrets from Azure Key Vault
	@echo "🔐 Getting secrets from Azure Key Vault..."
	./infra/azure/scripts/keyvault-secrets.sh get

keyvault-backup: ## Backup Azure Key Vault secrets
	@echo "🔐 Backing up Azure Key Vault secrets..."
	./infra/azure/scripts/keyvault-secrets.sh backup

# GitHub Actions Management
github-workflows: ## Show GitHub Actions workflow status
	@echo "🔄 GitHub Actions Workflows:"
	@echo "  Deploy: .github/workflows/deploy.yml"
	@echo "  Test: .github/workflows/test.yml"
	@echo "  Release: .github/workflows/release.yml"
	@echo "  OIDC Setup: .github/OIDC_SETUP.md"

github-test: ## Run GitHub Actions test workflow locally
	@echo "🧪 Running GitHub Actions test workflow locally..."
	@echo "Note: This simulates the test workflow. For full CI/CD, push to GitHub."

github-deploy: ## Trigger GitHub Actions deployment
	@echo "🚀 Triggering GitHub Actions deployment..."
	@echo "Note: This requires GitHub CLI and proper OIDC setup."
	@echo "Run: gh workflow run deploy.yml"

github-release: ## Create a new release
	@echo "📦 Creating a new release..."
	@echo "Note: This requires GitHub CLI and proper OIDC setup."
	@echo "Run: gh workflow run release.yml -f version=v1.0.0"

# Key Vault CSI Driver Management
csi-driver-install: ## Install Azure Key Vault CSI driver
	@echo "🔐 Installing Azure Key Vault CSI driver..."
	@kubectl apply -f k8s/csi-driver/install-csi-driver.yaml

csi-driver-setup-dev: ## Setup CSI driver for development environment
	@echo "🔐 Setting up CSI driver for development..."
	@./k8s/csi-driver/setup-csi-driver.sh dev

csi-driver-setup-staging: ## Setup CSI driver for staging environment
	@echo "🔐 Setting up CSI driver for staging..."
	@./k8s/csi-driver/setup-csi-driver.sh staging

csi-driver-setup-prod: ## Setup CSI driver for production environment
	@echo "🔐 Setting up CSI driver for production..."
	@./k8s/csi-driver/setup-csi-driver.sh prod

csi-driver-status: ## Check CSI driver status
	@echo "🔍 Checking CSI driver status..."
	@kubectl get pods -n kube-system | grep secrets-store-csi-driver
	@kubectl get secretproviderclass -n orca-core
	@kubectl get azureidentity -n orca-core

csi-driver-test: ## Test CSI driver integration
	@echo "🧪 Testing CSI driver integration..."
	@kubectl apply -f k8s/csi-driver/deployment-with-csi.yaml
	@echo "Waiting for deployment to be ready..."
	@kubectl rollout status deployment/orca-core-api --namespace=orca-core --timeout=300s
	@kubectl get pods -n orca-core -l app=orca-core-api

# Docker Management
docker-build: ## Build Docker image
	@echo "🐳 Building Docker image..."
	@docker build -t orca-core-api:latest .

docker-build-dev: ## Build Docker image for development
	@echo "🐳 Building Docker image for development..."
	@docker build --target production -t orca-core-api:dev .

docker-run: ## Run Docker container locally
	@echo "🐳 Running Docker container..."
	@docker run -p 8000:8000 --env-file .env.local orca-core-api:latest

docker-run-dev: ## Run Docker container in development mode
	@echo "🐳 Running Docker container in development mode..."
	@docker-compose up --build

docker-stop: ## Stop Docker containers
	@echo "🐳 Stopping Docker containers..."
	@docker-compose down

docker-logs: ## Show Docker container logs
	@echo "🐳 Showing Docker container logs..."
	@docker-compose logs -f orca-core-api

docker-shell: ## Open shell in running Docker container
	@echo "🐳 Opening shell in Docker container..."
	@docker-compose exec orca-core-api /bin/bash

docker-health: ## Check Docker container health
	@echo "🐳 Checking Docker container health..."
	@curl -f http://localhost:8000/healthz || echo "Health check failed"
	@curl -f http://localhost:8000/readyz || echo "Readiness check failed"

docker-clean: ## Clean up Docker images and containers
	@echo "🐳 Cleaning up Docker resources..."
	@docker-compose down --volumes --remove-orphans
	@docker system prune -f

# Project information
info: ## Show project information
	@echo "📋 Orca Project Information:"
	@echo "  Python version: $$(python --version 2>/dev/null || echo 'Not found')"
	@echo "  uv version: $$(uv --version 2>/dev/null || echo 'Not found')"
	@echo "  Git version: $$(git --version 2>/dev/null || echo 'Not found')"
	@echo "  GitHub CLI version: $$(gh --version 2>/dev/null | head -1 || echo 'Not found')"
	@echo "  Node version: $$(node --version 2>/dev/null || echo 'Not found')"
	@echo "  Docker version: $$(docker --version 2>/dev/null || echo 'Not found')"
