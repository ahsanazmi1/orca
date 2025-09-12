# Orca Core Decision Contract

## Overview
This document defines the complete contract for Orca Core's decision engine, including all required fields, enums, and examples for Week 4 Polish & Evidence implementation.

## Schema Evolution
- **Week 1**: Basic decision engine with simple approve/decline
- **Week 2**: Added rail/channel support and enhanced metadata
- **Week 3**: Added human-readable explanations with templates
- **Week 4**: Refined schema with structured metadata and canonical reason/action codes

## DecisionRequest Schema

### Required Fields

#### `cart_total` (float)
- **Type**: `float`
- **Validation**: Must be > 0
- **Description**: Total cart value in the specified currency
- **Example**: `150.0`

#### `currency` (string)
- **Type**: `string`
- **Default**: `"USD"`
- **Description**: Currency code (ISO 4217)
- **Example**: `"USD"`

#### `rail` (enum) ⭐ **Week 2 Required**
- **Type**: `RailType`
- **Values**: `"Card"` | `"ACH"`
- **Required**: Yes
- **Description**: Payment rail type
- **Examples**:
  - `"Card"` - Credit/debit card transactions
  - `"ACH"` - Bank transfer transactions

#### `channel` (enum) ⭐ **Week 2 Required**
- **Type**: `ChannelType`
- **Values**: `"online"` | `"pos"`
- **Required**: Yes
- **Description**: Transaction channel
- **Examples**:
  - `"online"` - E-commerce, mobile app, web
  - `"pos"` - Point of sale, in-store

### Optional Fields

#### `features` (object)
- **Type**: `dict[str, float]`
- **Default**: `{}`
- **Description**: Feature values for ML models
- **Example**:
  ```json
  {
    "velocity_24h": 2.5,
    "risk_score": 0.15
  }
  ```

#### `context` (object)
- **Type**: `dict[str, Any]`
- **Default**: `{}`
- **Description**: Additional context information
- **Example**:
  ```json
  {
    "location_ip_country": "US",
    "billing_country": "US",
    "customer": {
      "loyalty_tier": "GOLD",
      "chargebacks_12m": 0
    }
  }
  ```

## DecisionResponse Schema

### Core Fields (Week 4)

#### `status` (enum) ⭐ **Week 4 Required**
- **Type**: `DecisionStatus`
- **Values**: `"APPROVE"` | `"DECLINE"` | `"ROUTE"`
- **Description**: Standardized decision status
- **Note**: `ROUTE` replaces the legacy `REVIEW` status

#### `reasons[]` (array of strings) ⭐ **Week 4 Canonical**
- **Type**: `list[str]`
- **Description**: Machine-readable reason codes (canonical)
- **Canonical Codes**:
  - `"high_ticket"` - Cart total exceeds threshold
  - `"velocity_flag"` - High transaction velocity
  - `"ach_limit_exceeded"` - ACH transaction limit exceeded
  - `"location_mismatch"` - IP location differs from billing
  - `"online_verification"` - Online transaction verification needed
  - `"ach_online_verification"` - ACH online verification needed
  - `"chargeback_history"` - Customer has chargeback history
  - `"high_risk"` - ML risk score exceeds threshold

#### `actions[]` (array of strings) ⭐ **Week 4 Canonical**
- **Type**: `list[str]`
- **Description**: Recommended action codes (canonical)
- **Canonical Codes**:
  - `"manual_review"` - Route to human reviewer
  - `"step_up_auth"` - Require additional authentication
  - `"fallback_card"` - Suggest card payment instead
  - `"block_transaction"` - Block the transaction
  - `"micro_deposit_verification"` - Verify with micro deposits
  - `"process_payment"` - Process payment normally
  - `"send_confirmation"` - Send confirmation to customer

#### `meta` (object) ⭐ **Week 4 Structured**
- **Type**: `DecisionMeta`
- **Description**: Structured decision metadata
- **Required Fields**:
  - `timestamp` (datetime) - Decision timestamp
  - `transaction_id` (string) - Unique transaction identifier
  - `rail` (RailType) - Payment rail used
  - `channel` (ChannelType) - Transaction channel
  - `cart_total` (float) - Total cart value
  - `risk_score` (float) - ML risk score (0.0-1.0)
  - `rules_evaluated` (list[str]) - Rules that were evaluated
  - `approved_amount` (float, optional) - Amount approved if applicable

