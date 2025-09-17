# AP2 Decision Contract Specification

The AP2 (Agent Protocol v2) Decision Contract is Orca's standardized format for representing payment decisions with full transparency, explainability, and cryptographic integrity.

## Overview

The AP2 contract provides a comprehensive, structured representation of payment decisions that includes:

- **Intent**: What the customer wants to do
- **Cart**: What they're purchasing
- **Payment**: How they want to pay
- **Decision**: The outcome with full reasoning
- **Signing**: Cryptographic proof of decision integrity

## Contract Structure

```json
{
  "ap2_version": "0.1.0",
  "intent": { /* Customer intent and context */ },
  "cart": { /* Transaction details */ },
  "payment": { /* Payment method and requirements */ },
  "decision": { /* Decision outcome and reasoning */ },
  "signing": { /* Cryptographic signatures and hashes */ }
}
```

## Side-by-Side Comparison: Legacy vs AP2

### Legacy Decision Format (v0)
```json
{
  "decision": "APPROVE",
  "risk_score": 0.15,
  "reasons": ["velocity_flag", "mcc_risk"],
  "actions": ["ROUTE:PROCESSOR_A"],
  "meta": {
    "trace_id": "uuid-1234",
    "routing_hint": "LOW_RISK_ROUTING",
    "explain": "Transaction approved based on low risk indicators"
  }
}
```

### AP2 Decision Format (v0.1.0)
```json
{
  "ap2_version": "0.1.0",
  "intent": {
    "actor": {
      "id": "customer_123",
      "type": "individual",
      "metadata": {
        "loyalty_score": 0.8,
        "age_days": 365,
        "chargebacks_12m": 0
      }
    },
    "channel": "web",
    "geo": {
      "country": "US",
      "region": "CA",
      "city": "San Francisco"
    },
    "metadata": {
      "velocity_24h": 2.0,
      "velocity_7d": 5.0,
      "session_duration": 300
    }
  },
  "cart": {
    "amount": "89.99",
    "currency": "USD",
    "items": [
      {
        "name": "Software License",
        "category": "software",
        "mcc": "5734"
      }
    ],
    "geo": {
      "country": "US",
      "region": "CA"
    }
  },
  "payment": {
    "method": "card",
    "modality": "immediate",
    "auth_requirements": ["none"],
    "metadata": {
      "method_risk": 0.2,
      "bin_country": "US"
    }
  },
  "decision": {
    "result": "APPROVE",
    "risk_score": 0.15,
    "reasons": [
      {
        "type": "velocity_check",
        "message": "Transaction velocity within normal limits",
        "confidence": 0.9
      }
    ],
    "actions": [
      {
        "type": "route",
        "target": "PROCESSOR_A",
        "reason": "Low risk routing"
      }
    ],
    "meta": {
      "model": "model:xgb",
      "model_version": "1.0.0",
      "trace_id": "uuid-1234",
      "processing_time_ms": 45,
      "version": "0.1.0"
    }
  },
  "signing": {
    "vc_proof": {
      "type": "Ed25519Signature2020",
      "created": "2024-01-15T10:30:00Z",
      "verificationMethod": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
      "proofPurpose": "assertionMethod",
      "jws": "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..."
    },
    "receipt_hash": "sha256:abc123def456..."
  }
}
```

## Field Mapping Guide

### Where to Find Common Fields

