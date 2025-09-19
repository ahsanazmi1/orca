# Orca — The Open Checkout Agent

**Anchor story:** Checkout hasn't changed in 20 years. **B2B payments are even worse.**
**Orca** is the first **open, transparent, merchant-controlled checkout agent** with explainability built in.

## Why Orca
- Today: black-box fraud/routing decisions from processors.
- Problem: merchants can't see *why* transactions are approved, declined, or routed.
- Orca: open **JSON Decision Contract** + clear, human/AI explanations.

## Who It's For (Initial ICPs)
- **Mid-market SaaS** – embedded payments, need developer-first control.
- **Marketplaces** – multi-party routing + seller trust.
- **Exporters (International B2B)** – cross-border transparency and higher auth rates.

## What's Here in Phase 1 (Weeks 1–4)
- Repo + roadmap public
- Rules engine skeleton
- JSON decision contract draft
- Local demos: CLI + Streamlit stubs
- Community docs (contributing, templates)

## Quick Start (Local)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
python -m orca.cli --help
streamlit run examples/streamlit_demo.py
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

## Documentation

- **[AP2 Contract Specification](docs/ap2_contract.md)** - Complete AP2 decision contract documentation
- **[Explainability Guide](docs/phase2_explainability.md)** - How explanations work with AP2 field references
- **[Migration Guide](docs/migration_guide_ap2.md)** - Migrating from legacy to AP2 format
- **[Keys & Secrets](docs/keys.md)** - Cryptographic key management
- **[Roadmap](docs/roadmap.md)** - Development roadmap and milestones

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md). Star/watch the repo to follow progress.
