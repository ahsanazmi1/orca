# Orca Core Decision Engine Rules

This document describes the rule-based decision system in Orca Core, including the decision contract, current rules, and guidelines for extending the system.

## Decision Contract

The Orca Core decision engine follows a strict three-tier decision contract:

### Decision Types

- **`APPROVE`**: Transaction is approved for processing
- **`REVIEW`**: Transaction requires manual review before processing
- **`DECLINE`**: Transaction is declined and should not be processed

### Rule System Philosophy

**Rules can only promote decisions to `REVIEW`**. The `DECLINE` decision is reserved for:

1. **ML Risk Assessment**: When the ML risk score exceeds the high-risk threshold (default: 0.80)
2. **High-Risk Rules**: Special rules that explicitly handle high-risk scenarios

This design ensures that:
- Rules provide consistent, explainable decision logic
- ML models handle complex risk assessment
- Human review is available for edge cases
- Declines are based on strong evidence (high ML risk or explicit high-risk rules)

## Current Rules

### 1. High Ticket Rule (`HighTicketRule`)

**Purpose**: Flag high-value transactions for manual review

**Threshold**: Cart total > $500.00

**Rationale**: High-value transactions carry higher financial risk and warrant additional scrutiny

**Decision Impact**: Promotes to `REVIEW`

**Actions**: `ROUTE_TO_REVIEW`

**Implementation**:
```python
def apply(self, request: DecisionRequest) -> RuleResult:
    if request.cart_total > 500.0:
        return RuleResult(
            decision_hint="REVIEW",
            reasons=[f"HIGH_TICKET: Cart total ${request.cart_total:.2f} exceeds $500.00 threshold"],
            actions=["ROUTE_TO_REVIEW"]
        )
    return RuleResult()
```

### 2. Velocity Rule (`VelocityRule`)

**Purpose**: Detect unusual transaction velocity patterns

**Threshold**: 24-hour velocity > 3 transactions

**Rationale**: High transaction velocity may indicate fraudulent activity or account takeover

**Decision Impact**: Promotes to `REVIEW`

**Actions**: `ROUTE_TO_REVIEW`

**Implementation**:
```python
def apply(self, request: DecisionRequest) -> RuleResult:
    velocity = request.features.get("velocity_24h", 0.0)
    if velocity > 3.0:
        return RuleResult(
            decision_hint="REVIEW",
            reasons=[f"VELOCITY_FLAG: 24h velocity {velocity} exceeds 3.0 threshold"],
            actions=["ROUTE_TO_REVIEW"]
        )
    return RuleResult()
```

### 3. Location Mismatch Rule (`LocationMismatchRule`)

**Purpose**: Flag transactions from different countries than billing address

**Threshold**: IP country ≠ billing country

**Rationale**: Geographic inconsistencies may indicate fraudulent transactions

**Decision Impact**: Promotes to `REVIEW`

**Actions**: `ROUTE_TO_REVIEW`

**Implementation**:
```python
def apply(self, request: DecisionRequest) -> RuleResult:
    ip_country = request.context.get("location_ip_country", "")
    billing_country = request.context.get("billing_country", "")

    if ip_country and billing_country and ip_country != billing_country:
        return RuleResult(
            decision_hint="REVIEW",
            reasons=[f"LOCATION_MISMATCH: IP country '{ip_country}' differs from billing country '{billing_country}'"],
            actions=["ROUTE_TO_REVIEW"]
        )
    return RuleResult()
```

### 4. High IP Distance Rule (`HighIpDistanceRule`)

**Purpose**: Flag transactions from high-risk IP distances

**Threshold**: `features.high_ip_distance == True`

**Rationale**: High IP distance may indicate VPN usage or suspicious location patterns

**Decision Impact**: Promotes to `REVIEW`

**Actions**: `ROUTE_TO_REVIEW`

**Implementation**:
```python
def apply(self, request: DecisionRequest) -> RuleResult:
    if request.features.get("high_ip_distance", False):
        return RuleResult(
            decision_hint="REVIEW",
            reasons=["HIGH_IP_DISTANCE: Transaction originates from high-risk IP distance"],
            actions=["ROUTE_TO_REVIEW"]
        )
    return RuleResult()
```

### 5. Chargeback History Rule (`ChargebackHistoryRule`)

**Purpose**: Flag customers with recent chargeback history

**Threshold**: Customer chargebacks in last 12 months > 0

**Rationale**: Customers with chargeback history pose higher risk

**Decision Impact**: Promotes to `REVIEW`

**Actions**: `ROUTE_TO_REVIEW`

