# OCN Logging Infrastructure

## Overview

This directory contains infrastructure configuration and setup instructions for centralized logging across the Open Checkout Network (OCN) ecosystem using Azure Application Insights.

## Environment Variables

### Required Environment Variables

Set these environment variables in each OCN service deployment:

```bash
# Azure Application Insights Configuration
APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=<your-key>;IngestionEndpoint=https://<region>.in.applicationinsights.azure.com/"
APPINSIGHTS_INSTRUMENTATIONKEY="<your-instrumentation-key>"

# Service Identification
OCN_SERVICE_NAME="orca"  # or "weave", "okra", "opal"
OCN_ENVIRONMENT="production"  # or "staging", "development"

# Optional: Advanced Configuration
APPLICATIONINSIGHTS_ENABLEAGENT="true"
APPLICATIONINSIGHTS_ENABLEAPMCORRELATION="true"
```

### Environment-Specific Configuration

#### Development
```bash
export OCN_ENVIRONMENT="development"
export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=<dev-key>;IngestionEndpoint=https://eastus-8.in.applicationinsights.azure.com/"
```

#### Staging
```bash
export OCN_ENVIRONMENT="staging"
export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=<staging-key>;IngestionEndpoint=https://eastus-8.in.applicationinsights.azure.com/"
```

#### Production
```bash
export OCN_ENVIRONMENT="production"
export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=<prod-key>;IngestionEndpoint=https://eastus-8.in.applicationinsights.azure.com/"
```

## Service-Specific Configuration

### Orca (Decision Engine)
```bash
export OCN_SERVICE_NAME="orca"
export ORCA_LOG_LEVEL="INFO"
export ORCA_ENABLE_DECISION_LOGGING="true"
```

### Weave (Receipt Storage)
```bash
export OCN_SERVICE_NAME="weave"
export WEAVE_LOG_LEVEL="INFO"
export WEAVE_ENABLE_RECEIPT_LOGGING="true"
```

### Okra (Credit Agent)
```bash
export OCN_SERVICE_NAME="okra"
export OKRA_LOG_LEVEL="INFO"
export OKRA_ENABLE_QUOTE_LOGGING="true"
```

### Opal (Wallet Agent)
```bash
export OCN_SERVICE_NAME="opal"
export OPAL_LOG_LEVEL="INFO"
export OPAL_ENABLE_SELECTION_LOGGING="true"
```

## Azure Application Insights SDK Integration

### Python Services (Orca, Weave, Okra, Opal)

```python
# Minimal setup for future Application Insights SDK integration
import os
from opencensus.ext.azure.log_exporter import AzureLogHandler
import logging

def setup_application_insights():
    """Set up Azure Application Insights logging."""
    connection_string = os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING')
    if not connection_string:
        logging.warning("APPLICATIONINSIGHTS_CONNECTION_STRING not set, skipping Application Insights")
        return

    # Create Azure log handler
    handler = AzureLogHandler(connection_string=connection_string)

    # Add service-specific properties
    handler.add_telemetry_processor(add_service_properties)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

def add_service_properties(envelope):
    """Add service-specific properties to all telemetry."""
    envelope.data.baseData.properties['service'] = os.getenv('OCN_SERVICE_NAME', 'unknown')
    envelope.data.baseData.properties['environment'] = os.getenv('OCN_ENVIRONMENT', 'unknown')
    envelope.data.baseData.properties['version'] = os.getenv('OCN_VERSION', '1.0.0')
    return True

# Initialize on application startup
if __name__ == "__main__":
    setup_application_insights()
```

### Node.js Services (Future)

```javascript
// Future Node.js integration example
const appInsights = require('applicationinsights');

function setupApplicationInsights() {
    const connectionString = process.env.APPLICATIONINSIGHTS_CONNECTION_STRING;
    if (!connectionString) {
        console.warn('APPLICATIONINSIGHTS_CONNECTION_STRING not set');
        return;
    }

    appInsights.setup(connectionString)
        .setAutoDependencyCorrelation(true)
        .setAutoCollectRequests(true)
        .setAutoCollectPerformance(true)
        .setAutoCollectExceptions(true)
        .setAutoCollectDependencies(true)
        .setAutoCollectConsole(true)
        .setUseDiskRetryCaching(true)
        .setSendLiveMetrics(true)
        .start();

    // Add custom properties
    appInsights.defaultClient.addTelemetryProcessor((envelope) => {
        envelope.data.baseData.properties['service'] = process.env.OCN_SERVICE_NAME || 'unknown';
        envelope.data.baseData.properties['environment'] = process.env.OCN_ENVIRONMENT || 'unknown';
        return true;
    });
}

module.exports = { setupApplicationInsights };
```

