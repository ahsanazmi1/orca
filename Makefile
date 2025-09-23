.PHONY: all setup lint fmt test run clean help install-dev install-precommit

VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip
UVICORN := $(VENV_DIR)/bin/uvicorn
PYTEST := $(VENV_DIR)/bin/pytest
RUFF := $(VENV_DIR)/bin/ruff
BLACK := $(VENV_DIR)/bin/black
PRE_COMMIT := $(VENV_DIR)/bin/pre-commit

APP_MODULE := src/orca_api/main.py
APP_PATH := orca_api.main:app

# Default target
all: setup test

# Setup virtual environment and install dependencies
setup: $(VENV_DIR) install-dev install-precommit
	@echo "✅ Setup complete! Virtual environment created and dependencies installed."
	@echo "💡 Run 'make test' to verify everything works."

$(VENV_DIR):
	@echo "Creating virtual environment..."
	python -m venv $(VENV_DIR)
	@echo "Virtual environment created."

install-dev: $(VENV_DIR)
	@echo "📦 Installing development dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install fastapi uvicorn pytest pytest-cov ruff black mypy httpx
	@echo "✅ Development dependencies installed."

install-precommit: $(VENV_DIR)
	@echo "🔧 Installing pre-commit hooks..."
	$(PIP) install pre-commit
	$(PRE_COMMIT) install
	@echo "✅ Pre-commit hooks installed."

# Run linting checks
lint: $(VENV_DIR)
	@echo "🔍 Running linting checks..."
	$(RUFF) check .
	$(RUFF) format --check .
	@echo "✅ Linting checks passed."

# Format code
fmt: $(VENV_DIR)
	@echo "🎨 Formatting code..."
	$(BLACK) .
	$(RUFF) format .
	@echo "✅ Code formatted."

# Run tests with coverage
test: $(VENV_DIR)
	@echo "🧪 Running tests with coverage..."
	$(PYTEST) tests/test_mcp_smoke.py --cov=mcp --cov-report=term-missing --cov-report=html
	@echo "✅ Tests completed."

# Run the FastAPI application
run: $(VENV_DIR)
	@echo "🚀 Starting Orca service..."
	@if [ -f "$(APP_MODULE)" ]; then \
		$(UVICORN) $(APP_PATH) --reload; \
	else \
		echo "Error: FastAPI application file '$(APP_MODULE)' not found."; \
		exit 1; \
	fi

# Clean up generated files
clean:
	@echo "🧹 Cleaning up..."
	rm -rf $(VENV_DIR)
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .ruff_cache
	rm -rf bandit-report.json
	@echo "✅ Clean up complete."

# Display help message
help:
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m - %s\n", $$1, $$2}'
	@echo ""
	@echo "Quick start:"
	@echo "  make setup  # First time setup"
	@echo "  make test   # Run tests"
	@echo "  make run    # Start the service"