# CloudEvents Integration Guide

This document describes the CloudEvents integration across Orca and Weave, providing event-driven architecture for decision processing and audit trails.

## Overview

The CloudEvents integration enables:

- **Event-driven decision processing**: Orca emits decision and explanation events
- **Audit trail**: Weave receives events and stores receipt hashes on blockchain
- **Schema validation**: All events conform to ocn-common schemas
- **Traceability**: End-to-end correlation using trace_id

## Architecture

```
┌─────────────┐    CloudEvents     ┌─────────────┐    Receipt Hash    ┌─────────────┐
│    Orca     │ ──────────────────► │    Weave    │ ──────────────────► │  Blockchain │
│             │                     │  Subscriber │                     │             │
└─────────────┘                     └─────────────┘                     └─────────────┘
```

## CloudEvents Schemas

All schemas are defined in `ocn-common/common/events/v1/`:

### Decision Event (`orca.decision.v1.schema.json`)
- **Type**: `ocn.orca.decision.v1`
- **Purpose**: Emit decision results from Orca
- **Data**: Full AP2 decision payload
- **Subject**: Transaction trace_id

### Explanation Event (`orca.explanation.v1.schema.json`)
- **Type**: `ocn.orca.explanation.v1`
- **Purpose**: Emit AI/LLM explanations
- **Data**: Explanation with confidence and provenance
- **Subject**: Transaction trace_id

### Audit Event (`weave.audit.v1.schema.json`)
- **Type**: `ocn.weave.audit.v1`
- **Purpose**: Audit trail for blockchain receipts
- **Data**: Receipt hash and transaction details
- **Subject**: Transaction trace_id

## Usage

### 1. Emit Decision CloudEvents

#### CLI Usage
```bash
# Emit CloudEvents with CLI
python -m orca_core.cli decide-file fixtures/requests/high_ticket_review.json --emit-ce

# Set subscriber URL via environment
export ORCA_CE_SUBSCRIBER_URL="http://localhost:8080/events"
python -m orca_core.cli decide '{"cart_total": 100.0}' --emit-ce
```

#### Programmatic Usage
```python
from src.orca.core.ce import emit_decision_event

decision_data = {
    "ap2_version": "0.1.0",
    "intent": {...},
    "cart": {...},
    "payment": {...},
    "decision": {
        "result": "APPROVE",
        "risk_score": 0.15,
        "reasons": ["low_risk"],
        "actions": ["process_payment"],
        "meta": {}
    },
    "signing": {
        "vc_proof": None,
        "receipt_hash": "sha256:abc123"
    }
}

# Emit decision CloudEvent
ce = emit_decision_event(decision_data, "txn_1234567890abcdef")
```

### 2. Emit Explanation CloudEvents

```python
from src.orca.core.ce import emit_explanation_event

explanation_data = {
    "trace_id": "txn_1234567890abcdef",
    "decision_result": "APPROVE",
    "explanation": "Transaction approved based on low risk indicators...",
    "confidence": 0.85,
    "key_factors": ["low_velocity", "trusted_payment"],
    "model_provenance": {
        "model_name": "gpt-4o-mini",
        "provider": "azure_openai",
        "version": "1.0.0",
        "timestamp": "2024-01-01T12:00:00Z",
        "processing_time_ms": 250,
        "tokens_used": 150
    },
    "risk_score": 0.15,
    "reason_codes": ["VELOCITY_OK"]
}

# Emit explanation CloudEvent
ce = emit_explanation_event(explanation_data, "txn_1234567890abcdef")
```

### 3. Weave Subscriber

#### Start Weave Subscriber
```bash
# Start the subscriber server
cd weave
python subscriber.py
```

#### Endpoints
- `POST /events` - Receive CloudEvents
- `GET /health` - Health check
- `GET /receipts/{trace_id}` - Retrieve receipt information

#### Example CloudEvent POST
```bash
curl -X POST http://localhost:8080/events \
  -H "Content-Type: application/cloudevents+json" \
  -d '{
    "specversion": "1.0",
    "id": "decision-123",
    "source": "https://orca.ocn.ai/decision-engine",
    "type": "ocn.orca.decision.v1",
    "subject": "txn_1234567890abcdef",
    "time": "2024-01-01T12:00:00Z",
    "data": {...}
  }'
```

## Configuration

### Environment Variables