## Kubernetes Deployment

### ConfigMap for Environment Variables

```yaml
# k8s/ocn-logging-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ocn-logging-config
  namespace: ocn-system
data:
  APPLICATIONINSIGHTS_CONNECTION_STRING: "InstrumentationKey=<your-key>;IngestionEndpoint=https://eastus-8.in.applicationinsights.azure.com/"
  OCN_ENVIRONMENT: "production"
  APPLICATIONINSIGHTS_ENABLEAGENT: "true"
  APPLICATIONINSIGHTS_ENABLEAPMCORRELATION: "true"
---
# Service-specific ConfigMaps
apiVersion: v1
kind: ConfigMap
metadata:
  name: orca-logging-config
  namespace: ocn-system
data:
  OCN_SERVICE_NAME: "orca"
  ORCA_LOG_LEVEL: "INFO"
  ORCA_ENABLE_DECISION_LOGGING: "true"
```

### Deployment Example

```yaml
# k8s/orca-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orca-deployment
  namespace: ocn-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: orca
  template:
    metadata:
      labels:
        app: orca
    spec:
      containers:
      - name: orca
        image: ocn/orca:latest
        envFrom:
        - configMapRef:
            name: ocn-logging-config
        - configMapRef:
            name: orca-logging-config
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

## Docker Configuration

### Dockerfile Example

```dockerfile
# Dockerfile for OCN services
FROM python:3.13-slim

# Set environment variables for logging
ENV APPLICATIONINSIGHTS_ENABLEAGENT=true
ENV APPLICATIONINSIGHTS_ENABLEAPMCORRELATION=true

# Install Application Insights SDK (when ready)
# RUN pip install opencensus-ext-azure

# Copy application code
COPY . /app
WORKDIR /app

# Install dependencies
RUN pip install -e .

