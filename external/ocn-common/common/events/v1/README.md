# ocn-common CloudEvents Schemas

This directory contains CloudEvents schemas for the Open Checkout Network (OCN) ecosystem.

## Schemas

### Orca Decision Engine
- `orca.decision.v1.schema.json` - Decision CloudEvents from Orca
- `orca.explanation.v1.schema.json` - Explanation CloudEvents from Orca

### Weave Blockchain
- `weave.audit.v1.schema.json` - Audit CloudEvents from Weave
- `weave.bid_request.v1.schema.json` - Processor bid request events from Weave
- `weave.bid_response.v1.schema.json` - Processor bid response events from Weave

### Phase 3 — Negotiation & Live Fee Bidding
- `oasis.constraint.v1.schema.json` - Treasury constraint events from Oasis
- `onyx.trust_signal.v1.schema.json` - Trust signal events from Onyx

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

## Versioning

Schemas follow semantic versioning:
- Major version changes: Breaking changes to event structure
- Minor version changes: Additive changes (new optional fields)
- Patch version changes: Documentation updates, bug fixes

## Validation

All schemas are validated against:
- CloudEvents 1.0 specification
- JSON Schema Draft 2020-12
- OCN naming conventions
