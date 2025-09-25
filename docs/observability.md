# OCN Observability Specification

## Overview

The Open Checkout Network (OCN) implements enterprise-grade observability using structured JSON logging with Azure Application Insights for centralized monitoring, alerting, and analytics.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Orca Core     │    │     Weave       │    │   Okra/Opal     │
│   (Decisions)   │    │  (Receipts)     │    │  (Credit/Wallet)│
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │  Azure Application Insights│
                    │  + Log Analytics Workspace│
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │    OCN Dashboards        │
                    │  (Decisions, Errors, etc)│
                    └───────────────────────────┘
```

## Structured Logging Requirements

### JSON Log Format

All OCN services MUST emit structured JSON logs with the following standard fields:

```json
{
  "timestamp": "2024-01-21T12:00:00.000Z",
  "level": "INFO",
  "logger": "src.orca.engine",
  "message": "Processing payment decision",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "module": "engine",
  "function": "evaluate_rules",
  "line": 142,
  "service": "orca",
  "event_type": "decision",
  "custom_dimensions": {
    "decision_result": "APPROVE",
    "risk_score": 0.15,
    "processing_time_ms": 45
  }
}
```

### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `timestamp` | string | ISO 8601 timestamp | `"2024-01-21T12:00:00.000Z"` |
| `level` | string | Log level | `"INFO"`, `"WARNING"`, `"ERROR"` |
| `logger` | string | Logger name | `"src.orca.engine"` |
| `message` | string | Human-readable message | `"Processing payment decision"` |
| `trace_id` | string | **REQUIRED** - Request correlation ID | `"550e8400-e29b-41d4-a716-446655440000"` |
| `service` | string | Service identifier | `"orca"`, `"weave"`, `"okra"`, `"opal"` |
| `event_type` | string | Event classification | `"decision"`, `"receipt"`, `"credit_quote"` |

### Custom Dimensions

Each service SHOULD include relevant business metrics in `custom_dimensions`:

#### Orca (Decision Engine)
```json
{
  "custom_dimensions": {
    "decision_result": "APPROVE|DECLINE|REVIEW",
    "risk_score": 0.15,
    "processing_time_ms": 45,
    "rules_triggered": ["velocity_check", "mcc_validation"],
    "ml_model_version": "1.0.0"
  }
}
```

#### Weave (Receipt Storage)
```json
{
  "custom_dimensions": {
    "receipt_type": "decision|explanation",
    "provider_id": "ocn-orca-v1",
    "storage_time_ms": 12,
    "receipt_hash": "sha256:abc123..."
  }
}
```

#### Okra (Credit Agent)
```json
{
  "custom_dimensions": {
    "credit_decision": "APPROVE|DECLINE|REVIEW",
    "requested_amount": 5000,
    "credit_score": 720,
    "dti_ratio": 0.35,
    "processing_time_ms": 23
  }
}
```

#### Opal (Wallet Agent)
```json
{
  "custom_dimensions": {
    "selection_result": "ALLOWED|DENIED",
    "transaction_amount": 99.99,
    "mcc_code": "5411",
    "channel": "pos",
    "control_triggered": "daily_limit"
  }
}
```

## Azure Application Insights Setup

### 1. Create Application Insights Resource

```bash
# Create resource group
az group create --name ocn-rg --location eastus

# Create Application Insights
az monitor app-insights component create \
  --resource-group ocn-rg \
  --app ocn-insights \
  --location eastus \
  --kind web
```

### 2. Get Instrumentation Key

```bash
# Get the instrumentation key
az monitor app-insights component show \
  --resource-group ocn-rg \
  --app ocn-insights \
  --query instrumentationKey \
  --output tsv
```

### 3. Environment Variables

Set the following environment variables in each service:

```bash
# Required for all services
export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=<your-key>;IngestionEndpoint=https://eastus-8.in.applicationinsights.azure.com/"
export APPINSIGHTS_INSTRUMENTATIONKEY="<your-instrumentation-key>"

