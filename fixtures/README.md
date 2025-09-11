# Orca Core Decision Engine Fixtures

This directory contains realistic sample requests for testing the Orca Core decision engine.

## Structure

```
fixtures/
└── requests/
    ├── low_ticket_ok.json           # Clean approval scenario
    ├── high_ticket_review.json      # High ticket amount triggers review
    ├── velocity_review.json         # High velocity triggers review
    ├── location_mismatch_review.json # Location mismatch + IP distance
    └── high_risk_decline.json       # Chargeback history triggers review
```

## Fixture Descriptions

### `low_ticket_ok.json`
- **Cart Total**: $125.00
- **Expected Decision**: APPROVE
- **Features**: Low velocity (1.0)
- **Context**: US location, GOLD loyalty tier, no chargebacks
- **Triggers**: Loyalty boost action only

### `high_ticket_review.json`
- **Cart Total**: $750.00
- **Expected Decision**: REVIEW
- **Features**: Low velocity (1.0)
- **Context**: US location, SILVER loyalty tier, no chargebacks
- **Triggers**: HIGH_TICKET rule (> $500 threshold)

### `velocity_review.json`
- **Cart Total**: $180.00
- **Expected Decision**: REVIEW
- **Features**: High velocity (4.0)
- **Context**: US location, NONE loyalty tier, no chargebacks
- **Triggers**: VELOCITY rule (> 3.0 threshold)

### `location_mismatch_review.json`
- **Cart Total**: $200.00
- **Expected Decision**: REVIEW
- **Features**: Low velocity (1.0), high IP distance (true)
- **Context**: GB IP location vs US billing, GOLD loyalty tier, no chargebacks
- **Triggers**: LOCATION_MISMATCH, HIGH_IP_DISTANCE, and LOYALTY_BOOST rules

### `high_risk_decline.json`
- **Cart Total**: $220.00
- **Expected Decision**: REVIEW
- **Features**: Low velocity (2.0)
- **Context**: US location, NONE loyalty tier, 1 chargeback in 12 months
- **Triggers**: CHARGEBACK_HISTORY rule

## Usage

These fixtures can be used for:

1. **Testing**: Validate decision engine behavior with realistic data
2. **Documentation**: Examples of expected input/output formats
3. **Integration**: Sample data for API testing and demos
4. **Development**: Consistent test cases for rule development

## JSON Schema

All fixtures follow the `DecisionRequest` schema:

```json
{
  "cart_total": float,           // Required: Cart total amount
  "currency": string,            // Optional: Currency code (default: "USD")
  "features": {                  // Optional: Feature values
    "velocity_24h": float,
    "high_ip_distance": boolean,
    // ... other features
  },
  "context": {                   // Optional: Additional context
    "channel": string,
    "location_ip_country": string,
    "billing_country": string,
    "customer": {
      "loyalty_tier": string,
      "chargebacks_12m": integer
    }
  }
}
```

## Testing

To test these fixtures with the decision engine:

```python
import json
from src.orca_core.engine import evaluate_rules
from src.orca_core.models import DecisionRequest

# Load and test a fixture
with open('fixtures/requests/high_ticket_review.json', 'r') as f:
    data = json.load(f)

request = DecisionRequest(**data)
response = evaluate_rules(request)

print(f"Decision: {response.decision}")
print(f"Reasons: {response.reasons}")
print(f"Actions: {response.actions}")
```
