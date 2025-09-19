# AP2 NLG Templates

This document contains lightweight templates for generating natural language explanations that cite AP2 field paths explicitly.

## Template Structure

Templates follow the pattern:
```
{explanation_text} (AP2 fields: {field_citations})
```

## Reason Code Templates

### High Ticket
```
Transaction amount exceeds threshold (AP2 fields: CartMandate.amount={amount}, CartMandate.currency={currency})
```

### Velocity Flag
```
High transaction velocity detected (AP2 fields: IntentMandate.channel={channel}, velocity_24h=true)
```

### ACH Limit Exceeded
```
ACH transaction limit exceeded (AP2 fields: PaymentMandate.modality={modality}, CartMandate.amount={amount})
```

### Location Mismatch
```
Geographic location mismatch detected (AP2 fields: CartMandate.geo.country={country}, IntentMandate.channel={channel})
```

### Online Verification
```
Online transaction requires additional verification (AP2 fields: IntentMandate.channel={channel}, PaymentMandate.modality={modality})
```

### ACH Online Verification
```
ACH online transaction requires verification (AP2 fields: PaymentMandate.modality={modality}, IntentMandate.channel={channel})
```

### Chargeback History
```
Customer has chargeback history (AP2 fields: IntentMandate.actor={actor})
```

### High Risk
```
High risk score detected (AP2 fields: DecisionOutcome.risk_score={risk_score}, DecisionOutcome.result={result})
```

## Action Code Templates

### Manual Review
```
Route to manual review (AP2 fields: DecisionOutcome.result={result}, IntentMandate.channel={channel})
```

### Step Up Auth
```
Require additional authentication (AP2 fields: PaymentMandate.auth_requirements={auth_reqs}, IntentMandate.channel={channel})
```

### Fallback Card
```
Fallback to card payment (AP2 fields: PaymentMandate.modality={modality}, CartMandate.amount={amount})
```

### Block Transaction
```
Block transaction (AP2 fields: DecisionOutcome.result={result}, DecisionOutcome.risk_score={risk_score})
```

### Micro Deposit Verification
```
Require micro deposit verification (AP2 fields: PaymentMandate.modality={modality}, IntentMandate.channel={channel})
```

### Process Payment
```
Process payment normally (AP2 fields: DecisionOutcome.result={result}, PaymentMandate.modality={modality})
```

### Send Confirmation
```
Send confirmation (AP2 fields: IntentMandate.channel={channel}, DecisionOutcome.result={result})
```

## Context Templates

### AP2 Context Summary
```
AP2 context: IntentMandate.channel={channel}, IntentMandate.actor={actor}, CartMandate.amount={amount}, CartMandate.currency={currency}, PaymentMandate.modality={modality}
```

### Decision Summary
```
Decision: {result}. Risk score: {risk_score}. AP2 context: {context_fields}
```

## Field Citation Patterns

### Amount Citations
- `CartMandate.amount={amount}`
- `CartMandate.currency={currency}`

### Channel Citations
- `IntentMandate.channel={channel}`
- `IntentMandate.actor={actor}`

### Payment Citations
- `PaymentMandate.modality={modality}`
- `PaymentMandate.auth_requirements={auth_reqs}`

### Decision Citations
- `DecisionOutcome.result={result}`
- `DecisionOutcome.risk_score={risk_score}`

### Geographic Citations
- `CartMandate.geo.country={country}`
- `CartMandate.geo.city={city}`

## Template Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{amount}` | Cart amount | `100.00` |
| `{currency}` | Currency code | `USD` |
| `{channel}` | Intent channel | `web` |
| `{actor}` | Intent actor | `human` |
| `{modality}` | Payment modality | `immediate` |
| `{auth_reqs}` | Auth requirements | `[pin, biometric]` |
| `{result}` | Decision result | `APPROVE` |
| `{risk_score}` | Risk score | `0.65` |
| `{country}` | Geographic country | `US` |
| `{city}` | Geographic city | `New York` |
| `{mcc}` | Merchant category code | `5733` |

## Usage Examples

### Single Reason
```
Declined due to high ticket amount (AP2 fields: CartMandate.amount=5000.00, CartMandate.currency=USD)
```

### Multiple Reasons
```
Declined due to high ticket amount (AP2 fields: CartMandate.amount=5000.00, CartMandate.currency=USD). Additionally, high velocity detected (AP2 fields: IntentMandate.channel=web, velocity_24h=true)
```

### With Actions
```
Review required due to location mismatch (AP2 fields: CartMandate.geo.country=GB, IntentMandate.channel=web). Action: Route to manual review (AP2 fields: DecisionOutcome.result=REVIEW, IntentMandate.channel=web)
```

### Full Context
```
Decision: REVIEW. Risk score: 0.650. Reason 'location_mismatch': IP country 'GB' differs from billing country 'US' (AP2 fields: CartMandate.geo.country=GB, IntentMandate.channel=web). Action 'manual_review': Location verification required (AP2 fields: DecisionOutcome.result=REVIEW, IntentMandate.channel=web). AP2 context: IntentMandate.channel=web, IntentMandate.actor=human, CartMandate.amount=100.00, CartMandate.currency=USD, PaymentMandate.modality=immediate
```

## Field Validation

All field citations must reference valid AP2 field paths:

### Valid Field Paths
- `intent.actor`
- `intent.channel`
- `intent.agent_presence`
- `cart.amount`
- `cart.currency`
- `cart.mcc`
- `cart.geo.country`
- `payment.modality`
- `payment.auth_requirements`
- `decision.result`
- `decision.risk_score`

### Invalid Field Paths (Will be filtered out)
- `legacy.cart_total`
- `old.rail`
- `custom.field`
- Any field not in the AP2 schema