# Optional: Service identification
export OCN_SERVICE_NAME="orca"  # or "weave", "okra", "opal"
export OCN_ENVIRONMENT="production"  # or "staging", "development"
```

### 4. Log Analytics Workspace Integration

Application Insights automatically creates a Log Analytics workspace. Query data using Kusto (KQL):

```kusto
// Basic query structure
customEvents
| where timestamp > ago(1h)
| where customDimensions.service == "orca"
| project timestamp, name, customDimensions
```

## OCN Dashboards

### Dashboard 1: "Decisions Over Time"

**Purpose**: Monitor decision volume and outcomes across all services

**Widgets**:
1. **Decision Volume** (Line Chart)
   - X-axis: Time (1-hour buckets)
   - Y-axis: Count of decisions
   - Split by: `customDimensions.decision_result`

2. **Decision Distribution** (Pie Chart)
   - Show: `APPROVE` vs `DECLINE` vs `REVIEW` percentages
   - Time range: Last 24 hours

3. **Service Comparison** (Bar Chart)
   - X-axis: Service name (`customDimensions.service`)
   - Y-axis: Decision count
   - Filter: Last 7 days

**Kusto Query Example**:
```kusto
customEvents
| where name == "decision_processed"
| where timestamp > ago(24h)
| extend decision_result = tostring(customDimensions.decision_result)
| extend service_name = tostring(customDimensions.service)
| summarize decision_count = count() by bin(timestamp, 1h), decision_result
| render timechart
```

### Dashboard 2: "Explanation Rate"

**Purpose**: Track AI/LLM explanation usage and performance

**Widgets**:
1. **Explanation Coverage** (Gauge)
   - Show: Percentage of decisions with explanations
   - Target: >80% explanation rate

2. **Explanation Latency** (Line Chart)
   - X-axis: Time
   - Y-axis: Average explanation generation time
   - Split by: Explanation type

3. **Explanation Quality** (Bar Chart)
   - Show: Confidence score distribution
   - Filter: Last 7 days

**Kusto Query Example**:
```kusto
customEvents
| where name == "explanation_generated"
| where timestamp > ago(7d)
| extend confidence = todouble(customDimensions.confidence_score)
| extend explanation_time = todouble(customDimensions.explanation_time_ms)
| summarize
    explanation_count = count(),
    avg_confidence = avg(confidence),
    avg_time = avg(explanation_time)
  by bin(timestamp, 1h)
| render timechart
```

### Dashboard 3: "Errors by Service"

**Purpose**: Monitor error rates and types across OCN services

**Widgets**:
1. **Error Rate by Service** (Bar Chart)
   - X-axis: Service name
   - Y-axis: Error rate percentage
   - Time range: Last 24 hours

2. **Error Trends** (Line Chart)
   - X-axis: Time
   - Y-axis: Error count
   - Split by: Service and error type

3. **Top Error Messages** (Table)
   - Show: Most frequent error messages
   - Columns: Error message, count, affected service

**Kusto Query Example**:
```kusto
exceptions
| where timestamp > ago(24h)
| extend service_name = tostring(customDimensions.service)
| extend error_type = tostring(customDimensions.error_type)
| summarize error_count = count() by service_name, error_type
| order by error_count desc
| take 10
```

### Dashboard 4: "Latency by Event Type"

**Purpose**: Monitor performance of CloudEvents processing

**Widgets**:
1. **Decision Processing Time** (Line Chart)
   - X-axis: Time
   - Y-axis: P50, P95, P99 processing times
   - Event type: `ocn.orca.decision.v1`

2. **Receipt Storage Time** (Line Chart)
   - X-axis: Time
   - Y-axis: P50, P95, P99 storage times
   - Event type: `ocn.weave.receipt.v1`

3. **End-to-End Latency** (Gauge)
   - Show: Average time from decision to receipt storage
   - Target: <200ms

**Kusto Query Example**:
```kusto
customEvents
| where timestamp > ago(1h)
| where name in ("decision_processed", "receipt_stored")
| extend processing_time = todouble(customDimensions.processing_time_ms)
| extend event_type = tostring(customDimensions.event_type)
| summarize
    p50 = percentile(processing_time, 50),
    p95 = percentile(processing_time, 95),
    p99 = percentile(processing_time, 99)
  by bin(timestamp, 5m), event_type