**Implementation**:
```python
def apply(self, request: DecisionRequest) -> RuleResult:
    customer = request.context.get("customer", {})
    chargebacks = customer.get("chargebacks_12m", 0)

    if chargebacks > 0:
        return RuleResult(
            decision_hint="REVIEW",
            reasons=[f"CHARGEBACK_HISTORY: Customer has {chargebacks} chargeback(s) in last 12 months"],
            actions=["ROUTE_TO_REVIEW"]
        )
    return RuleResult()
```

### 6. Loyalty Boost Rule (`LoyaltyBoostRule`)

**Purpose**: Provide benefits to loyal customers

**Threshold**: Customer loyalty tier in `{"GOLD", "PLATINUM"}`

**Rationale**: Reward loyal customers with positive actions

**Decision Impact**: No decision change (approval remains approval)

**Actions**: `LOYALTY_BOOST`

**Implementation**:
```python
def apply(self, request: DecisionRequest) -> RuleResult:
    customer = request.context.get("customer", {})
    loyalty_tier = customer.get("loyalty_tier", "NONE")

    if loyalty_tier in {"GOLD", "PLATINUM"}:
        return RuleResult(
            decision_hint=None,  # No decision change
            reasons=[f"LOYALTY_BOOST: Customer has {loyalty_tier} loyalty tier"],
            actions=["LOYALTY_BOOST"]
        )
    return RuleResult()
```

### 7. High Risk Assessment (Engine-Level)

**Purpose**: Handle high-risk scenarios based on ML risk assessment

**Threshold**: ML risk score > 0.80

**Rationale**: High ML risk scores indicate strong evidence of fraudulent activity

**Decision Impact**: Promotes to `DECLINE`

**Actions**: `BLOCK`

**Implementation**: This is handled directly in the engine after rule evaluation:
```python
# If ML risk score > 0.80, override to DECLINE
if risk_score > 0.80:
    final_decision = "DECLINE"
    reasons.append(f"HIGH_RISK: ML risk score {risk_score:.3f} exceeds 0.800 threshold")
    actions.append("BLOCK")
    meta["rules_evaluated"].append("HIGH_RISK")
```

## Rule Ordering and Determinism

### Rule Execution Order

Rules are executed in a specific order defined in `src/orca_core/rules/registry.py`:

1. **High Ticket Rule** - Early detection of high-value transactions
2. **Velocity Rule** - Pattern-based fraud detection
3. **Location Mismatch Rule** - Geographic inconsistency detection
4. **High IP Distance Rule** - IP-based risk assessment
5. **Chargeback History Rule** - Customer risk assessment
6. **Loyalty Boost Rule** - Customer benefit application

After rule evaluation, the engine applies:
7. **High Risk Assessment** - ML-based high-risk detection (engine-level)

### Determinism Guarantees

The rule system provides the following guarantees:

1. **Stable Output**: Same input always produces the same output
2. **Ordered Execution**: Rules execute in a consistent, predefined order
3. **Predictable Aggregation**: Decision hints, reasons, and actions are aggregated deterministically
4. **No Race Conditions**: Single-threaded execution ensures consistent results

### Decision Aggregation Logic

```python
# Start with APPROVE
decision = "APPROVE"

# Apply rules in order
for rule in rules():
    result = rule.apply(request)

    # Aggregate reasons and actions
    reasons.extend(result.reasons)
    actions.extend(result.actions)

    # Update decision based on hints
    if result.decision_hint == "REVIEW":
        decision = "REVIEW"
    elif result.decision_hint == "DECLINE":
        decision = "DECLINE"
        break  # DECLINE is final

# Remove duplicates while preserving order
unique_reasons = list(dict.fromkeys(reasons))
unique_actions = list(dict.fromkeys(actions))
```

## Adding a New Rule

### Step 1: Implement the Rule Class

Create a new rule class in `src/orca_core/rules/builtins.py`:

```python
class NewRule(Rule):
    """Description of what this rule does."""

    def __init__(self, threshold: float = 1.0):
        self.threshold = threshold

    def apply(self, request: DecisionRequest) -> RuleResult:
        # Implement your rule logic
        if self._condition_met(request):
            return RuleResult(
                decision_hint="REVIEW",  # or None for no decision change
                reasons=[f"NEW_RULE: Description of why rule triggered"],
                actions=["ROUTE_TO_REVIEW"]  # or other appropriate action
            )
        return RuleResult()

    def _condition_met(self, request: DecisionRequest) -> bool:
        # Implement your condition logic
        return request.some_field > self.threshold
```

### Step 2: Add to Registry

Update `src/orca_core/rules/registry.py` to include your rule in the appropriate order:

