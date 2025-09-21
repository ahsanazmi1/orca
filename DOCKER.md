# Docker Setup for Orca Core

This document provides comprehensive instructions for building, running, and managing Orca Core using Docker.

## 🐳 Overview

Orca Core is containerized using a multi-stage Docker build that includes:
- **Build Stage**: Python dependencies and package installation
- **Model Training Stage**: XGBoost model training (optional)
- **Production Stage**: Optimized runtime with model artifacts

## 📁 Docker Files

### Core Files
- **`Dockerfile`**: Multi-stage build configuration
- **`.dockerignore`**: Files to exclude from Docker context
- **`docker-compose.yml`**: Development and production orchestration
- **`nginx.conf`**: Reverse proxy configuration

## 🚀 Quick Start

### 1. Build Docker Image

```bash
# Build production image
make docker-build

# Build development image
make docker-build-dev
```

### 2. Run Container

```bash
# Run with Docker Compose (recommended)
make docker-run-dev

# Run standalone container
make docker-run
```

### 3. Check Health

```bash
# Check container health
make docker-health
```

## 🔧 Detailed Setup

### Prerequisites

1. **Docker**: Version 20.10+ with BuildKit support
2. **Docker Compose**: Version 2.0+
3. **Environment File**: `.env.local` with configuration

### Environment Configuration

Create `.env.local` with required variables:

```bash
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini

# Orca Configuration
ORCA_DECISION_MODE=RULES_PLUS_AI
ORCA_USE_XGB=true
ORCA_EXPLAIN_ENABLED=true
ORCA_MODEL_DIR=/app/models/xgb

# Environment
ENVIRONMENT=development
```

### Build Process

#### Multi-Stage Build

The Dockerfile uses three stages:

1. **Builder Stage**:
   - Installs Python dependencies
   - Uses `uv` for fast package management
   - Creates optimized Python environment

2. **Model Trainer Stage**:
   - Trains XGBoost model (if not present)
   - Generates model artifacts
   - Can be skipped if pre-trained models exist

3. **Production Stage**:
   - Minimal runtime environment
   - Copies model artifacts
   - Non-root user for security
   - Health check configuration

#### Build Commands

```bash
# Standard build
docker build -t orca-core-api:latest .

# Build specific stage
docker build --target production -t orca-core-api:prod .

# Build with build arguments
docker build --build-arg MODEL_VERSION=1.0.0 -t orca-core-api:latest .
```

### Running Containers

#### Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# Start with build
docker-compose up --build

# View logs
docker-compose logs -f orca-core-api

# Stop services
docker-compose down
```

#### Standalone Container

```bash
# Run with environment file
docker run -p 8000:8000 --env-file .env.local orca-core-api:latest

# Run with volume mounts
docker run -p 8000:8000 \
  -v $(pwd)/models:/app/models:ro \
  -v $(pwd)/.env.local:/app/.env.local:ro \
  orca-core-api:latest

# Run in background
docker run -d -p 8000:8000 --name orca-api orca-core-api:latest
```

## 🏥 Health Checks

### Health Endpoints

Orca Core provides comprehensive health checking:

#### `/healthz` - Liveness Probe
- **Purpose**: Kubernetes liveness probe
- **Response**: Basic service health status
- **Timeout**: 10 seconds
- **Interval**: 30 seconds

```json
{
  "ok": true,
  "timestamp": "2025-09-15T00:58:29.421128",
  "version": "0.1.0",
  "environment": "production"
}
```

#### `/readyz` - Readiness Probe
- **Purpose**: Kubernetes readiness probe
- **Response**: Detailed component status
- **Checks**: Configuration, ML model, LLM service, model artifacts

```json
{
  "ready": true,
  "timestamp": "2025-09-15T00:58:35.120311",
  "checks": {
    "configuration": {
      "status": "ok",
      "decision_mode": "RULES_PLUS_AI",
      "use_xgb": true,
      "explain_enabled": true
    },
    "ml_model": {
      "status": "ok",
      "model_type": "xgb",
      "version": "1.0.0"
    },
    "llm_service": {
      "status": "ok",
      "configured": true
    },
    "model_artifacts": {
      "status": "ok",
      "model_dir": "/app/models/xgb",
      "files": ["xgb_model.joblib", "calibrator.joblib", "metadata.json"]
    }
  },
  "overall_status": "ready"
}
```

### Health Check Configuration

#### Docker Health Check

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1
```

