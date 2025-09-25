# ocn-common Integration Guide

This document describes the integration of ocn-common schemas and contract validation across the Orca ecosystem.

## Overview

The ocn-common integration provides:

- **Standardized schemas** for AP2 contracts and CloudEvents
- **Contract validation** using ocn-common schemas
- **CI/CD validation** for all contracts and examples
- **Security scanning** for dependencies and code
- **Automated testing** for schema conformance

## Directory Structure

```
external/ocn-common/
├── common/
│   ├── events/v1/                    # CloudEvents schemas
│   │   ├── orca.decision.v1.schema.json
│   │   ├── orca.explanation.v1.schema.json
│   │   └── weave.audit.v1.schema.json
│   └── mandates/ap2/v1/              # AP2 contract schemas
│       └── README.md
└── README.md
```

## Contract Validation

### AP2 Decision Validation

```python
from src.orca.core.contract_validation import validate_decision_contract

decision_data = {
    "ap2_version": "0.1.0",
    "intent": {...},
    "cart": {...},
    "payment": {...},
    "decision": {
        "result": "APPROVE",
        "risk_score": 0.15,
        "reasons": ["low_risk"],
        "actions": ["process_payment"],
        "meta": {}
    },
    "signing": {
        "vc_proof": None,
        "receipt_hash": "sha256:abc123"
    }
}

# Validate against ocn-common schema
is_valid = validate_decision_contract(decision_data)
```

### AP2 Explanation Validation

```python
from src.orca.core.contract_validation import validate_explanation_contract

explanation_data = {
    "trace_id": "txn_1234567890abcdef",
    "decision_result": "APPROVE",
    "explanation": "Low risk transaction approved...",
    "confidence": 0.85,
    "model_provenance": {
        "model_name": "gpt-4o-mini",
        "provider": "azure_openai",
        "version": "1.0.0",
        "timestamp": "2024-01-01T12:00:00Z",
        "processing_time_ms": 250,
        "tokens_used": 150
    }
}

# Validate against ocn-common schema
is_valid = validate_explanation_contract(explanation_data)
```

### CloudEvent Validation

```python
from src.orca.core.contract_validation import validate_cloud_event_contract

ce_data = {
    "specversion": "1.0",
    "id": "test-event-id",
    "source": "https://orca.ocn.ai/decision-engine",
    "type": "ocn.orca.decision.v1",
    "subject": "txn_1234567890abcdef",
    "time": "2024-01-01T12:00:00Z",
    "data": {...}
}

# Validate against ocn-common schema
is_valid = validate_cloud_event_contract(ce_data, "orca.decision.v1")
```

## GitHub Workflows

### Contracts Validation (`contracts.yml`)

The contracts workflow validates:

- **ocn-common schema structure** and JSON Schema validity
- **Contract validation integration** with ocn-common schemas
- **Examples and fixtures** against contracts
- **CloudEvents integration** tests
- **AP2 contract compatibility** validation

```yaml
# Triggers
on:
  pull_request:
  push:
    branches: [main, develop]
  workflow_dispatch:
```

### Security Validation (`security.yml`)

The security workflow includes:

- **Python dependency audit** with pip-audit
- **Known vulnerability scan** with safety
- **Container security scan** with Trivy (if Dockerfile exists)
- **Code security analysis** with Bandit and Semgrep
- **Secrets detection** with TruffleHog

```yaml
# Triggers
on:
  pull_request:
  push:
    branches: [main, develop]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC
  workflow_dispatch:
```

## CLI Contract Validation

Use the contract validation script for manual validation:

```bash
# Validate decision files
python scripts/validate_contracts.py \
  --schema-type ap2_decision \
  --files fixtures/requests/*.json \
  --exit-on-failure

# Validate explanation files
python scripts/validate_contracts.py \
  --schema-type ap2_explanation \
  --files examples/explanations/*.json

# Validate CloudEvent files
python scripts/validate_contracts.py \
  --schema-type cloudevent:orca.decision.v1 \
  --files examples/events/*.json
```

