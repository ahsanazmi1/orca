# 🚀 Orca Core v0.3.0-ap2 Release Notes

## 🎯 First AP2-Compliant Release

This release introduces the **Agent Protocol 2 (AP2)** compliant decision engine, marking a major milestone in Orca's evolution from stub implementations to a production-ready system with real machine learning models and cryptographic security.

## ✨ What's New

### 🏗️ AP2 Decision Contract
- **Complete AP2 implementation** with structured mandates (Intent, Cart, Payment)
- **Backward compatibility** through legacy adapters with `--legacy-json` flag
- **JSON Schema validation** for all AP2 contracts
- **Type-safe implementation** with comprehensive Pydantic models

### 🤖 Real Machine Learning
- **XGBoost model v1.0.0** with calibration and feature importance
- **SHAP explanations** for model interpretability
- **Deterministic inference** with fixed random seeds for reproducibility
- **Model registry** with versioning and artifact management

### 🔐 Cryptographic Security
- **Ed25519 digital signatures** with verifiable credentials
- **Receipt hashing** for privacy-preserving audit trails
- **Environment flags** for signing configuration (`ORCA_SIGN_DECISIONS`)
- **Key management** for local development and production

### 🧠 Explainable AI
- **AP2 field references** with 50+ valid paths and validation
- **Hallucination prevention** through field guardrails
- **Natural language generation** for human-readable explanations
- **Key signals mapping** to AP2 JSONPaths

## 📊 Model Artifacts

| Artifact | SHA-256 Hash | Purpose |
|----------|--------------|---------|
| `calibrator.pkl` | `4528c383bbe1e93ca9913a468a68f79ee53dd8a364d93d351928a5cdb6c9a211` | Model calibration |
| `scaler.pkl` | `a9cae63297a1d2560ff4c866911a4dd4c580fc0c70de7015d626ba01f747b0b6` | Feature scaling |
| `feature_spec.json` | `2de471da947c018c842a1c2e8db8c9e70cebfd6d9ae0fe4e6d408378783926d4` | Feature specification |
| `metadata.json` | `c288e0b6489031d824a8c8a953abfff1358e7accb11985034766e2cd180bf34d` | Model metadata |
| `model.json` | `293297e4785c4857fcef31b2bf8d2457a0f909970d06ce3027e807a5c759283c` | XGBoost model |

## 🔄 Breaking Changes

### Decision Contract Format
- **Default format**: Now AP2 instead of legacy
- **Legacy support**: Available via `--legacy-json` flag
- **Field mapping**: Some fields renamed or restructured

### Environment Variables
```bash
# New signing configuration
ORCA_SIGN_DECISIONS=true
ORCA_SIGNING_KEY_PATH=./keys/private.pem
ORCA_RECEIPT_HASH_ONLY=true

# ML configuration
ORCA_MODEL_DIR=./models/xgb
ORCA_ENABLE_SHAP=true

# Azure OpenAI (for explanations)
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
```

### CLI Changes
```bash
# AP2 format (default)
python -m orca.cli decide-file sample.json

# Legacy format
python -m orca.cli decide-file sample.json --legacy-json

# With explanations
python -m orca.cli decide-file sample.json --explain
```

## 📚 Documentation

### New Guides
- **[AP2 Contract Specification](docs/ap2_contract.md)**: Complete AP2 format documentation
- **[Migration Guide](docs/migration_guide_ap2.md)**: Legacy to AP2 migration
- **[Explainability Guide](docs/phase2_explainability.md)**: AP2 field references and NLG
- **[Keys & Secrets](docs/keys.md)**: Cryptographic key management

### Updated Documentation
- **[README.md](README.md)**: AP2 examples and feature overview
- **[CHANGELOG.md](CHANGELOG.md)**: Release notes and breaking changes

## 🧪 Testing & Quality

### Sample Data
- **21 sample files**: 7 AP2, 7 legacy, 7 golden decision outputs
- **Schema validation**: All samples validate against AP2 schemas
- **Round-trip testing**: Legacy ↔ AP2 conversion preserves semantics

### CI Pipeline
- **Schema validation**: AP2 contract compliance
- **Crypto determinism**: Signing and hashing consistency
- **Golden snapshots**: Decision output stability
- **Feature spec validation**: ML feature specification compliance
- **SHAP snapshots**: Model explanation consistency

## 🚀 Getting Started

### 1. Install Dependencies
```bash
# Install with all extras
uv sync --all-extras --dev

# Or with pip
pip install -e ".[all]"
```

### 2. Configure Environment
```bash
# Copy example environment
cp .env.example .env

# Edit configuration
nano .env
```

### 3. Generate Test Keys (Development)
```bash
# Generate Ed25519 test keys
python scripts/generate_test_keys.py

# Keys will be created in ./keys/
```

### 4. Run Sample Decision
```bash
# AP2 format
python -m orca.cli decide-file samples/ap2/approve_card_low_risk.json

# Legacy format
python -m orca.cli decide-file samples/legacy/approve_card_low_risk.json --legacy-json

# With explanations
python -m orca.cli decide-file samples/ap2/approve_card_low_risk.json --explain
```

### 5. Validate Samples
```bash
# Validate all sample files
python scripts/validate_samples.py
```

## 🔮 What's Next

### v0.3.1-ml (Planned)
- **Enhanced SHAP integration** with more detailed explanations
- **Model performance monitoring** and drift detection
- **Advanced calibration** with temperature scaling
- **Feature importance visualization** improvements

### Future Releases
- **Multi-model support** with ensemble methods
- **Real-time model updates** with A/B testing
- **Advanced cryptography** with threshold signatures
- **Performance optimizations** for high-throughput scenarios

## 🎉 Acknowledgments

This release represents a significant milestone in Orca's development, transitioning from prototype to production-ready system. Special thanks to the development team for their dedication to quality, security, and maintainability.

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/ahsanazmi1/orca/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ahsanazmi1/orca/discussions)

---

**Full Changelog**: https://github.com/ahsanazmi1/orca/compare/v0.2.0...v0.3.0-ap2