| Field | Legacy Location | AP2 Location | Notes |
|-------|----------------|--------------|-------|
| **MCC** | `mcc` | `cart.items[].mcc` | Merchant Category Code |
| **Amount** | `amount` | `cart.amount` | Transaction amount (Decimal) |
| **Currency** | `currency` | `cart.currency` | ISO 4217 currency code |
| **Payment Method** | `payment_method` | `payment.method` | "card", "ach", "wallet" |
| **Modality** | `rail` | `payment.modality` | "immediate", "deferred" |
| **Agent Presence** | `agent_present` | `intent.metadata.agent_present` | Boolean flag |
| **Velocity** | `velocity_24h` | `intent.metadata.velocity_24h` | Transaction frequency |
| **Cross Border** | `cross_border` | `cart.geo.country != intent.geo.country` | Calculated field |
| **Customer ID** | `customer_id` | `intent.actor.id` | Customer identifier |
| **Channel** | `channel` | `intent.channel` | "web", "pos", "mobile" |
| **Risk Score** | `risk_score` | `decision.risk_score` | ML risk assessment |
| **Decision** | `decision` | `decision.result` | "APPROVE", "DECLINE", "REVIEW" |
| **Reasons** | `reasons[]` | `decision.reasons[]` | Array of reason objects |
| **Actions** | `actions[]` | `decision.actions[]` | Array of action objects |
| **Trace ID** | `meta.trace_id` | `decision.meta.trace_id` | Request tracking ID |
| **Model** | `meta.model` | `decision.meta.model` | ML model identifier |
| **Model Version** | `meta.model_version` | `decision.meta.model_version` | Model version |

### AP2-Specific Fields

| Field | Location | Description |
|-------|----------|-------------|
| **AP2 Version** | `ap2_version` | Contract version identifier |
| **Actor Type** | `intent.actor.type` | "individual", "business", "system" |
| **Loyalty Score** | `intent.actor.metadata.loyalty_score` | Customer loyalty metric |
| **Customer Age** | `intent.actor.metadata.age_days` | Account age in days |
| **Chargebacks** | `intent.actor.metadata.chargebacks_12m` | 12-month chargeback count |
| **Session Duration** | `intent.metadata.session_duration` | Session length in seconds |
| **Auth Requirements** | `payment.auth_requirements[]` | Required authentication methods |
| **Method Risk** | `payment.metadata.method_risk` | Payment method risk score |
| **BIN Country** | `payment.metadata.bin_country` | Bank Identification Number country |
| **Processing Time** | `decision.meta.processing_time_ms` | Decision processing time |
| **VC Proof** | `signing.vc_proof` | Verifiable credential proof |
| **Receipt Hash** | `signing.receipt_hash` | Decision receipt hash |

## Intent Section

The `intent` section describes what the customer wants to do and their context.

```json
{
  "intent": {
    "actor": {
      "id": "customer_123",
      "type": "individual",
      "metadata": {
        "loyalty_score": 0.8,
        "age_days": 365,
        "chargebacks_12m": 0,
        "time_since_last_purchase": 7.0
      }
    },
    "channel": "web",
    "geo": {
      "country": "US",
      "region": "CA",
      "city": "San Francisco",
      "postal_code": "94105"
    },
    "metadata": {
      "velocity_24h": 2.0,
      "velocity_7d": 5.0,
      "session_duration": 300,
      "agent_present": false,
      "device_fingerprint": "fp_abc123"
    }
  }
}
```

### Intent Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `actor.id` | string | Customer identifier | "customer_123" |
| `actor.type` | enum | Actor type | "individual", "business", "system" |
| `actor.metadata.loyalty_score` | float | Customer loyalty (0-1) | 0.8 |
| `actor.metadata.age_days` | float | Account age in days | 365.0 |
| `actor.metadata.chargebacks_12m` | float | 12-month chargebacks | 0.0 |
| `channel` | enum | Transaction channel | "web", "pos", "mobile" |
| `geo.country` | string | ISO 3166-1 country | "US" |
| `geo.region` | string | State/province | "CA" |
| `geo.city` | string | City name | "San Francisco" |
| `metadata.velocity_24h` | float | 24-hour transaction count | 2.0 |
| `metadata.velocity_7d` | float | 7-day transaction count | 5.0 |
| `metadata.session_duration` | float | Session length (seconds) | 300.0 |
| `metadata.agent_present` | boolean | Agent assistance flag | false |

## Cart Section

The `cart` section describes what the customer is purchasing.

```json
{
  "cart": {
    "amount": "89.99",
    "currency": "USD",
    "items": [
      {
        "name": "Software License",
        "category": "software",
        "mcc": "5734",
        "quantity": 1,
        "unit_price": "89.99"
      }
    ],
    "geo": {
      "country": "US",
      "region": "CA"
    }
  }
}
```

