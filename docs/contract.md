# Orca Core Decision Contract

## Overview
This document defines the complete contract for Orca Core's decision engine, including all required fields, enums, and examples for Week 2 Rules + Rails implementation.

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

### Legacy Fields (Required for Backward Compatibility)

#### `decision` (string)
- **Type**: `string`
- **Description**: Decision result
- **Values**: `"APPROVE"` | `"REVIEW"` | `"DECLINE"`

#### `reasons[]` (array of strings) ⭐ **Week 2 Enhanced**
- **Type**: `list[str]`
- **Description**: Machine-readable reason codes
- **Examples**:
  - `["high_ticket"]` - Cart total exceeds threshold
  - `["velocity_flag"]` - High transaction velocity
  - `["ach_limit_exceeded"]` - ACH transaction limit exceeded
  - `["location_mismatch"]` - IP location differs from billing
  - `["online_verification"]` - Online transaction verification needed

#### `actions[]` (array of strings) ⭐ **Week 2 Enhanced**
- **Type**: `list[str]`
- **Description**: Recommended follow-up actions
- **Examples**:
  - `["manual_review"]` - Route to human reviewer
  - `["step_up_auth"]` - Require additional authentication
  - `["fallback_card"]` - Suggest card payment instead
  - `["block_transaction"]` - Block the transaction
  - `["micro_deposit_verification"]` - Verify with micro deposits

#### `meta` (object)
- **Type**: `dict[str, Any]`
- **Description**: Additional metadata
- **Example**:
  ```json
  {
    "risk_score": 0.15,
    "rules_evaluated": ["CARD_HIGH_TICKET", "HIGH_TICKET"],
    "approved_amount": 150.0
  }
  ```

### Enhanced Fields (Week 2)

#### `status` (enum)
- **Type**: `DecisionStatus | null`
- **Values**: `"APPROVE"` | `"DECLINE"` | `"ROUTE"` | `null`
- **Description**: Standardized decision status

#### `signals_triggered[]` (array of strings)
- **Type**: `list[str]`
- **Description**: List of triggered rule signals
- **Examples**: `["CARD_HIGH_TICKET", "HIGH_TICKET", "VELOCITY"]`

#### `explanation` (string)
- **Type**: `string | null`
- **Description**: Human-readable explanation
- **Example**: `"Transaction approved for $150.00. Cart total within approved limits."`

#### `routing_hint` (string)
- **Type**: `string | null`
- **Description**: Routing instruction
- **Examples**:
  - `"PROCESS_NORMALLY"`
  - `"ROUTE_TO_VISA_NETWORK"`
  - `"ROUTE_TO_ACH_NETWORK"`
  - `"BLOCK_TRANSACTION"`
  - `"ROUTE_TO_MANUAL_REVIEW"`

#### `rail` (enum) ⭐ **Week 2 New**
- **Type**: `RailType | null`
- **Values**: `"Card"` | `"ACH"` | `null`
- **Description**: Payment rail type used for this transaction

#### `transaction_id` (string)
- **Type**: `string | null`
- **Description**: Unique transaction identifier
- **Example**: `"txn_17173cba4a4b4c6f"`

#### `cart_total` (float)
- **Type**: `float | null`
- **Description**: Total cart value for this transaction
- **Example**: `150.0`

#### `timestamp` (datetime)
- **Type**: `datetime | null`
- **Description**: Decision timestamp
- **Example**: `"2025-09-11T20:58:47.979764"`

## Complete Example

### Input (DecisionRequest)
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

### Output (DecisionResponse)
```json
{
  "decision": "REVIEW",
  "reasons": [
    "online_verification",
    "HIGH_TICKET: Cart total $2200.00 exceeds $500.00 threshold",
    "VELOCITY_FLAG: 24h velocity 4.0 exceeds 3.0 threshold",
    "CHARGEBACK_HISTORY: Customer has 1 chargeback(s) in last 12 months"
  ],
  "actions": [
    "step_up_auth",
    "ROUTE_TO_REVIEW",
    "ROUTE_TO_REVIEW",
    "ROUTE_TO_REVIEW"
  ],
  "meta": {
    "risk_score": 0.15,
    "rules_evaluated": ["CARD_CHANNEL", "HIGH_TICKET", "VELOCITY", "CHARGEBACK_HISTORY"]
  },
  "status": null,
  "signals_triggered": ["CARD_CHANNEL", "HIGH_TICKET", "VELOCITY", "CHARGEBACK_HISTORY"],
  "explanation": "Transaction decision: REVIEW",
  "routing_hint": "PROCESS_NORMALLY",
  "rail": "Card",
  "transaction_id": "txn_4656d3770e1a423b",
  "cart_total": 2200.0,
  "timestamp": "2025-09-11T20:58:15.639211"
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
