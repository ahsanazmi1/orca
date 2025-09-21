# AP2 Migration Guide

## Overview

This guide helps you migrate from legacy payment decision formats to the Agent Protocol v2 (AP2) contract specification.

## What is AP2?

AP2 is a standardized contract format for payment decisions that ensures interoperability across the Open Checkout Network (OCN). It provides:

- **Standardized Structure**: Consistent format across all agents
- **Comprehensive Context**: Rich metadata for better decision making
- **Extensibility**: Flexible schema design for future enhancements
- **Validation**: Built-in schema validation for data integrity

## Migration Checklist

### 1. Update Data Structures

**Before (Legacy)**:
```json
{
  "user_id": "12345",
  "amount": 99.99,
  "currency": "USD",
  "payment_method": "card",
  "decision": "approve"
}
```

**After (AP2)**:
```json
{
  "ap2_version": "0.1.0",
  "intent": {
    "actor": {
      "id": "user_12345",
      "type": "user"
    },
    "channel": "web",
    "geo": {
      "country": "US",
      "region": "CA",
      "city": "San Francisco"
    },
    "metadata": {}
  },
  "cart": {
    "amount": "99.99",
    "currency": "USD",
    "items": [
      {
        "id": "item_001",
        "name": "Product",
        "amount": "99.99",
        "quantity": 1,
        "category": "General"
      }
    ],
    "geo": {
      "country": "US",
      "region": "CA",
      "city": "San Francisco"
    },
    "metadata": {}
  },
  "payment": {
    "method": "card",
    "modality": {
      "type": "immediate",
      "description": "Immediate payment processing"
    },
    "auth_requirements": ["pin"],
    "metadata": {}
  },
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
```

### 2. Field Mapping

| Legacy Field | AP2 Location | Notes |
|--------------|--------------|-------|
| `user_id` | `intent.actor.id` | Renamed for clarity |
| `amount` | `cart.amount` | String format, decimal precision |
| `currency` | `cart.currency` | ISO 4217 format |
| `payment_method` | `payment.method` | Enum values only |
| `decision` | `decision.result` | Uppercase enum values |
| `risk_score` | `decision.risk_score` | 0-1 range |
| `reasons` | `decision.reasons` | Array of strings |

### 3. Data Type Changes

#### Amount Format
- **Before**: `99.99` (number)
- **After**: `"99.99"` (string with decimal format)

#### Decision Values
- **Before**: `"approve"`, `"decline"`, `"review"`
- **After**: `"APPROVE"`, `"DECLINE"`, `"REVIEW"`

#### Payment Methods
- **Before**: Free-form strings
- **After**: Enum values: `card`, `ach`, `wallet`, `crypto`, `cash`, `check`

### 4. Required Fields

Ensure all required fields are present:

#### Intent Mandate
- `actor.id` (string)
- `actor.type` (enum: user, merchant, agent)
- `channel` (enum: web, mobile, pos, api, voice)
- `geo` (object)
- `metadata` (object)

#### Cart Mandate
- `amount` (string, decimal format)
- `currency` (string, ISO 4217)
- `items` (array)
- `geo` (object)
- `metadata` (object)

#### Payment Mandate
- `method` (enum)
- `modality` (object)
- `auth_requirements` (array)
- `metadata` (object)

### 5. Validation

Use the provided validation functions:

```python
from ocn_common.contracts import validate_json

# Validate individual mandates
validate_json(intent_data, "intent_mandate")
validate_json(cart_data, "cart_mandate")
validate_json(payment_data, "payment_mandate")
```

### 6. Common Migration Patterns