### Cart Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `amount` | string | Total amount (Decimal) | "89.99" |
| `currency` | string | ISO 4217 currency | "USD" |
| `items[].name` | string | Item name | "Software License" |
| `items[].category` | string | Item category | "software" |
| `items[].mcc` | string | Merchant Category Code | "5734" |
| `items[].quantity` | integer | Item quantity | 1 |
| `items[].unit_price` | string | Unit price (Decimal) | "89.99" |
| `geo.country` | string | Merchant country | "US" |
| `geo.region` | string | Merchant region | "CA" |

## Payment Section

The `payment` section describes how the customer wants to pay.

```json
{
  "payment": {
    "method": "card",
    "modality": "immediate",
    "auth_requirements": ["none"],
    "metadata": {
      "method_risk": 0.2,
      "bin_country": "US",
      "card_type": "credit",
      "issuer": "Visa"
    }
  }
}
```

### Payment Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `method` | enum | Payment method | "card", "ach", "wallet" |
| `modality` | enum | Payment timing | "immediate", "deferred" |
| `auth_requirements[]` | array | Required auth methods | ["none", "pin", "biometric"] |
| `metadata.method_risk` | float | Method risk score (0-1) | 0.2 |
| `metadata.bin_country` | string | BIN country | "US" |
| `metadata.card_type` | string | Card type | "credit", "debit" |
| `metadata.issuer` | string | Card issuer | "Visa", "Mastercard" |

## Decision Section

The `decision` section contains the outcome and reasoning.

```json
{
  "decision": {
    "result": "APPROVE",
    "risk_score": 0.15,
    "reasons": [
      {
        "type": "velocity_check",
        "message": "Transaction velocity within normal limits",
        "confidence": 0.9,
        "ap2_path": "intent.metadata.velocity_24h"
      }
    ],
    "actions": [
      {
        "type": "route",
        "target": "PROCESSOR_A",
        "reason": "Low risk routing",
        "metadata": {
          "processor_fee": "0.029"
        }
      }
    ],
    "meta": {
      "model": "model:xgb",
      "model_version": "1.0.0",
      "model_sha256": "abc123def456",
      "model_trained_on": "2024-01-01",
      "trace_id": "uuid-1234",
      "processing_time_ms": 45,
      "version": "0.1.0"
    }
  }
}
```

### Decision Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `result` | enum | Decision outcome | "APPROVE", "DECLINE", "REVIEW" |
| `risk_score` | float | ML risk score (0-1) | 0.15 |
| `reasons[].type` | string | Reason type | "velocity_check" |
| `reasons[].message` | string | Human-readable reason | "Velocity within limits" |
| `reasons[].confidence` | float | Reason confidence (0-1) | 0.9 |
| `reasons[].ap2_path` | string | AP2 field reference | "intent.metadata.velocity_24h" |
| `actions[].type` | string | Action type | "route", "step_up", "capture" |
| `actions[].target` | string | Action target | "PROCESSOR_A" |
| `actions[].reason` | string | Action reason | "Low risk routing" |
| `meta.model` | string | ML model identifier | "model:xgb" |
| `meta.model_version` | string | Model version | "1.0.0" |
| `meta.model_sha256` | string | Model hash | "abc123def456" |
| `meta.model_trained_on` | string | Training date | "2024-01-01" |
| `meta.trace_id` | string | Request tracking ID | "uuid-1234" |
| `meta.processing_time_ms` | integer | Processing time | 45 |
| `meta.version` | string | Decision version | "0.1.0" |

## Signing Section

The `signing` section provides cryptographic proof of decision integrity.

### Verifiable Credentials (VC Proof)

When `ORCA_SIGN_DECISIONS=true` and `ORCA_RECEIPT_HASH_ONLY=false`:

```json
{
  "signing": {
    "vc_proof": {
      "type": "Ed25519Signature2020",
      "created": "2024-01-15T10:30:00Z",
      "verificationMethod": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
      "proofPurpose": "assertionMethod",
      "jws": "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..."
    },
    "receipt_hash": "sha256:abc123def456..."
  }
}
```