```python
def rules() -> list[Rule]:
    """Return ordered list of rule instances."""
    return [
        HighTicketRule(),
        VelocityRule(),
        LocationMismatchRule(),
        HighIpDistanceRule(),
        ChargebackHistoryRule(),
        NewRule(),  # Add your rule here
        LoyaltyBoostRule(),
    ]
```

### Step 3: Add Unit Tests

Create comprehensive tests in `tests/test_rules.py`:

```python
class TestNewRule:
    """Test cases for NewRule."""

    def test_new_rule_triggered(self):
        """Test that NewRule triggers when condition is met."""
        rule = NewRule(threshold=100.0)
        request = DecisionRequest(
            cart_total=50.0,
            currency="USD",
            features={"some_field": 150.0},
            context={}
        )

        result = rule.apply(request)

        assert result.decision_hint == "REVIEW"
        assert "NEW_RULE" in result.reasons[0]
        assert "ROUTE_TO_REVIEW" in result.actions

    def test_new_rule_not_triggered(self):
        """Test that NewRule doesn't trigger when condition is not met."""
        rule = NewRule(threshold=100.0)
        request = DecisionRequest(
            cart_total=50.0,
            currency="USD",
            features={"some_field": 50.0},
            context={}
        )

        result = rule.apply(request)

        assert result.decision_hint is None
        assert not result.reasons
        assert not result.actions

    def test_new_rule_custom_threshold(self):
        """Test NewRule with custom threshold."""
        rule = NewRule(threshold=200.0)
        # ... test implementation
```

### Step 4: Add Fixture Case (if applicable)

If your rule represents a common scenario, add a fixture file in `fixtures/requests/`:

```json
{
  "cart_total": 150.0,
  "currency": "USD",
  "features": {
    "velocity_24h": 1,
    "some_field": 250.0
  },
  "context": {
    "channel": "ecom",
    "location_ip_country": "US",
    "billing_country": "US",
    "customer": {
      "loyalty_tier": "SILVER",
      "chargebacks_12m": 0
    }
  }
}
```

### Step 5: Update Documentation

Update this `RULES.md` file to include your new rule in the "Current Rules" section.

## Rule Design Guidelines

### 1. Keep Rules Simple and Focused

Each rule should have a single, clear purpose. Avoid complex logic that combines multiple concerns.

### 2. Use Descriptive Names and Messages

- Rule names should clearly indicate their purpose
- Reason messages should explain why the rule triggered
- Action names should indicate what should happen next

### 3. Make Rules Configurable

Use constructor parameters to make thresholds and conditions configurable:

```python
class VelocityRule(Rule):
    def __init__(self, threshold: float = 3.0, window_hours: int = 24):
        self.threshold = threshold
        self.window_hours = window_hours
```

### 4. Handle Missing Data Gracefully

Always check for missing or invalid data:

```python
def apply(self, request: DecisionRequest) -> RuleResult:
    velocity = request.features.get("velocity_24h", 0.0)
    if not isinstance(velocity, (int, float)):
        return RuleResult()  # Skip rule if data is invalid
    # ... rest of logic
```

### 5. Test Edge Cases

Include tests for:
- Missing data
- Invalid data types
- Boundary conditions
- Custom thresholds

### 6. Consider Performance

Rules are executed for every transaction, so keep them efficient:
- Avoid expensive computations
- Use simple data structures
- Minimize external dependencies

## Integration with ML

The rule system is designed to work alongside ML models:

1. **Rules provide explainable logic** for common scenarios
2. **ML handles complex patterns** that are difficult to encode as rules
3. **High-risk rule** bridges the gap between rules and ML
4. **Feature extraction** prepares data for both rules and ML models

This hybrid approach provides:
- **Transparency**: Rules are easily understood and auditable
- **Flexibility**: ML can adapt to new patterns
- **Performance**: Rules provide fast decisions for common cases
- **Accuracy**: ML provides sophisticated risk assessment

## Testing and Validation

### Unit Tests

Each rule should have comprehensive unit tests covering:
- Normal operation
- Edge cases
- Error conditions
- Custom configurations

### Integration Tests

Use the parametrized fixture tests in `tests/test_fixtures_param.py` to validate:
- End-to-end decision flow
- Rule interactions
- Expected outcomes for common scenarios

### Performance Tests

Consider adding performance tests for rules that:
- Process large amounts of data
- Perform complex calculations
- Are executed frequently

## Conclusion

The Orca Core rule system provides a robust, extensible foundation for transaction decision-making. By following the guidelines in this document, you can confidently add new rules that maintain the system's determinism, performance, and reliability.

For questions or clarifications, refer to the existing rule implementations or the test suite for examples of best practices.