```bash
# Orca CloudEvents Configuration
export ORCA_CE_SUBSCRIBER_URL="http://localhost:8080/events"
export ORCA_CE_SOURCE_URI="https://orca.ocn.ai/decision-engine"

# Weave Configuration
export WEAVE_ENDPOINT="http://localhost:8545"
```

### Configuration Files

No additional configuration files required - all configuration is done via environment variables.

## Testing

### Run CloudEvents Tests
```bash
# Run all CloudEvents tests
PYTHONPATH=src python -m pytest tests/events/ -v

# Run specific test files
PYTHONPATH=src python -m pytest tests/events/test_decision_ce.py -v
PYTHONPATH=src python -m pytest tests/events/test_explanation_ce.py -v
PYTHONPATH=src python -m pytest tests/events/test_weave_subscriber.py -v
```

### Test Schema Validation
```bash
# Validate schemas
python -c "
import json
import jsonschema

# Load and validate decision schema
with open('ocn-common/common/events/v1/orca.decision.v1.schema.json') as f:
    schema = json.load(f)
    jsonschema.Draft202012Validator.check_schema(schema)
    print('✅ Decision schema is valid')
"
```

### Test Round-trip Integration
```bash
# Test Orca → Weave round-trip
export ORCA_CE_SUBSCRIBER_URL="http://localhost:8080/events"

# Start Weave subscriber in background
python weave/subscriber.py &

# Emit CloudEvent from Orca
python -m orca_core.cli decide '{"cart_total": 100.0}' --emit-ce

# Check receipt
curl http://localhost:8080/receipts/txn_cli_test_123456
```

## Monitoring and Observability

### CloudEvent Metadata
Each CloudEvent includes:
- **id**: Unique event identifier
- **source**: Event producer URI
- **subject**: Transaction trace_id for correlation
- **time**: Event timestamp
- **dataschema**: Schema URI for validation

### Audit Trail
Weave provides complete audit trail:
- Receipt hash for each decision/explanation
- Blockchain transaction hash
- Block height and timestamp
- Gas usage metrics

### Health Checks
```bash
# Check Orca CloudEvents health
curl http://localhost:8000/health

# Check Weave subscriber health
curl http://localhost:8080/health
```

## Security Considerations

### Schema Validation
- All CloudEvents validated against ocn-common schemas
- Malformed events rejected with 400 status
- Unknown event types logged as warnings

### HTTPS and Authentication
- Production deployments should use HTTPS
- Consider adding API keys or OAuth for subscriber authentication
- Validate source URIs to prevent spoofing

### Data Privacy
- Only receipt hashes stored on blockchain
- Original decision/explanation data not persisted
- Trace IDs used for correlation only

## Troubleshooting

### Common Issues

#### CloudEvent Emission Fails
```bash
# Check subscriber URL
echo $ORCA_CE_SUBSCRIBER_URL

# Test connectivity
curl -v $ORCA_CE_SUBSCRIBER_URL/health
```

#### Schema Validation Errors
```bash
# Validate event manually
python -c "
import json
from src.orca.core.ce import CloudEvent

# Test event creation
ce = CloudEvent(
    id='test',
    source='https://orca.ocn.ai/decision-engine',
    type='ocn.orca.decision.v1',
    subject='txn_test123',
    time='2024-01-01T12:00:00Z',
    data={'test': 'data'}
)
print('✅ Event created successfully')
"
```

#### Weave Connection Issues
```bash
# Check Weave endpoint
curl $WEAVE_ENDPOINT

# Test receipt storage
python -c "
from weave.subscriber import WeaveClient
client = WeaveClient()
receipt = client.store_receipt('txn_test', 'sha256:test', 'decision')
print(f'✅ Receipt stored: {receipt.transaction_hash}')
"
```

## Future Enhancements

### Planned Features
- **Event replay**: Replay events from blockchain
- **Batch processing**: Support for batch CloudEvents
- **Dead letter queue**: Handle failed event processing
- **Metrics**: CloudEvents emission and processing metrics
- **Compression**: Compress large event payloads

### Integration Points
- **Event bus**: Integration with Kafka/RabbitMQ
- **Monitoring**: Prometheus metrics for CloudEvents
- **Alerting**: Alerts for failed event processing
- **Analytics**: Event processing analytics and dashboards

## References

- [CloudEvents Specification](https://cloudevents.io/)
- [ocn-common Schemas](https://github.com/ocn-ai/ocn-common)
- [AP2 Contract Documentation](./ap2_contract.md)
- [Weave Integration Guide](../weave/README.md)
