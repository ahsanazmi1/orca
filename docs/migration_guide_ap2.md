# AP2 Migration Guide

This guide explains how to migrate from legacy Orca decision contracts to the new AP2-compliant format while maintaining backward compatibility.

## Overview

The AP2 (Agent Protocol 2) contract introduces a structured, standardized format for decision contracts that provides better interoperability, signing capabilities, and feature mapping. Legacy support is retained through adapters and feature flags.

## Version Information

- **AP2 Version**: 0.1.0
- **ML Model Version**: 1.0.0
- **Legacy Version**: 0.0.1
- **Content Type**: `application/vnd.ocn.ap2+json; version=1`

## Migration Paths

### 1. Legacy → AP2 Migration

Use the `decision_legacy_adapter.py` to convert legacy contracts to AP2 format:

```python
from src.orca.core.decision_legacy_adapter import LegacyToAP2Adapter

# Convert legacy contract to AP2
adapter = LegacyToAP2Adapter()
ap2_contract = adapter.from_legacy_json(legacy_json_string)

# Process with AP2 engine
from src.orca.core.rules_engine import AP2RulesEngine
engine = AP2RulesEngine()
outcome = engine.evaluate(ap2_contract)
```

### 2. AP2 → Legacy Migration

Convert AP2 contracts back to legacy format for backward compatibility:

```python
from src.orca.core.decision_legacy_adapter import AP2ToLegacyAdapter

# Convert AP2 contract to legacy
adapter = AP2ToLegacyAdapter()
legacy_json = adapter.to_legacy_json(ap2_contract)
```

## Feature Mapping

### Legacy Features → AP2 Features

| Legacy Feature | AP2 Path | Description |
|----------------|----------|-------------|
| `cart_total` | `cart.amount` | Transaction amount |
| `currency` | `cart.currency` | Currency code |
| `rail` | `payment.modality` | Payment rail (ACH, card, etc.) |
| `channel` | `intent.channel` | Transaction channel (web, pos, etc.) |
| `customer_id` | `intent.actor` | Customer identifier |
| `location_country` | `cart.geo.country` | Transaction location |
| `ip_country` | `cart.geo.ip_country` | IP-based location |
| `mcc` | `cart.mcc` | Merchant category code |
| `auth_requirements` | `payment.auth_requirements` | Authentication requirements |

### ML Model Features → AP2 Paths

| Model Feature | AP2 Path | Description |
|---------------|----------|-------------|
| `amount` | `cart.amount` | Transaction amount |
| `velocity_24h` | `velocity.24h` | 24-hour transaction velocity |
| `velocity_7d` | `velocity.7d` | 7-day transaction velocity |
| `cross_border` | `cart.geo.cross_border` | Cross-border transaction flag |
| `location_mismatch` | `cart.geo.location_mismatch` | Location mismatch flag |
| `payment_method_risk` | `payment.method_risk` | Payment method risk score |
| `chargebacks_12m` | `customer.chargebacks_12m` | 12-month chargeback count |
| `customer_age_days` | `customer.age_days` | Customer account age |
| `loyalty_score` | `customer.loyalty_score` | Customer loyalty score |
| `time_since_last_purchase` | `customer.time_since_last_purchase` | Time since last purchase |

## Model Versioning

### Model Retraining and Version Bumps

When retraining ML models, the `model_version` must be incremented to maintain compatibility:

1. **Feature Changes**: If features are added, removed, or reordered, bump the major version
2. **Model Architecture**: If the model type changes (e.g., XGBoost → Neural Network), bump the major version
3. **Training Data**: If training data changes significantly, bump the minor version
4. **Hyperparameters**: If hyperparameters change, bump the patch version

### Version Bump Examples

```python
# Major version bump (breaking changes)
"model_version": "2.0.0"  # New features, different model type

# Minor version bump (new features, backward compatible)
"model_version": "1.1.0"  # New features added

# Patch version bump (bug fixes, same features)
"model_version": "1.0.1"  # Bug fixes, same feature set
```

### Model Artifacts Structure

```
models/xgb/
├── 1.0.0/
│   ├── model.json          # XGBoost model
│   ├── calibrator.pkl      # Calibrated classifier
│   ├── scaler.pkl          # Feature scaler
│   ├── feature_spec.json   # Feature specification
│   └── metadata.json       # Model metadata
├── 1.1.0/                  # New version
│   └── ...
└── 2.0.0/                  # Breaking changes
    └── ...
```

## CLI Usage

### AP2 Mode (Default)

```bash
# Process AP2 contract
python -m orca.cli decide-file input.json --output output.json

# Generate AP2 sample
python -m orca.cli create-sample --output sample.json
```

### Legacy Mode

```bash
# Process with legacy output
python -m orca.cli decide-file input.json --output output.json --legacy-json

# Generate legacy sample
python -m orca.cli create-sample --output sample.json --legacy-json
```

## Environment Variables

### Feature Flags

