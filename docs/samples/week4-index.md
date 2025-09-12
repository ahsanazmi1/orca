# Week 4 Sample Index

## Overview
This document provides an index of all Week 4 sample fixtures, linking request files to their corresponding response files with rationale for each decision outcome.

## Sample Fixtures

| Request File | Response File | Status | Rail | Channel | Cart Total | Rationale |
|--------------|---------------|--------|------|---------|------------|-----------|
| `card_approve_small.json` | `card_approve_small.json` | APPROVE | Card | online | $150.00 | Small transaction with GOLD loyalty tier gets loyalty boost approval |
| `card_decline_high_ticket.json` | `card_decline_high_ticket.json` | ROUTE | Card | online | $6,000.00 | High ticket amount triggers review for additional verification |
| `card_route_location_mismatch.json` | `card_route_location_mismatch.json` | ROUTE | Card | online | $2,200.00 | Multiple risk factors: high ticket, velocity, location mismatch, chargeback history |
| `ach_approve_small.json` | `ach_approve_small.json` | ROUTE | ACH | pos | $800.00 | High ticket threshold exceeded but GOLD loyalty provides boost |
| `ach_decline_limit.json` | `ach_decline_limit.json` | DECLINE | ACH | online | $2,500.00 | ACH limit exceeded, transaction blocked |

## Decision Rationale Details

### APPROVE Cases

#### Card Approve Small
- **File**: `card_approve_small.json`
- **Amount**: $150.00
- **Rail**: Card, Channel: online
- **Rationale**: Small transaction amount with GOLD loyalty tier. The loyalty boost rule overrides normal processing, resulting in immediate approval.
- **Key Factors**:
  - Low cart total ($150 < $500 threshold)
  - GOLD loyalty tier provides approval boost
  - No risk factors triggered

### ROUTE Cases

#### Card Decline High Ticket → ROUTE
- **File**: `card_decline_high_ticket.json`
- **Amount**: $6,000.00
- **Rail**: Card, Channel: online
- **Rationale**: High ticket amount ($6,000 > $5,000) triggers review. Online channel adds additional verification requirements.
- **Key Factors**:
  - High ticket amount exceeds $5,000 threshold
  - Online channel requires additional verification
  - BRONZE loyalty tier provides no boost

#### Card Route Location Mismatch
- **File**: `card_route_location_mismatch.json`
- **Amount**: $2,200.00
- **Rail**: Card, Channel: online
- **Rationale**: Multiple risk factors combine to trigger comprehensive review.
- **Key Factors**:
  - High ticket amount ($2,200 > $500)
  - High velocity (4.0 > 3.0 threshold)
  - Location mismatch (IP: CA, Billing: US)
  - Chargeback history (1 in last 12 months)
  - Online channel verification requirements

#### ACH Approve Small → ROUTE
- **File**: `ach_approve_small.json`
- **Amount**: $800.00
- **Rail**: ACH, Channel: pos
- **Rationale**: Amount exceeds high ticket threshold but GOLD loyalty provides boost. POS channel is more trusted than online.
- **Key Factors**:
  - High ticket amount ($800 > $500)
  - GOLD loyalty tier provides boost
  - POS channel is more trusted
  - ACH rail has different thresholds

### DECLINE Cases

#### ACH Decline Limit
- **File**: `ach_decline_limit.json`
- **Amount**: $2,500.00
- **Rail**: ACH, Channel: online
- **Rationale**: ACH transaction exceeds $2,000 limit, resulting in immediate decline.
- **Key Factors**:
  - ACH limit exceeded ($2,500 > $2,000)
  - Online channel adds risk
  - BRONZE loyalty tier provides no protection

## Schema Validation

All fixtures have been validated against the Week 4 schema:

### Request Schema Validation
- ✅ All requests include required fields: `cart_total`, `rail`, `channel`
- ✅ All requests include optional fields: `currency`, `features`, `context`
- ✅ All enum values are valid: `rail` ∈ {Card, ACH}, `channel` ∈ {online, pos}

### Response Schema Validation
- ✅ All responses include core fields: `status`, `reasons[]`, `actions[]`, `meta`
- ✅ All responses include structured metadata: `timestamp`, `transaction_id`, `rail`, `channel`, `cart_total`, `risk_score`, `rules_evaluated`
- ✅ All responses include legacy fields for backward compatibility
- ✅ All responses include enhanced fields: `explanation`, `explanation_human`, `routing_hint`

## Usage Examples

### CLI Usage
```bash
# Test individual fixtures
python -m orca_core.cli decide-file fixtures/week4/requests/card_approve_small.json

# Test all fixtures
python -m orca_core.cli decide-batch --glob "fixtures/week4/requests/*.json"
```

### Programmatic Usage
```python
from orca_core.engine import evaluate_rules
from orca_core.models import DecisionRequest
import json

# Load and evaluate a request
with open("fixtures/week4/requests/card_approve_small.json") as f:
    request_data = json.load(f)

request = DecisionRequest(**request_data)
response = evaluate_rules(request)

print(f"Status: {response.status}")
print(f"Reasons: {response.reasons}")
print(f"Actions: {response.actions}")
print(f"Meta: {response.meta.model_dump()}")
```

## File Structure
```
fixtures/week4/
├── requests/
│   ├── card_approve_small.json
│   ├── card_decline_high_ticket.json
│   ├── card_route_location_mismatch.json
│   ├── ach_approve_small.json
│   └── ach_decline_limit.json
└── responses/
    ├── card_approve_small.json
    ├── card_decline_high_ticket.json
    ├── card_route_location_mismatch.json
    ├── ach_approve_small.json
    └── ach_decline_limit.json
```

## Notes

1. **Status Mapping**: The engine maps legacy `REVIEW` decisions to new `ROUTE` status for consistency.

2. **Loyalty Boost**: GOLD loyalty tier can override normal risk assessment in certain scenarios.

3. **Rail-Specific Rules**: Card and ACH rails have different thresholds and processing rules.

4. **Channel Impact**: Online transactions require more verification than POS transactions.

5. **Risk Accumulation**: Multiple risk factors can compound to trigger more severe actions.
