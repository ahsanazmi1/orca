# ocn-common — Open Checkout Network Common

Shared schemas, utilities, and contracts for the Open Checkout Network (OCN) ecosystem.

## Phase 3 — Negotiation & Live Fee Bidding

Contracts for bidding/constraints signals.

### Phase 3 — Negotiation & Live Fee Bidding
- [x] CloudEvent schemas: ocn.weave.bid_request.v1, ocn.weave.bid_response.v1
- [x] CloudEvent schemas: ocn.oasis.constraint.v1, ocn.onyx.trust_signal.v1
- [x] Examples in /examples/events/ and CI validation tests

## CloudEvents Schemas

This repository contains CloudEvents schemas for the OCN ecosystem:

### Current Schemas (v1)
- `orca.decision.v1.schema.json` - Decision CloudEvents from Orca
- `orca.explanation.v1.schema.json` - Explanation CloudEvents from Orca  
- `weave.audit.v1.schema.json` - Audit CloudEvents from Weave

### AP2 Mandates
- AP2 (Agent Protocol 2.0) schemas for decision processing contracts

## Usage

These schemas can be used to validate CloudEvents in any OCN service:

```python
import json
import jsonschema

# Load schema
with open('orca.decision.v1.schema.json') as f:
    schema = json.load(f)

# Validate CloudEvent
jsonschema.validate(cloudevent_data, schema)
```

## Related OCN Repositories

- [Orca](https://github.com/ocn-ai/orca): The Open Checkout Agent
- [Okra](https://github.com/ocn-ai/okra): The Open Credit Agent
- [Onyx](https://github.com/ocn-ai/onyx): The Open Trust Registry
- [Oasis](https://github.com/ocn-ai/oasis): The Open Treasury Agent
- [Orion](https://github.com/ocn-ai/orion): The Open Payout Agent
- [Weave](https://github.com/ocn-ai/weave): The Open Receipt Ledger
- [Opal](https://github.com/ocn-ai/opal): The Open Payment Agent
- [Olive](https://github.com/ocn-ai/olive): The Open Loyalty Agent