| render timechart
```

## Implementation Guidelines

### 1. Service Integration

Each OCN service MUST:

1. **Emit structured logs** using the standardized JSON format
2. **Include trace_id** in every log entry for correlation
3. **Use custom_dimensions** for business metrics
4. **Implement health checks** that emit to Application Insights
5. **Set service identification** via environment variables

### 2. Logging Best Practices

```python
# Example implementation
from src.orca.logging_setup import get_traced_logger
import json

logger = get_traced_logger(__name__)

# Business event logging
logger.info(
    "Decision processed",
    extra={
        "custom_dimensions": {
            "decision_result": "APPROVE",
            "risk_score": 0.15,
            "processing_time_ms": 45,
            "rules_triggered": ["velocity_check", "mcc_validation"]
        }
    }
)
```

### 3. Alert Configuration

Set up alerts for:

- **High Error Rate**: >5% error rate in any service
- **High Latency**: P95 processing time >500ms
- **Low Explanation Rate**: <70% decisions with explanations
- **Service Down**: No logs from a service for >5 minutes

### 4. Data Retention

- **Raw logs**: 90 days
- **Aggregated metrics**: 1 year
- **Custom dashboards**: Indefinite (backed up to Git)

## Security Considerations

### 1. Data Redaction

All sensitive data MUST be redacted in logs:
- PAN numbers → `[PAN_REDACTED]`
- CVV codes → `[CVV_REDACTED]`
- Email addresses → `[EMAIL_REDACTED]`
- Expiry dates → `[EXPIRY_REDACTED]`

### 2. Access Control

- Application Insights: RBAC with minimal required permissions
- Log Analytics: Reader access for monitoring team
- Dashboards: Shared with appropriate stakeholders

### 3. Compliance

- **PCI DSS**: No cardholder data in logs
- **GDPR**: Personal data redaction and retention policies
- **SOC 2**: Audit trail for all system activities

## Monitoring SLA

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Decision Processing Time (P95) | <200ms | >500ms |
| Receipt Storage Time (P95) | <50ms | >100ms |
| Error Rate | <1% | >5% |
| Service Availability | >99.9% | <99% |
| Explanation Rate | >80% | <70% |

## Troubleshooting Guide

### Common Issues

1. **Missing trace_id**: Ensure `ocn_common.trace` is properly initialized
2. **Custom dimensions not appearing**: Check JSON serialization of complex objects
3. **High latency alerts**: Review database queries and external API calls
4. **Low explanation rate**: Check LLM service connectivity and rate limits

### Debug Queries

```kusto
// Find requests without trace_id
customEvents
| where timestamp > ago(1h)
| where isempty(customDimensions.trace_id)
| project timestamp, name, customDimensions

// Service health check
requests
| where timestamp > ago(1h)
| where name contains "health"
| summarize count() by resultCode, bin(timestamp, 5m)
| render timechart
```

## Future Enhancements

1. **Real-time Alerting**: Azure Monitor alerts with PagerDuty integration
2. **Custom Metrics**: Business KPI tracking (approval rates, revenue impact)
3. **Distributed Tracing**: OpenTelemetry integration for request flow visualization
4. **Cost Optimization**: Log sampling and data archiving strategies
5. **Machine Learning**: Anomaly detection for unusual patterns

---

*This specification is part of the OCN observability framework and should be reviewed quarterly for updates and improvements.*