#### Simple Transaction
```python
def migrate_simple_transaction(legacy_data):
    return {
        "ap2_version": "0.1.0",
        "intent": {
            "actor": {
                "id": legacy_data["user_id"],
                "type": "user"
            },
            "channel": "web",  # Default value
            "geo": {
                "country": "US"  # Default value
            },
            "metadata": {}
        },
        "cart": {
            "amount": f"{legacy_data['amount']:.2f}",
            "currency": legacy_data["currency"],
            "items": [{
                "id": "default_item",
                "name": "Transaction",
                "amount": f"{legacy_data['amount']:.2f}",
                "quantity": 1,
                "category": "General"
            }],
            "geo": {
                "country": "US"
            },
            "metadata": {}
        },
        "payment": {
            "method": legacy_data["payment_method"],
            "modality": {
                "type": "immediate",
                "description": "Immediate payment processing"
            },
            "auth_requirements": [],
            "metadata": {}
        },
        "decision": {
            "result": legacy_data["decision"].upper(),
            "risk_score": legacy_data.get("risk_score", 0.5),
            "reasons": legacy_data.get("reasons", []),
            "actions": [],
            "meta": {}
        },
        "signing": {
            "vc_proof": None,
            "receipt_hash": "sha256:placeholder"
        }
    }
```

#### Enhanced Transaction with Profile
```python
def migrate_enhanced_transaction(legacy_data, user_profile):
    intent = {
        "actor": {
            "id": legacy_data["user_id"],
            "type": "user",
            "profile": {
                "identity": {
                    "verified": user_profile.get("verified", False),
                    "verification_level": user_profile.get("verification_level", "basic"),
                    "kyc_status": user_profile.get("kyc_status", "pending")
                },
                "risk_profile": {
                    "risk_score": user_profile.get("risk_score", 0.5),
                    "risk_category": user_profile.get("risk_category", "medium"),
                    "velocity_flags": user_profile.get("velocity_flags", [])
                },
                "preferences": {
                    "language": user_profile.get("language", "en-US"),
                    "currency": legacy_data["currency"],
                    "timezone": user_profile.get("timezone", "UTC")
                },
                "metadata": user_profile.get("metadata", {})
            }
        },
        "channel": legacy_data.get("channel", "web"),
        "geo": {
            "country": legacy_data.get("country", "US"),
            "region": legacy_data.get("region"),
            "city": legacy_data.get("city"),
            "timezone": user_profile.get("timezone", "UTC")
        },
        "metadata": legacy_data.get("metadata", {})
    }

    # ... rest of AP2 structure
```

### 7. Testing Migration

1. **Validate Examples**: Use the provided examples in `examples/ap2/`
2. **Test Edge Cases**: Handle missing fields gracefully
3. **Verify Decisions**: Ensure decision logic still works with new format
4. **Performance Test**: Validate that new format doesn't impact performance

### 8. Rollback Strategy

- Keep legacy format support during transition period
- Use feature flags to switch between formats
- Monitor error rates and performance metrics
- Have rollback plan ready

## Migration Tools

### Validation Script
```python
#!/usr/bin/env python3
"""
AP2 Migration Validation Script
"""

import json
import sys
from pathlib import Path
from ocn_common.contracts import validate_json, ContractValidationError

def validate_migrated_data(file_path):
    """Validate a migrated AP2 file."""
    try:
        with open(file_path) as f:
            data = json.load(f)

        # Validate individual mandates
        validate_json(data["intent"], "intent_mandate")
        validate_json(data["cart"], "cart_mandate")
        validate_json(data["payment"], "payment_mandate")

        print(f"✅ {file_path} - Valid AP2 format")
        return True

    except ContractValidationError as e:
        print(f"❌ {file_path} - Validation error: {e}")
        return False
    except Exception as e:
        print(f"❌ {file_path} - Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_migration.py <file_path>")
        sys.exit(1)

    success = validate_migrated_data(sys.argv[1])
    sys.exit(0 if success else 1)
```

## Support

For migration support:

1. **Documentation**: Check `docs/ap2_contract.md` for detailed specifications
2. **Examples**: Use `examples/ap2/` for reference implementations
3. **Validation**: Use `ocn_common.contracts` for validation functions
4. **Community**: Join OCN community for migration assistance

## Timeline

- **Phase 1**: Schema definition and validation (✅ Complete)
- **Phase 2**: Example implementations (✅ Complete)
- **Phase 3**: Migration tools and documentation (✅ Complete)
- **Phase 4**: Community adoption and feedback (🔄 In Progress)
- **Phase 5**: Legacy format deprecation (📅 Future)
