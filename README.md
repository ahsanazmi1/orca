# Orca — The Open Checkout Agent

[![Latest Release](https://img.shields.io/github/v/release/ocn-ai/orca?label=latest%20release)](https://github.com/ocn-ai/orca/releases/latest)
[![Contracts Validation](https://github.com/ocn-ai/orca/actions/workflows/contracts.yml/badge.svg)](https://github.com/ocn-ai/orca/actions/workflows/contracts.yml)
[![Security Validation](https://github.com/ocn-ai/orca/actions/workflows/security.yml/badge.svg)](https://github.com/ocn-ai/orca/actions/workflows/security.yml)
[![CI](https://github.com/ocn-ai/orca/actions/workflows/ci.yml/badge.svg)](https://github.com/ocn-ai/orca/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/ocn-ai/orca/branch/main/graph/badge.svg)](https://codecov.io/gh/ocn-ai/orca)

## Phase 2 — Explainability

🚧 **Currently in development** - Phase 2 focuses on enhanced explainability features and advanced decision transparency.

- **Status**: Active development on `phase-2-explainability` branch
- **Features**: Enhanced explainability, LLM-powered explanations, comprehensive audit trails
- **Issue Tracker**: [Phase 2 Issues](https://github.com/ocn-ai/orca/issues?q=is%3Aopen+is%3Aissue+label%3Aphase-2)
- **Timeline**: Weeks 4-8 of OCN development roadmap

**Anchor story:** Checkout hasn't changed in 20 years. **B2B payments are even worse.**
**Orca** is the first **open, transparent, merchant-controlled checkout agent** with explainability built in for the [Open Checkout Network (OCN)](https://github.com/ocn-ai/ocn-common).

## 🎯 Phase 1 Complete: v0.1.0+ap2.v1+ce.v1

**Latest Release**: [v0.1.0+ap2.v1+ce.v1](https://github.com/ocn-ai/orca/releases/latest)

Orca Phase 1 delivers a complete rules engine with CloudEvents integration, AP2 decision contracts, and Weave blockchain receipt storage. This release establishes the foundation for open, transparent, merchant-controlled checkout with explainability built in.

## Why Orca
- Today: black-box fraud/routing decisions from processors.
- Problem: merchants can't see *why* transactions are approved, declined, or routed.
- Orca: open **JSON Decision Contract** + clear, human/AI explanations.

## Who It's For (Initial ICPs)
- **Mid-market SaaS** – embedded payments, need developer-first control.
- **Marketplaces** – multi-party routing + seller trust.
- **Exporters (International B2B)** – cross-border transparency and higher auth rates.

## What's Here in Phase 1 ✅
- **Deterministic Rules Engine**: Complete rules engine with APPROVE/DECLINE/REVIEW outcomes
- **AP2 Decision Contract v1**: Standardized decision payload format with full traceability
- **CloudEvents v1 Integration**: Event-driven architecture with ocn.orca.decision.v1 and ocn.orca.explanation.v1
- **Weave Blockchain Integration**: Receipt storage for immutable audit trails
- **ocn-common Schema Validation**: Cross-stack contract validation and compliance
- **CLI + Streamlit Demos**: Complete local demos with CloudEvents emission
- **Security-First CI/CD**: Comprehensive GitHub workflows for contracts and security validation
- **Community Docs**: Contributing guides, templates, and comprehensive documentation

## Quickstart (≤ 60s)

Get up and running with Orca in under a minute:

```bash
# Clone the repository
git clone https://github.com/ahsanazmi1/orca.git
cd orca

# Setup everything (venv, deps, pre-commit hooks)
make setup

# Run tests to verify everything works
make test

# Start the service
make run
```

**That's it!** 🎉

The service will be running at `http://localhost:8080`. Test the endpoints:

```bash
# Health check
curl http://localhost:8080/health

# MCP getStatus
curl -X POST http://localhost:8080/mcp/invoke \
  -H "Content-Type: application/json" \
  -d '{"verb": "getStatus", "args": {}}'

# MCP getDecisionSchema
curl -X POST http://localhost:8080/mcp/invoke \
  -H "Content-Type: application/json" \
  -d '{"verb": "getDecisionSchema", "args": {}}'
```

### Additional Makefile Targets

```bash
make lint        # Run code quality checks
make fmt         # Format code with black/ruff
make clean       # Remove virtual environment and cache
make help        # Show all available targets
```

## Manual Setup (Alternative)

If you prefer manual setup over the Makefile:

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run tests
pytest -q

# Start the service
uvicorn orca_api.main:app --reload
```

### Example Output
```json
{
  "status": "success",
  "receipt": {
    "trace_id": "txn_1234567890abcdef",
    "receipt_hash": "sha256:abc123def456789",
    "event_type": "decision",
    "block_height": 1000001,
    "transaction_hash": "0x1234567890abcdef",
    "status": "success"
  }
}
```

## AP2 Decision Contract (v0.1.0)

Orca uses the **AP2 (Agent Protocol v2) Decision Contract** for transparent, explainable payment decisions with cryptographic integrity.

### Quick Example
```json
{
  "ap2_version": "0.1.0",
  "intent": {
    "actor": {
      "id": "customer_123",
      "type": "individual",
      "metadata": {
        "loyalty_score": 0.8,
        "age_days": 365
      }
    },
    "channel": "web",
    "geo": { "country": "US", "region": "CA" },
    "metadata": {
      "velocity_24h": 2.0,
      "velocity_7d": 5.0
    }
  },
  "cart": {
    "amount": "89.99",
    "currency": "USD",
    "items": [
      {
        "name": "Software License",
        "category": "software",
        "mcc": "5734"
      }
    ]
  },
  "payment": {
    "method": "card",
    "modality": "immediate",
    "auth_requirements": ["none"]
  },
  "decision": {
    "result": "APPROVE",
    "risk_score": 0.15,
    "reasons": [
      {
        "type": "low_risk",
        "message": "Low risk transaction",
        "confidence": 0.9,
        "ap2_path": "intent.metadata.velocity_24h"
      }
    ],
    "actions": [
      {
        "type": "route",
        "target": "PROCESSOR_A"
      }
    ],
    "meta": {
      "model": "model:xgb",
      "model_version": "1.0.0",
      "trace_id": "uuid-1234",
      "processing_time_ms": 45,
      "version": "0.1.0"
    }
  },
  "signing": {
    "vc_proof": null,
    "receipt_hash": "sha256:abc123def456..."
  }
}
```

### Legacy vs AP2 Comparison

| Legacy (v0) | AP2 (v0.1.0) | Notes |
|-------------|--------------|-------|
| `decision: "APPROVE"` | `decision.result: "APPROVE"` | Structured decision object |
| `risk_score: 0.15` | `decision.risk_score: 0.15` | Moved to decision section |
| `reasons: ["velocity_flag"]` | `decision.reasons[].message` | Structured reason objects |
| `meta.trace_id` | `decision.meta.trace_id` | Moved to decision meta |
| `amount: 89.99` | `cart.amount: "89.99"` | Structured cart section |
| `mcc: "5734"` | `cart.items[].mcc: "5734"` | Moved to cart items |
| `payment_method: "card"` | `payment.method: "card"` | Structured payment section |
| `channel: "online"` | `intent.channel: "web"` | Structured intent section |

### Key Features

- **🔍 Full Transparency**: Every decision field is clearly defined and accessible
- **📊 Rich Context**: Intent, cart, and payment details in structured format
- **🤖 ML Integration**: Model metadata and versioning built-in
- **🔐 Cryptographic Integrity**: Verifiable credentials and receipt hashes
- **📝 Explainable**: AP2 field references in all explanations
- **🔄 Backward Compatible**: Legacy adapter for existing integrations

## Structured Logging & Redaction

Orca implements enterprise-grade structured JSON logging with automatic redaction of sensitive data:

### Features
- **JSON Format**: All logs are structured JSON for easy parsing and analysis
- **Trace ID Binding**: Every log automatically includes the current trace ID for correlation
- **Sensitive Data Redaction**: Automatic masking of:
  - PAN (Primary Account Numbers): 13-19 digits → `[PAN_REDACTED]`
  - CVV (Card Verification Values): 3-4 digits near 'cvv' → `[CVV_REDACTED]`
  - Expiry dates: MM/YY format → `[EXPIRY_REDACTED]`
  - Email addresses: user@domain.com → `[EMAIL_REDACTED]`

### Usage
```python
from src.orca.logging_setup import get_traced_logger, setup_logging

# Set up logging (done automatically in app/CLI startup)
setup_logging(level='INFO', format_type='json')

# Get logger with automatic trace ID binding
logger = get_traced_logger(__name__)
logger.info("Processing payment for user@example.com with card ending in 1111")
```

### Example Output
```json
{
  "timestamp": "2024-01-21T12:00:00Z",
  "level": "INFO",
  "logger": "src.orca.engine",
  "message": "Processing payment for [EMAIL_REDACTED] with card ending in [PAN_REDACTED]",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "module": "engine",
  "function": "process_payment",
  "line": 142
}
```

## Documentation

- **[AP2 Contract Specification](docs/ap2_contract.md)** - Complete AP2 decision contract documentation
- **[Explainability Guide](docs/phase2_explainability.md)** - How explanations work with AP2 field references
- **[Migration Guide](docs/migration_guide_ap2.md)** - Migrating from legacy to AP2 format
- **[Keys & Secrets](docs/keys.md)** - Cryptographic key management
- **[Roadmap](docs/roadmap.md)** - Development roadmap and milestones

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md). Star/watch the repo to follow progress.