### Legacy Fields (Backward Compatibility)

#### `decision` (string)
- **Type**: `string`
- **Description**: Legacy decision result
- **Values**: `"APPROVE"` | `"REVIEW"` | `"DECLINE"`
- **Note**: `REVIEW` maps to `ROUTE` in the new schema

### Enhanced Fields (Week 3+)

#### `signals_triggered[]` (array of strings)
- **Type**: `list[str]`
- **Description**: List of triggered rule signals
- **Examples**: `["CARD_HIGH_TICKET", "HIGH_TICKET", "VELOCITY"]`

#### `explanation` (string)
- **Type**: `string | null`
- **Description**: Human-readable explanation
- **Example**: `"Transaction approved for $150.00. Cart total within approved limits."`

#### `explanation_human` (string) ⭐ **Week 3**
- **Type**: `string | null`
- **Description**: Enhanced human-readable explanation with templates
- **Example**: `"Approved: Transaction amount within approved limits."`

#### `routing_hint` (string)
- **Type**: `string | null`
- **Description**: Routing instruction
- **Examples**:
  - `"PROCESS_NORMALLY"`
  - `"ROUTE_TO_VISA_NETWORK"`
  - `"ROUTE_TO_ACH_NETWORK"`
  - `"BLOCK_TRANSACTION"`
  - `"ROUTE_TO_MANUAL_REVIEW"`

### Deprecated Fields (Backward Compatibility)

#### `transaction_id` (string)
- **Type**: `string | null`
- **Description**: [DEPRECATED] Use `meta.transaction_id`
- **Example**: `"txn_17173cba4a4b4c6f"`

#### `cart_total` (float)
- **Type**: `float | null`
- **Description**: [DEPRECATED] Use `meta.cart_total`
- **Example**: `150.0`

#### `timestamp` (datetime)
- **Type**: `datetime | null`
- **Description**: [DEPRECATED] Use `meta.timestamp`
- **Example**: `"2025-09-11T20:58:47.979764"`

#### `rail` (enum)
- **Type**: `RailType | null`
- **Description**: [DEPRECATED] Use `meta.rail`
- **Values**: `"Card"` | `"ACH"` | `null`

## Complete Examples

### Example 1: APPROVE Decision

#### Input (DecisionRequest)
```json
{
  "cart_total": 150.0,
  "currency": "USD",
  "rail": "Card",
  "channel": "online",
  "features": {
    "velocity_24h": 1.0
  },
  "context": {
    "location_ip_country": "US",
    "billing_country": "US",
    "customer": {
      "loyalty_tier": "GOLD",
      "chargebacks_12m": 0
    }
  }
}
```

#### Output (DecisionResponse)
```json
{
  "status": "APPROVE",
  "reasons": ["Cart total $150.00 within approved threshold"],
  "actions": ["process_payment", "send_confirmation"],
  "meta": {
    "timestamp": "2025-01-15T10:30:45.123456",
    "transaction_id": "txn_a82c4dfcfbe945e4",
    "rail": "Card",
    "channel": "online",
    "cart_total": 150.0,
    "risk_score": 0.15,
    "rules_evaluated": [],
    "approved_amount": 150.0
  },
  "decision": "APPROVE",
  "signals_triggered": [],
  "explanation": "Transaction approved for $150.00. Cart total within approved limits.",
  "explanation_human": "Approved: Transaction amount within approved limits.",
  "routing_hint": "PROCESS_NORMALLY",
  "transaction_id": "txn_a82c4dfcfbe945e4",
  "cart_total": 150.0,
  "timestamp": "2025-01-15T10:30:45.123456",
  "rail": "Card"
}
```

### Example 2: ROUTE Decision

#### Input (DecisionRequest)
```json
{
  "cart_total": 2200.0,
  "currency": "USD",
  "rail": "Card",
  "channel": "online",
  "features": {
    "velocity_24h": 4.0
  },
  "context": {
    "location_ip_country": "US",
    "billing_country": "US",
    "customer": {
      "loyalty_tier": "BRONZE",
      "chargebacks_12m": 1
    }
  }
}
```