- `ORCA_USE_XGB=true` - Enable real ML model (default: false, uses stub)
- `ORCA_ENABLE_SHAP=true` - Enable SHAP explanations (default: false)
- `ORCA_SIGN_DECISIONS=true` - Enable decision signing (default: false)
- `ORCA_RECEIPT_HASH_ONLY=true` - Enable receipt hashing only (default: false)

### Version Control

- `AP2_VERSION=0.1.0` - AP2 contract version
- `ML_MODEL_VERSION=1.0.0` - ML model version
- `XGBOOST_RANDOM_STATE=42` - Deterministic XGBoost
- `PYTHONHASHSEED=0` - Deterministic Python hashing

## API Integration

### Content Type Headers

```http
# AP2 contract
Content-Type: application/vnd.ocn.ap2+json; version=1

# Legacy contract
Content-Type: application/json
```

### Request/Response Format

#### AP2 Request
```json
{
  "ap2_version": "0.1.0",
  "intent": {
    "actor": "human",
    "intent_type": "purchase",
    "channel": "web",
    "agent_presence": "none",
    "timestamps": {
      "created": "2024-01-01T10:00:00Z",
      "expires": "2024-01-01T11:00:00Z"
    }
  },
  "cart": {
    "items": [...],
    "amount": "100.00",
    "currency": "USD",
    "mcc": "5812",
    "geo": {
      "country": "US",
      "ip_country": "US"
    }
  },
  "payment": {
    "instrument_ref": "card_123",
    "modality": "immediate",
    "auth_requirements": ["pin"]
  }
}
```

#### AP2 Response
```json
{
  "ap2_version": "0.1.0",
  "intent": {...},
  "cart": {...},
  "payment": {...},
  "decision": {
    "result": "APPROVE",
    "risk_score": 0.15,
    "reasons": [
      {
        "code": "APPROVED",
        "detail": "Transaction approved"
      }
    ],
    "actions": [
      {
        "type": "process_payment",
        "detail": "Process payment normally"
      }
    ],
    "meta": {
      "model": "xgboost",
      "model_version": "1.0.0",
      "model_sha256": "abc123...",
      "trace_id": "uuid-here",
      "version": "0.1.0"
    }
  },
  "signing": {
    "vc_proof": {...},
    "receipt_hash": "sha256-hash"
  }
}
```

## Testing

### Round-trip Tests

Test that legacy → AP2 → legacy conversion preserves semantics:

```python
def test_round_trip_conversion():
    # Start with legacy contract
    legacy_contract = {...}

    # Convert to AP2
    ap2_contract = legacy_to_ap2_adapter.from_legacy_json(legacy_contract)

    # Convert back to legacy
    converted_legacy = ap2_to_legacy_adapter.to_legacy_json(ap2_contract)

    # Verify key fields are preserved
    assert converted_legacy["decision"] == legacy_contract["decision"]
    assert converted_legacy["risk_score"] == legacy_contract["risk_score"]
```

### Feature Drift Tests

Test that model versioning prevents feature drift:

```python
def test_feature_drift_guard():
    # Test with missing features
    incomplete_features = {"amount": 100.0}

    with pytest.raises(ValueError, match="Feature drift detected"):
        predict_risk(incomplete_features)
```

## Troubleshooting

### Common Issues

1. **Feature Drift Error**: Model expects different features than provided
   - **Solution**: Update feature extraction or retrain model with new version

2. **Version Mismatch**: AP2 version not supported
   - **Solution**: Update to supported AP2 version or use legacy adapter

3. **Model Loading Failed**: Model artifacts not found
   - **Solution**: Ensure model artifacts exist in `models/xgb/` directory

4. **SHAP Not Available**: SHAP explanations not working
   - **Solution**: Install SHAP with `pip install shap` or disable with `ORCA_ENABLE_SHAP=false`

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
export ORCA_DEBUG=true
python -m orca.cli decide-file input.json --verbose
```

## Best Practices

1. **Always use versioning**: Include version information in all contracts
2. **Test round-trips**: Verify legacy ↔ AP2 conversions preserve semantics
3. **Monitor feature drift**: Set up alerts for feature drift detection
4. **Document model changes**: Update model version when retraining
5. **Use content types**: Set appropriate content type headers for APIs
6. **Enable signing in production**: Use `ORCA_SIGN_DECISIONS=true` for audit trails

## Support

For questions or issues with AP2 migration:

1. Check this migration guide
2. Review the test suite in `tests/schemas/`
3. Examine golden files in `tests/golden/`
4. Contact the Orca Core team

## Changelog

### v0.1.0 (AP2 Introduction)
- ✅ AP2 contract format introduced
- ✅ Legacy support retained behind `--legacy-json` flag
- ✅ Model versioning system implemented
- ✅ Feature drift guard added
- ✅ SHAP explanations support
- ✅ Decision signing and receipt hashing
- ✅ Round-trip conversion tests
