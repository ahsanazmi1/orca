# Orca Development Makefile
# Provides common development tasks and shortcuts

.PHONY: help doctor init install install-mac install-win clean test lint format type-check security-check run fmt type

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

# ML Training commands
train-model: ## Train Random Forest risk prediction model
	@echo "🤖 Training Random Forest model..."
	PYTHONPATH=src uv run python -m orca_core.cli train --samples 2000

model-info: ## Show ML model information
	@echo "📊 ML Model Information:"
	PYTHONPATH=src uv run python -m orca_core.cli model-info

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

# Project information
info: ## Show project information
	@echo "📋 Orca Project Information:"
	@echo "  Python version: $$(python --version 2>/dev/null || echo 'Not found')"
	@echo "  uv version: $$(uv --version 2>/dev/null || echo 'Not found')"
	@echo "  Git version: $$(git --version 2>/dev/null || echo 'Not found')"
	@echo "  GitHub CLI version: $$(gh --version 2>/dev/null | head -1 || echo 'Not found')"
	@echo "  Node version: $$(node --version 2>/dev/null || echo 'Not found')"
	@echo "  Docker version: $$(docker --version 2>/dev/null || echo 'Not found')"