### Receipt Hash Only

When `ORCA_RECEIPT_HASH_ONLY=true`:

```json
{
  "signing": {
    "vc_proof": null,
    "receipt_hash": "sha256:abc123def456..."
  }
}
```

### Signing Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `vc_proof.type` | string | Signature type | "Ed25519Signature2020" |
| `vc_proof.created` | string | Signature timestamp | "2024-01-15T10:30:00Z" |
| `vc_proof.verificationMethod` | string | Public key identifier | "did:key:z6Mk..." |
| `vc_proof.proofPurpose` | string | Proof purpose | "assertionMethod" |
| `vc_proof.jws` | string | JSON Web Signature | "eyJhbGciOiJFZERTQS..." |
| `receipt_hash` | string | Decision hash | "sha256:abc123def456..." |

## Cryptographic Signatures and Receipts

### Why Only Hashes Are Stored (Weave Integration)

Orca uses a **receipt-based approach** for decision integrity:

1. **Decision Hash**: Each decision is hashed using SHA-256
2. **Receipt Storage**: Only the hash is stored in the Weave blockchain
3. **Verification**: Full decisions can be verified against stored hashes
4. **Privacy**: Sensitive transaction data is not stored on-chain
5. **Efficiency**: Minimal blockchain storage requirements

### Signature Process

1. **Data Sanitization**: Remove sensitive fields (PII, card numbers)
2. **Canonical JSON**: Convert to deterministic JSON format
3. **Hash Generation**: Create SHA-256 hash of sanitized data
4. **Digital Signature**: Sign hash with Ed25519 private key
5. **VC Proof**: Create W3C-compliant verifiable credential
6. **Receipt Storage**: Store hash in Weave blockchain

### Verification Process

1. **Hash Extraction**: Extract receipt hash from decision
2. **Data Sanitization**: Sanitize decision data (same process)
3. **Hash Calculation**: Calculate hash of sanitized data
4. **Hash Comparison**: Compare calculated hash with stored hash
5. **Signature Verification**: Verify Ed25519 signature
6. **VC Validation**: Validate verifiable credential proof

## Migration from Legacy Format

### Using the Legacy Adapter

```python
from src.orca.core.decision_legacy_adapter import DecisionLegacyAdapter

# Convert legacy to AP2
adapter = DecisionLegacyAdapter()
ap2_contract = adapter.from_legacy(legacy_data)

# Convert AP2 to legacy
legacy_data = adapter.to_legacy(ap2_contract)
```

### Field Mapping Examples

| Legacy Field | AP2 Field | Notes |
|--------------|-----------|-------|
| `rail: "Card"` | `payment.modality: "immediate"` | Card = immediate |
| `rail: "ACH"` | `payment.modality: "deferred"` | ACH = deferred |
| `channel: "online"` | `intent.channel: "web"` | online = web |
| `channel: "pos"` | `intent.channel: "pos"` | pos = pos |
| `amount: 89.99` | `cart.amount: "89.99"` | Convert to Decimal string |
| `mcc: "5734"` | `cart.items[0].mcc: "5734"` | Move to cart items |

## Examples

### Low-Risk Card Transaction

```json
{
  "ap2_version": "0.1.0",
  "intent": {
    "actor": {
      "id": "customer_123",
      "type": "individual",
      "metadata": {
        "loyalty_score": 0.8,
        "age_days": 365,
        "chargebacks_12m": 0
      }
    },
    "channel": "web",
    "geo": {
      "country": "US",
      "region": "CA"
    },
    "metadata": {
      "velocity_24h": 1.0,
      "velocity_7d": 3.0
    }
  },
  "cart": {
    "amount": "89.99",
    "currency": "USD",
    "items": [
      {
        "name": "Software License",
        "category": "software",
        "mcc": "5734"
      }
    ]
  },
  "payment": {
    "method": "card",
    "modality": "immediate",
    "auth_requirements": ["none"],
    "metadata": {
      "method_risk": 0.2
    }
  },
  "decision": {
    "result": "APPROVE",
    "risk_score": 0.15,
    "reasons": [
      {
        "type": "low_risk",
        "message": "Low risk transaction",
        "confidence": 0.9
      }
    ],
    "actions": [
      {
        "type": "route",
        "target": "PROCESSOR_A"
      }
    ],
    "meta": {
      "model": "model:xgb",
      "model_version": "1.0.0",
      "trace_id": "uuid-1234",
      "processing_time_ms": 45,
      "version": "0.1.0"
    }
  },
  "signing": {
    "vc_proof": null,
    "receipt_hash": "sha256:abc123def456..."
  }
}
```