## Integration Points

### Orca Core

- **CloudEvents emitter** validates all events against ocn-common schemas
- **Decision engine** validates AP2 contracts before processing
- **CLI commands** use contract validation for input validation

### Weave Subscriber

- **HTTP endpoints** validate incoming CloudEvents against ocn-common schemas
- **Receipt storage** validates AP2 contracts before blockchain storage
- **Audit events** conform to ocn-common audit schemas

### CI/CD Pipeline

- **Pre-commit hooks** validate contracts before commit
- **Pull request validation** ensures all contracts are valid
- **Release validation** confirms schema compatibility

## Testing

### Run Contract Validation Tests

```bash
# Run all contract validation tests
PYTHONPATH=src python -m pytest tests/test_contract_validation.py -v

# Run ocn-common integration tests
PYTHONPATH=src python -m pytest tests/test_ocn_common_integration.py -v

# Run CloudEvents integration tests
PYTHONPATH=src python -m pytest tests/events/ -v
```

### Test Schema Conformance

```bash
# Test with sample data
PYTHONPATH=src python -c "
from src.orca.core.contract_validation import get_contract_validator
validator = get_contract_validator()
print('✅ Contract validator initialized')
"
```

## Configuration

### Environment Variables

```bash
# ocn-common path (optional, defaults to external/ocn-common)
export OCN_COMMON_PATH="/path/to/ocn-common"

# Contract validation strict mode
export CONTRACT_VALIDATION_STRICT="true"
```

### Dependencies

The following packages are required for contract validation:

```toml
[project.optional-dependencies]
dev = [
    "jsonschema>=4.20.0",
    "pip-audit>=2.6.0",
    "safety>=2.3.0",
    "bandit>=1.7.0",
    "semgrep>=1.0.0"
]
```

## Schema Evolution

### Versioning Strategy

- **Major version changes**: Breaking changes to event structure
- **Minor version changes**: Additive changes (new optional fields)
- **Patch version changes**: Documentation updates, bug fixes

### Backward Compatibility

- All schema changes maintain backward compatibility within major versions
- New optional fields are added without breaking existing consumers
- Deprecated fields are marked but not removed immediately

### Migration Guide

When schemas are updated:

1. **Update ocn-common** submodule or dependency
2. **Run contract validation** to identify breaking changes
3. **Update code** to handle new schema requirements
4. **Test integration** with updated schemas
5. **Deploy** with backward compatibility

## Troubleshooting

### Common Issues

#### Schema Not Found
```
❌ No schema found for event type: orca.decision.v1
```

**Solution**: Ensure ocn-common is properly installed and schemas are available in `external/ocn-common/`.

#### Validation Failures
```
❌ AP2 decision contract validation failed
```

**Solution**: Check the decision data structure against the ocn-common schema requirements.

#### CI/CD Failures
```
❌ Contract validation failed in CI
```

**Solution**: Run contract validation locally and fix any schema conformance issues.

### Debug Mode

Enable debug logging for contract validation:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from src.orca.core.contract_validation import get_contract_validator
validator = get_contract_validator()
```

## Future Enhancements

### Planned Features

- **Schema registry** for dynamic schema loading
- **Validation metrics** and performance monitoring
- **Automated schema generation** from code annotations
- **Multi-version schema support** for gradual migrations

### Integration Roadmap

- **Event bus integration** with schema validation
- **API gateway** with contract validation
- **Monitoring dashboards** for contract compliance
- **Alerting** for schema validation failures

## References

- [ocn-common Repository](https://github.com/ocn-ai/ocn-common)
- [JSON Schema Specification](https://json-schema.org/)
- [CloudEvents Specification](https://cloudevents.io/)
- [AP2 Contract Documentation](./ap2_contract.md)
- [CloudEvents Integration Guide](./cloudevents_integration.md)