#### Output (DecisionResponse)
```json
{
  "status": "ROUTE",
  "reasons": [
    "high_ticket",
    "online_verification",
    "HIGH_TICKET: Cart total $2200.00 exceeds $500.00 threshold"
  ],
  "actions": [
    "manual_review",
    "step_up_auth",
    "ROUTE_TO_REVIEW"
  ],
  "meta": {
    "timestamp": "2025-01-15T10:30:45.123456",
    "transaction_id": "txn_37d9b85b0f1b4789",
    "rail": "Card",
    "channel": "online",
    "cart_total": 2200.0,
    "risk_score": 0.15,
    "rules_evaluated": ["CARD_HIGH_TICKET", "CARD_CHANNEL", "HIGH_TICKET"]
  },
  "decision": "REVIEW",
  "signals_triggered": ["CARD_HIGH_TICKET", "CARD_CHANNEL", "HIGH_TICKET"],
  "explanation": "Transaction flagged for manual review due to: high_ticket, online_verification.",
  "explanation_human": "Under review: High-value card transaction requires additional verification. Please check your email for next steps. Additionally, under review: additional verification required for online card transaction.",
  "routing_hint": "ROUTE_TO_MANUAL_REVIEW",
  "transaction_id": "txn_37d9b85b0f1b4789",
  "cart_total": 2200.0,
  "timestamp": "2025-01-15T10:30:45.123456",
  "rail": "Card"
}
```

### Example 3: DECLINE Decision

#### Input (DecisionRequest)
```json
{
  "cart_total": 6000.0,
  "currency": "USD",
  "rail": "ACH",
  "channel": "online",
  "features": {
    "velocity_24h": 1.0
  },
  "context": {
    "location_ip_country": "US",
    "billing_country": "US"
  }
}
```

#### Output (DecisionResponse)
```json
{
  "status": "DECLINE",
  "reasons": ["ach_limit_exceeded"],
  "actions": ["block_transaction"],
  "meta": {
    "timestamp": "2025-01-15T10:30:45.123456",
    "transaction_id": "txn_82803fa162594a60",
    "rail": "ACH",
    "channel": "online",
    "cart_total": 6000.0,
    "risk_score": 0.15,
    "rules_evaluated": ["ACH_LIMIT"]
  },
  "decision": "DECLINE",
  "signals_triggered": ["ACH_LIMIT"],
  "explanation": "Transaction declined due to: ach_limit_exceeded.",
  "explanation_human": "Declined: ACH transaction limit exceeded. Please use a different payment method.",
  "routing_hint": "BLOCK_TRANSACTION",
  "transaction_id": "txn_82803fa162594a60",
  "cart_total": 6000.0,
  "timestamp": "2025-01-15T10:30:45.123456",
  "rail": "ACH"
}
```

## Validation Rules

### Rail-Specific Rules

#### Card Rules
- **High Ticket**: Cart > $5,000 → `DECLINE` with `high_ticket` reason
- **Velocity**: 24h velocity > 4.0 → `DECLINE` with `velocity_flag` reason
- **Online Verification**: Online + cart > $1,000 → `REVIEW` with `online_verification` reason

#### ACH Rules
- **Limit**: Cart > $2,000 → `DECLINE` with `ach_limit_exceeded` reason
- **Location Mismatch**: IP ≠ billing country → `DECLINE` with `location_mismatch` reason
- **Online Verification**: Online + cart > $500 → `REVIEW` with `ach_online_verification` reason

### Channel-Specific Behavior
- **Online**: Higher verification requirements, additional security steps
- **POS**: Generally more trusted, streamlined processing

## Error Handling

### Validation Errors
- **Missing rail**: `ValidationError: Field required: rail`
- **Invalid rail**: `ValidationError: Input should be 'Card' or 'ACH'`
- **Missing channel**: `ValidationError: Field required: channel`
- **Invalid channel**: `ValidationError: Input should be 'online' or 'pos'`
- **Zero cart_total**: `ValidationError: Input should be greater than 0`

### Graceful Failures
- Extra fields in input are ignored
- Malformed JSON returns `JSONDecodeError`
- Invalid enum values return clear validation messages
- All errors include helpful context for debugging

## CLI Usage Examples

```bash
# Basic usage with rail and channel
orca decide-file sample.json --rail Card --channel online

# Stdin with rail override
echo '{"cart_total": 150.0, "rail": "ACH", "channel": "pos"}' | orca decide -

# All combinations supported
orca decide-file sample.json --rail ACH --channel pos
```