# Run application with logging setup
CMD ["python", "-m", "orca_api.main"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  orca:
    build: ./orca
    environment:
      - APPLICATIONINSIGHTS_CONNECTION_STRING=${APPLICATIONINSIGHTS_CONNECTION_STRING}
      - OCN_SERVICE_NAME=orca
      - OCN_ENVIRONMENT=${OCN_ENVIRONMENT}
    ports:
      - "8000:8000"
    depends_on:
      - weave

  weave:
    build: ./weave
    environment:
      - APPLICATIONINSIGHTS_CONNECTION_STRING=${APPLICATIONINSIGHTS_CONNECTION_STRING}
      - OCN_SERVICE_NAME=weave
      - OCN_ENVIRONMENT=${OCN_ENVIRONMENT}
    ports:
      - "8080:8080"

  okra:
    build: ./okra
    environment:
      - APPLICATIONINSIGHTS_CONNECTION_STRING=${APPLICATIONINSIGHTS_CONNECTION_STRING}
      - OCN_SERVICE_NAME=okra
      - OCN_ENVIRONMENT=${OCN_ENVIRONMENT}
    ports:
      - "8001:8001"

  opal:
    build: ./opal
    environment:
      - APPLICATIONINSIGHTS_CONNECTION_STRING=${APPLICATIONINSIGHTS_CONNECTION_STRING}
      - OCN_SERVICE_NAME=opal
      - OCN_ENVIRONMENT=${OCN_ENVIRONMENT}
    ports:
      - "8002:8002"
```

## Azure Resource Setup

### Terraform Configuration

```hcl
# terraform/application-insights.tf
resource "azurerm_application_insights" "ocn_insights" {
  name                = "ocn-application-insights"
  location            = azurerm_resource_group.ocn_rg.location
  resource_group_name = azurerm_resource_group.ocn_rg.name
  application_type    = "web"

  tags = {
    Environment = var.environment
    Service     = "ocn-observability"
  }
}

resource "azurerm_log_analytics_workspace" "ocn_logs" {
  name                = "ocn-log-analytics"
  location            = azurerm_resource_group.ocn_rg.location
  resource_group_name = azurerm_resource_group.ocn_rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 90

  tags = {
    Environment = var.environment
    Service     = "ocn-observability"
  }
}

# Output the connection string for environment variables
output "application_insights_connection_string" {
  value = azurerm_application_insights.ocn_insights.connection_string
  sensitive = true
}

output "application_insights_instrumentation_key" {
  value = azurerm_application_insights.ocn_insights.instrumentation_key
  sensitive = true
}
```

### ARM Template

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "environment": {
      "type": "string",
      "defaultValue": "production"
    }
  },
  "resources": [
    {
      "type": "Microsoft.Insights/components",
      "apiVersion": "2020-02-02",
      "name": "[concat('ocn-insights-', parameters('environment'))]",
      "location": "[resourceGroup().location]",
      "kind": "web",
      "properties": {
        "Application_Type": "web",
        "Request_Source": "rest"
      }
    }
  ]
}
```

## Monitoring and Alerting

### Health Check Endpoints

Each service MUST implement a health check endpoint:

```python
# Health check implementation
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": os.getenv('OCN_SERVICE_NAME'),
        "environment": os.getenv('OCN_ENVIRONMENT'),
        "timestamp": datetime.utcnow().isoformat(),
        "version": os.getenv('OCN_VERSION', '1.0.0')
    }
```

### Log Levels by Environment

| Environment | Log Level | Trace Level | Custom Dimensions |
|-------------|-----------|-------------|-------------------|
| Development | DEBUG | VERBOSE | Full details |
| Staging | INFO | MODERATE | Business metrics |
| Production | WARNING | MINIMAL | Essential metrics only |

## Troubleshooting

### Common Issues

1. **Missing logs in Application Insights**
   - Check connection string format
   - Verify environment variables are set
   - Check network connectivity to Azure

2. **High log volume costs**
   - Implement log sampling
   - Use appropriate log levels
   - Filter out debug logs in production

3. **Missing custom dimensions**
   - Ensure JSON serialization is working
   - Check that `extra` parameter is used correctly
   - Verify Application Insights SDK is properly configured

### Debug Commands

```bash
# Check environment variables
echo $APPLICATIONINSIGHTS_CONNECTION_STRING
echo $OCN_SERVICE_NAME
echo $OCN_ENVIRONMENT

# Test Application Insights connectivity
curl -X POST "https://dc.applicationinsights.azure.com/v2/track" \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "time": "2024-01-21T12:00:00.000Z"}'

# View recent logs
az monitor app-insights query \
  --resource-group ocn-rg \
  --app ocn-insights \
  --analytics-query "customEvents | where timestamp > ago(1h) | take 10"
```

## Security Considerations

### Secrets Management

- Store connection strings in Azure Key Vault
- Use managed identities where possible
- Rotate instrumentation keys regularly
- Limit access to Application Insights data

### Data Privacy

- All sensitive data MUST be redacted before logging
- Use the OCN logging setup modules for automatic redaction
- Implement data retention policies
- Ensure GDPR/CCPA compliance

## Cost Optimization

### Log Sampling

```python
# Implement log sampling for high-volume scenarios
import random

def should_sample_log(log_level: str) -> bool:
    """Determine if log should be sampled based on level."""
    if log_level == "ERROR":
        return True  # Always log errors
    elif log_level == "WARNING":
        return random.random() < 0.1  # 10% of warnings
    elif log_level == "INFO":
        return random.random() < 0.01  # 1% of info logs
    return False
```

### Retention Policies

- Raw logs: 90 days
- Aggregated metrics: 1 year
- Custom dashboards: Indefinite (backed up to Git)

## Migration Guide

### From Local Logging to Application Insights

1. **Phase 1**: Add Application Insights SDK without changing existing logging
2. **Phase 2**: Gradually migrate to structured JSON logging
3. **Phase 3**: Implement custom dimensions and business metrics
4. **Phase 4**: Set up dashboards and alerting

### Rollback Plan

- Keep existing logging infrastructure during transition
- Use feature flags to enable/disable Application Insights
- Monitor costs and performance impact
- Have rollback procedures documented and tested

---

*This infrastructure guide is part of the OCN observability framework. For questions or issues, refer to the main [Observability Specification](../docs/observability.md).*
