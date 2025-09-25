# AP2 Contract Specification

## Overview

The Agent Protocol v2 (AP2) contract defines the standardized format for payment decision requests and responses across the Open Checkout Network (OCN). This specification ensures interoperability between different agents and services.

## Contract Version

- **Version**: 0.1.0
- **Content Type**: `application/vnd.ocn.ap2+json; version=1`
- **Schema Version**: v1

## Structure

An AP2 contract consists of the following top-level components:

```json
{
  "ap2_version": "0.1.0",
  "intent": { /* Intent Mandate */ },
  "cart": { /* Cart Mandate */ },
  "payment": { /* Payment Mandate */ },
  "decision": { /* Decision Result */ },
  "signing": { /* Digital Signing */ }
}
```

## Mandates

### Intent Mandate

Defines the actor performing the transaction and the context in which it occurs.

**Required Fields:**
- `actor.id`: Unique identifier for the actor
- `actor.type`: Type of actor (`user`, `merchant`, `agent`)
- `channel`: Transaction channel (`web`, `mobile`, `pos`, `api`, `voice`)
- `geo`: Geographic context (country, region, city, timezone)
- `metadata`: Additional context metadata

**Example:**
```json
{
  "actor": {
    "id": "user_12345",
    "type": "user",
    "profile": {
      "identity": {
        "verified": true,
        "verification_level": "enhanced",
        "kyc_status": "approved"
      },
      "risk_profile": {
        "risk_score": 0.15,
        "risk_category": "low",
        "velocity_flags": []
      }
    }
  },
  "channel": "web",
  "geo": {
    "country": "US",
    "region": "CA",
    "city": "San Francisco",
    "timezone": "America/Los_Angeles"
  },
  "metadata": {
    "session_id": "sess_abc123",
    "user_agent": "Mozilla/5.0..."
  }
}
```

### Cart Mandate

Defines the shopping cart contents and total value.

**Required Fields:**
- `amount`: Total cart amount in decimal format (e.g., "99.99")
- `currency`: ISO 4217 currency code (e.g., "USD")
- `items`: Array of cart items
- `geo`: Cart geographic context
- `metadata`: Additional cart metadata

**Example:**
```json
{
  "amount": "99.99",
  "currency": "USD",
  "items": [
    {
      "id": "item_001",
      "name": "Wireless Headphones",
      "amount": "79.99",
      "quantity": 1,
      "category": "Electronics",
      "mcc": "5733"
    }
  ],
  "geo": {
    "country": "US",
    "region": "CA",
    "city": "San Francisco"
  },
  "metadata": {
    "merchant_id": "merchant_123",
    "order_id": "order_456"
  }
}
```

### Payment Mandate

Defines the payment method and processing requirements.

**Required Fields:**
- `method`: Payment method type (`card`, `ach`, `wallet`, `crypto`, `cash`, `check`)
- `modality`: Payment timing and processing details
- `auth_requirements`: Array of required authentication factors
- `metadata`: Payment method metadata

**Example:**
```json
{
  "method": "card",
  "modality": {
    "type": "immediate",
    "description": "Immediate payment processing"
  },
  "auth_requirements": ["pin", "biometric"],
  "metadata": {
    "card_brand": "visa",
    "last_four": "1234"
  }
}
```

## Decision Result

Contains the decision outcome and supporting information.

**Required Fields:**
- `result`: Decision result (`APPROVE`, `DECLINE`, `REVIEW`)
- `risk_score`: Risk score between 0 and 1
- `reasons`: Array of decision reasoning
- `actions`: Array of recommended actions
- `meta`: Additional decision metadata

**Example:**
```json
{
  "result": "APPROVE",
  "risk_score": 0.15,
  "reasons": [
    "Low risk transaction",
    "Verified user with good history",
    "Amount within normal limits"
  ],
  "actions": [
    "Process payment immediately",
    "Update user transaction history"
  ],
  "meta": {
    "model_version": "0.1.0",
    "processing_time_ms": 45,
    "rules_triggered": ["low_risk_threshold", "verified_user"]
  }
}
```

## Digital Signing

Contains digital signing and receipt information.

**Fields:**
- `vc_proof`: Verifiable credential proof (optional)
- `receipt_hash`: Receipt hash for audit trail

**Example:**
```json
{
  "vc_proof": null,
  "receipt_hash": "sha256:abc123def456789"
}
```

## Validation

All AP2 contracts must be validated against the JSON schemas defined in `common/mandates/`:

- `intent_mandate.schema.json`
- `cart_mandate.schema.json`
- `payment_mandate.schema.json`
- `actor_profile.schema.json`
- `agent_presence.schema.json`
- `modality.schema.json`

## Usage

```python
from ocn_common.contracts import validate_json

# Validate individual mandates
validate_json(intent_data, "intent_mandate")
validate_json(cart_data, "cart_mandate")
validate_json(payment_data, "payment_mandate")
```

## Examples

See the `examples/ap2/` directory for complete AP2 contract examples:

- `approve.json`: Approved transaction example
- `decline.json`: Declined transaction example
- `review.json`: Manual review transaction example
