# Orca Core API Dockerfile
# Multi-stage build for production-ready container with model artifacts

# Build stage
FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package management
RUN pip install uv

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY pyproject.toml README.md ./
RUN uv pip install --system -e .

# Model training stage (optional - can be skipped if models exist)
FROM python:3.11-slim AS model-trainer

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package management
RUN pip install uv

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY pyproject.toml README.md ./
RUN uv pip install --system -e .

# Copy source code for model training
COPY src/ ./src/

# Create models directory
RUN mkdir -p models

# Train XGBoost model (if not already present)
# This can be overridden by copying pre-trained models
RUN python -m orca_core.cli train-xgb --samples 10000 || echo "Model training failed, will use stub model"

# Production stage
FROM python:3.11-slim AS production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    ORCA_MODE=RULES_PLUS_AI \
    ORCA_USE_XGB=true \
    ORCA_EXPLAIN_ENABLED=true \
    ORCA_MODEL_DIR=/app/models/xgb

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r orca && useradd -r -g orca orca

# Set work directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/

# Copy model artifacts from model-trainer stage
COPY --from=model-trainer /app/models/ ./models/

# Create models directory structure
RUN mkdir -p models/xgb && \
    mkdir -p models/stub && \
    chmod 755 models

# Set ownership
RUN chown -R orca:orca /app

# Switch to non-root user
USER orca

# Expose port
EXPOSE 8000

# Health check endpoints
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Default command
CMD ["python", "-m", "orca_api.main"]