#### Kubernetes Health Checks

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /readyz
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

## 🔧 Development Workflow

### Local Development

```bash
# Start development environment
make docker-run-dev

# View logs
make docker-logs

# Open shell in container
make docker-shell

# Check health
make docker-health

# Stop containers
make docker-stop
```

### Model Development

```bash
# Train model locally
make train-xgb

# Copy models to container
docker cp models/ <container-id>:/app/models/

# Restart container to pick up new models
docker-compose restart orca-core-api
```

### Testing

```bash
# Run tests in container
docker-compose exec orca-core-api python -m pytest tests/

# Test API endpoints
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
curl -X POST http://localhost:8000/decision \
  -H "Content-Type: application/json" \
  -d '{"cart_total": 100.0, "currency": "USD", "rail": "Card"}'
```

## 🚀 Production Deployment

### Production Configuration

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  orca-core-api:
    build:
      context: .
      target: production
    environment:
      - ENVIRONMENT=production
      - ORCA_MODE=RULES_PLUS_AI
      - ORCA_USE_XGB=true
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Production Build

```bash
# Build production image
docker build --target production -t orca-core-api:prod .

# Tag for registry
docker tag orca-core-api:prod your-registry/orca-core-api:latest

# Push to registry
docker push your-registry/orca-core-api:latest
```

## 🔍 Troubleshooting

### Common Issues

1. **Build Failures**
   ```bash
   # Check Dockerfile syntax
   docker build --no-cache -t test .

   # Check build context
   docker build --progress=plain -t test .
   ```

2. **Container Won't Start**
   ```bash
   # Check logs
   docker logs <container-id>

   # Check environment variables
   docker exec <container-id> env

   # Check file permissions
   docker exec <container-id> ls -la /app/models/
   ```

3. **Health Check Failures**
   ```bash
   # Test health endpoints manually
   curl -v http://localhost:8000/healthz
   curl -v http://localhost:8000/readyz

   # Check container logs
   docker logs <container-id> | grep -i health
   ```

4. **Model Loading Issues**
   ```bash
   # Check model directory
   docker exec <container-id> ls -la /app/models/

   # Check environment variables
   docker exec <container-id> echo $ORCA_MODEL_DIR

   # Test model loading
   docker exec <container-id> python -c "from orca_core.ml.model import predict_risk; print(predict_risk({'amount': 100}))"
   ```

### Debug Commands

```bash
# Inspect image layers
docker history orca-core-api:latest

# Check image size
docker images orca-core-api:latest

# Inspect container
docker inspect <container-id>

# Check resource usage
docker stats <container-id>

# Access container shell
docker exec -it <container-id> /bin/bash
```

## 📊 Performance Optimization

### Image Size Optimization

- **Multi-stage builds**: Separate build and runtime environments
- **Alpine base images**: Minimal base images for smaller size
- **Layer caching**: Optimize layer order for better caching
- **Dependency cleanup**: Remove build dependencies in production stage

### Runtime Optimization

- **Resource limits**: Set appropriate CPU and memory limits
- **Health checks**: Configure proper health check intervals
- **Logging**: Use structured logging for better monitoring
- **Metrics**: Expose Prometheus metrics for monitoring

## 🔒 Security Considerations

### Container Security

- **Non-root user**: Run containers as non-root user
- **Read-only filesystem**: Use read-only root filesystem where possible
- **Minimal base image**: Use minimal base images
- **Regular updates**: Keep base images updated

### Secret Management

- **Environment variables**: Use environment variables for configuration
- **Secret mounts**: Mount secrets as files, not environment variables
- **Key Vault integration**: Use Azure Key Vault CSI driver for secrets
- **No hardcoded secrets**: Never hardcode secrets in images

## 📚 Additional Resources

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Multi-stage Builds](https://docs.docker.com/develop/dev-best-practices/dockerfile_best-practices/#use-multi-stage-builds)
- [Health Checks](https://docs.docker.com/engine/reference/builder/#healthcheck)
- [Docker Compose](https://docs.docker.com/compose/)
- [Kubernetes Health Checks](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)


