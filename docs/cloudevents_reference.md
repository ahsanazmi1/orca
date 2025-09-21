# CloudEvents Reference

## Overview

This document describes the CloudEvents specifications used in the Open Checkout Network (OCN). All events follow the CloudEvents v1.0 specification and include standardized attributes and data payloads.

## CloudEvents v1.0 Specification

All OCN CloudEvents must include the following required attributes:

- `specversion`: Always "1.0"
- `id`: Unique identifier for the event
- `source`: URI reference indicating the context in which the event occurred
- `type`: Event type identifier
- `subject`: Subject of the event (typically trace_id)
- `time`: ISO 8601 timestamp when the event occurred
- `data`: Event payload

Optional attributes:
- `datacontenttype`: Content type of the data (default: "application/vnd.ocn.ap2+json; version=1")
- `dataschema`: URI reference to the schema that the data adheres to

## Event Types

### Decision Events

#### ocn.orca.decision.v1

Emitted when Orca makes a payment decision.

**Event Type**: `ocn.orca.decision.v1`

**Source**: `https://orca.ocn.ai/v1`

**Data Schema**: AP2 decision contract

**Example**:
```json
{
  "specversion": "1.0",
  "id": "evt_12345",
  "source": "https://orca.ocn.ai/v1",
  "type": "ocn.orca.decision.v1",
  "subject": "txn_67890",
  "time": "2024-01-21T12:00:00Z",
  "datacontenttype": "application/vnd.ocn.ap2+json; version=1",
  "dataschema": "https://schemas.ocn.ai/ap2/v1/decision.schema.json",
  "data": {
    "ap2_version": "0.1.0",
    "intent": { /* Intent Mandate */ },
    "cart": { /* Cart Mandate */ },
    "payment": { /* Payment Mandate */ },
    "decision": {
      "result": "APPROVE",
      "risk_score": 0.15,
      "reasons": ["Low risk transaction"],
      "actions": ["Process payment"],
      "meta": {}
    },
    "signing": {
      "vc_proof": null,
      "receipt_hash": "sha256:abc123"
    }
  }
}
```

### Explanation Events

#### ocn.orca.explanation.v1

Emitted when Orca provides an explanation for a decision.

**Event Type**: `ocn.orca.explanation.v1`

**Source**: `https://orca.ocn.ai/v1`

**Data Schema**: Explanation contract

**Example**:
```json
{
  "specversion": "1.0",
  "id": "evt_54321",
  "source": "https://orca.ocn.ai/v1",
  "type": "ocn.orca.explanation.v1",
  "subject": "txn_67890",
  "time": "2024-01-21T12:00:01Z",
  "datacontenttype": "application/vnd.ocn.ap2+json; version=1",
  "dataschema": "https://schemas.ocn.ai/ap2/v1/explanation.schema.json",
  "data": {
    "explanation_version": "0.1.0",
    "trace_id": "txn_67890",
    "decision_id": "evt_12345",
    "explanation": {
      "reason": "Transaction approved based on low risk profile",
      "key_signals": [
        {
          "signal": "user_verification_status",
          "value": "verified",
          "impact": "positive",
          "weight": 0.3
        }
      ],
      "mitigation": ["Enhanced monitoring"],
      "confidence": 0.92
    },
    "metadata": {
      "model_version": "0.1.0",
      "explanation_method": "rule_based"
    }
  }
}
```

### Audit Events

#### ocn.weave.audit.v1

Emitted when Weave stores a receipt for audit purposes.

**Event Type**: `ocn.weave.audit.v1`

**Source**: `https://weave.ocn.ai/v1`

**Data Schema**: Audit contract

**Example**:
```json
{
  "specversion": "1.0",
  "id": "evt_98765",
  "source": "https://weave.ocn.ai/v1",
  "type": "ocn.weave.audit.v1",
  "subject": "txn_67890",
  "time": "2024-01-21T12:00:02Z",
  "datacontenttype": "application/vnd.ocn.ap2+json; version=1",
  "dataschema": "https://schemas.ocn.ai/audit/v1/audit.schema.json",
  "data": {
    "audit_version": "0.1.0",
    "trace_id": "txn_67890",
    "receipt_hash": "sha256:def456789",
    "event_type": "ocn.orca.decision.v1",
    "block_height": 1234567,
    "transaction_hash": "0xabc123def456789",
    "status": "confirmed",
    "original_event_id": "evt_12345",
    "storage_metadata": {
      "storage_provider": "weave_v1",
      "replication_factor": 3,
      "encryption": {
        "algorithm": "AES-256",
        "key_id": "key_789"
      }
    },
    "verification": {
      "verified": true,
      "verification_method": "merkle_proof",
      "verification_timestamp": "2024-01-21T12:00:05Z"
    },
    "metadata": {
      "network": "mainnet",
      "gas_used": 21000
    }
  }
}
```

## Event Flow

1. **Decision Event**: Orca emits `ocn.orca.decision.v1` when making a payment decision
2. **Explanation Event**: Orca emits `ocn.orca.explanation.v1` with decision reasoning
3. **Audit Event**: Weave emits `ocn.weave.audit.v1` when storing receipt

All events share the same `subject` (trace_id) for correlation.

## Validation

CloudEvents can be validated using the schemas in `common/events/v1/`:

- `orca.decision.v1.schema.json`
- `orca.explanation.v1.schema.json`
- `weave.audit.v1.schema.json`

## Usage

```python
from ocn_common.contracts import validate_cloudevent

# Validate CloudEvents
validate_cloudevent(decision_ce, "ocn.orca.decision.v1")
validate_cloudevent(explanation_ce, "ocn.orca.explanation.v1")
validate_cloudevent(audit_ce, "ocn.weave.audit.v1")
```

## Examples

See the `examples/events/` directory for complete CloudEvent examples:

- `decision_approve.json`: Decision event example
- `explanation_approve.json`: Explanation event example
- `audit_approve.json`: Audit event example

## Best Practices

1. **Event ID**: Use UUIDs or other globally unique identifiers
2. **Source URI**: Use consistent, versioned URIs for each service
3. **Subject**: Always use trace_id for event correlation
4. **Timestamp**: Use UTC ISO 8601 format
5. **Data Schema**: Always include dataschema URI for validation
6. **Content Type**: Use standardized content type for OCN events

## Security Considerations

- Events contain only hashes and metadata, never raw payment data
- All sensitive data is encrypted before storage
- Event signatures can be verified using VC proofs
- Audit trails provide immutable transaction records