### High-Risk Transaction with Review

```json
{
  "ap2_version": "0.1.0",
  "intent": {
    "actor": {
      "id": "customer_456",
      "type": "individual",
      "metadata": {
        "loyalty_score": 0.2,
        "age_days": 30,
        "chargebacks_12m": 2
      }
    },
    "channel": "web",
    "geo": {
      "country": "US",
      "region": "NY"
    },
    "metadata": {
      "velocity_24h": 8.0,
      "velocity_7d": 25.0
    }
  },
  "cart": {
    "amount": "2500.00",
    "currency": "USD",
    "items": [
      {
        "name": "Electronics",
        "category": "electronics",
        "mcc": "5732"
      }
    ]
  },
  "payment": {
    "method": "card",
    "modality": "immediate",
    "auth_requirements": ["3ds"],
    "metadata": {
      "method_risk": 0.6
    }
  },
  "decision": {
    "result": "REVIEW",
    "risk_score": 0.75,
    "reasons": [
      {
        "type": "high_velocity",
        "message": "High transaction velocity detected",
        "confidence": 0.95,
        "ap2_path": "intent.metadata.velocity_24h"
      },
      {
        "type": "high_amount",
        "message": "Transaction amount exceeds threshold",
        "confidence": 0.9,
        "ap2_path": "cart.amount"
      }
    ],
    "actions": [
      {
        "type": "step_up",
        "target": "3DS",
        "reason": "Additional authentication required"
      }
    ],
    "meta": {
      "model": "model:xgb",
      "model_version": "1.0.0",
      "trace_id": "uuid-5678",
      "processing_time_ms": 120,
      "version": "0.1.0"
    }
  },
  "signing": {
    "vc_proof": null,
    "receipt_hash": "sha256:def456ghi789..."
  }
}
```

## Validation

### Schema Validation

```python
from src.orca.core.decision_contract import AP2DecisionContract

# Validate AP2 contract
contract = AP2DecisionContract(**ap2_data)
print("✅ Valid AP2 contract")
```

### Field Reference Validation

All `ap2_path` references in reasons must point to valid AP2 fields:

```python
# Valid AP2 paths
valid_paths = [
    "intent.metadata.velocity_24h",
    "cart.amount",
    "payment.method",
    "intent.actor.metadata.loyalty_score"
]

# Invalid AP2 paths (will cause validation errors)
invalid_paths = [
    "user.profile",  # Non-existent field
    "transaction.metadata",  # Non-existent field
    "system.config"  # Non-existent field
]
```

## Best Practices

### 1. Field References
- Always use valid AP2 JSONPath expressions
- Reference actual fields in the contract
- Avoid hardcoded or non-existent field paths

### 2. Data Types
- Use Decimal strings for monetary amounts
- Use proper enum values for categorical fields
- Maintain consistent data types across versions

### 3. Metadata
- Include comprehensive model metadata
- Track processing times for performance monitoring
- Use consistent trace IDs for request tracking

### 4. Signing
- Always include receipt hashes for integrity
- Use VC proofs for high-value transactions
- Sanitize sensitive data before signing

### 5. Versioning
- Increment version numbers for breaking changes
- Maintain backward compatibility where possible
- Document migration paths for version changes

## Related Documentation

- [Migration Guide](migration_guide_ap2.md) - How to migrate from legacy format
- [Explainability Guide](phase2_explainability.md) - How explanations work with AP2
- [Keys & Secrets](keys.md) - Cryptographic key management
- [API Reference](../src/orca/core/decision_contract.py) - Python API documentation
