# Orca Core Decision Engine

A production-ready decision engine for e-commerce applications, built with Python and designed for high-performance rule evaluation with ML integration.

## What is Orca?

Orca Core is an open-source decision engine that provides transparent, explainable payment processing decisions. Unlike traditional payment gateways that operate as "black boxes," Orca exposes the complete decision logic through structured JSON responses with human-readable explanations.

### Key Differentiators

- **🔍 Transparency**: Every decision includes machine-readable reasons and human explanations
- **⚡ Performance**: Sub-millisecond decision evaluation with ML integration
- **🛡️ Security**: Comprehensive rule system with configurable risk thresholds
- **🔧 Extensibility**: Modular architecture for custom rule development
- **📊 Observability**: Rich metadata and audit trails for every decision

## Features

- **Fast Decision Making**: Evaluate complex business rules in milliseconds
- **ML Integration**: Machine learning risk prediction with configurable thresholds
- **Modular Rules System**: Extensible rule registry with easy rule addition
- **Type Safety**: Built with Pydantic for robust data validation
- **CLI Interface**: Command-line tool for quick decision evaluation
- **Streamlit Demo**: Interactive web interface with rail/channel toggles
- **Human Explanations**: Plain-English decision explanations for merchants
- **Production Ready**: Comprehensive testing, linting, and CI/CD pipeline

## Quick Start

### Prerequisites

- Python 3.11+ (recommended: Python 3.12)
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/orca-team/orca-core.git
cd orca-core

# Install dependencies and setup development environment
uv sync --dev

# Activate virtual environment (if using uv)
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Initialize development environment
make init
```

### Usage

#### Command Line Interface

```bash
# Evaluate a Card transaction with rail and channel
uv run python -m orca_core.cli decide-file fixtures/week4/requests/card_approve_small.json

# Example output
{
  "status": "APPROVE",
  "reasons": ["LOYALTY_BOOST: Customer has GOLD loyalty tier"],
  "actions": ["LOYALTY_BOOST"],
  "meta": {
    "timestamp": "2025-01-15T10:30:45.123456",
    "transaction_id": "txn_a82c4dfcfbe945e4",
    "rail": "Card",
    "channel": "online",
    "cart_total": 150.0,
    "risk_score": 0.15,
    "rules_evaluated": []
  },
  "decision": "APPROVE",
  "explanation_human": "Approved: Customer loyalty tier provides approval boost."
}

# Evaluate an ACH transaction
uv run python -m orca_core.cli decide-file fixtures/week4/requests/ach_decline_limit.json

# Example output
{
  "status": "DECLINE",
  "reasons": ["ach_limit_exceeded"],
  "actions": ["block_transaction"],
  "meta": {
    "timestamp": "2025-01-15T10:30:45.123456",
    "transaction_id": "txn_82803fa162594a60",
    "rail": "ACH",
    "channel": "online",
    "cart_total": 2500.0,
    "risk_score": 0.15,
    "rules_evaluated": ["ACH_LIMIT"]
  },
  "decision": "DECLINE",
  "explanation_human": "Declined: ACH transaction limit exceeded. Please use a different payment method."
}

# Batch process multiple files
uv run python -m orca_core.cli decide-batch --glob "fixtures/week4/requests/*.json"

# Get plain-English explanation
uv run python -m orca_core.cli explain fixtures/week4/requests/card_route_location_mismatch.json

# Example output
Under review: High-value card transaction requires additional verification. Please check your email for next steps. Additionally, under review: additional verification required for online card transaction.
```

#### Python API

```python
from orca_core.engine import evaluate_rules
from orca_core.models import DecisionRequest

# Create a request with rail and channel
request = DecisionRequest(
    cart_total=150.0,
    currency="USD",
    rail="Card",
    channel="online",
    features={"velocity_24h": 1.0, "risk_score": 0.15},
    context={
        "location_ip_country": "US",
        "billing_country": "US",
        "customer": {
            "loyalty_tier": "GOLD",
            "chargebacks_12m": 0
        }
    }
)

# Evaluate decision
response = evaluate_rules(request)
print(f"Status: {response.status}")
print(f"Decision: {response.decision}")  # Legacy field
print(f"Reasons: {response.reasons}")
print(f"Actions: {response.actions}")
print(f"Transaction ID: {response.meta.transaction_id}")
print(f"Risk Score: {response.meta.risk_score}")
print(f"Human Explanation: {response.explanation_human}")
```

#### FastAPI Web Service

Start the API server:

```bash
# Run the FastAPI service
uv run python -m orca_api.main

# Or with uvicorn directly
uv run uvicorn orca_api.main:app --host 0.0.0.0 --port 8080
```

The API provides three endpoints:

**Health Check:**
```bash
curl http://localhost:8080/healthz
# Response: {"ok": true}
```

**Decision Evaluation:**
```bash
curl -X POST http://localhost:8080/decision \
  -H "Content-Type: application/json" \
  -d '{
    "cart_total": 150.0,
    "currency": "USD",
    "rail": "Card",
    "channel": "online",
    "features": {"velocity_24h": 1.0},
    "context": {"customer": {"loyalty_tier": "GOLD"}}
  }'

# Response:
{
  "decision": "APPROVE",
  "reasons": ["LOYALTY_BOOST: Customer has GOLD loyalty tier"],
  "actions": ["LOYALTY_BOOST"],
  "meta": {
    "timestamp": "2025-01-15T10:30:45.123456",
    "transaction_id": "txn_a82c4dfcfbe945e4",
    "rail": "Card",
    "channel": "online",
    "cart_total": 150.0,
    "risk_score": 0.15,
    "rules_evaluated": []
  },
  "status": "APPROVE",
  "explanation_human": "Approved: Customer loyalty tier provides approval boost."
}
```

**Decision Explanation:**
```bash
curl -X POST http://localhost:8080/explain \
  -H "Content-Type: application/json" \
  -d '{
    "decision": {
      "decision": "DECLINE",
      "reasons": ["HIGH_TICKET: Amount exceeds card threshold of $5000"],
      "actions": ["BLOCK"],
      "meta": {"risk_score": 0.9, "cart_total": 10000.0},
      "status": "DECLINE"
    }
  }'

# Response:
{
  "explanation": "Declined: Amount exceeds card threshold of $5,000. Please try a smaller amount or contact support."
}
```

**Interactive API Documentation:**
- Visit http://localhost:8080/docs for Swagger UI
- Visit http://localhost:8080/redoc for ReDoc documentation

#### Streamlit Demo

```bash
# Launch interactive demo with rail/channel toggles
make demo
```

The demo includes:
- **Rail/Channel Toggles**: Switch between Card/ACH and online/pos
- **ML Toggle**: Switch between "Rules only" and "Rules + ML" modes
- **Risk Score Display**: Color-coded risk metrics (🟢 Low, 🟡 Medium, 🔴 High)
- **Two-column Layout**: Input controls on left, JSON results on right
- **Real-time Updates**: Instant decision evaluation as you change inputs
- **Plain-English Explanations**: Toggle between JSON output and human-readable explanations

#### Week 4 — Enhanced Explanation Demo

```bash
# Launch enhanced explanation demo
streamlit run apps/explain/app_streamlit.py
```

The enhanced demo includes:
- **File Upload**: Upload transaction JSON files for analysis
- **Rail/Channel Controls**: UI toggles for payment rail and channel selection
- **Human Explanations**: Clear, non-technical explanations of decisions
- **Copy/Download JSON**: Copy decision JSON to clipboard or download as file
- **Example Files**: Pre-built examples for all Week 4 scenarios
- **Improved Layout**: Clear sections for upload, parameters, decision, and explanation

#### Explain Decisions

Get natural-language explanations for decision responses:

```bash
# Explain a high-ticket, high-velocity decision
uv run python -m orca_core.cli explain '{"cart_total": 750, "features": {"velocity_24h": 4}}'

# Example output
The cart total was unusually high, so the transaction was flagged for review. This customer made multiple purchases in a short time, which triggered a velocity check. Final decision: REVIEW.
```

The explain command is perfect for:
- **Customer Support**: Provide clear explanations to merchants
- **Debugging**: Understand why specific decisions were made
- **Documentation**: Generate human-readable decision logs
- **Compliance**: Create audit trails with plain-English reasoning

**Streamlit Demo Integration**: The web interface now includes a "Plain-English Explanation" tab that automatically converts technical decision responses into merchant-friendly explanations, making it easy for non-technical users to understand decision logic.

## Roadmap

### ✅ Completed (Weeks 1-4)

- **Week 1**: Basic decision engine with simple approve/decline logic
- **Week 2**: Added rail/channel support and enhanced metadata structure
- **Week 3**: Added human-readable explanations with template system
- **Week 4**: Refined schema with structured metadata and canonical reason/action codes

### 🚧 Upcoming (Weeks 5+)

- **Week 5**: Advanced ML integration with real-time model serving
- **Week 6**: Multi-tenant support with merchant-specific rule configurations
- **Week 7**: Real-time monitoring and alerting dashboard
- **Week 8**: Performance optimization and horizontal scaling
- **Week 9**: Advanced fraud detection with behavioral analysis
- **Week 10**: Production deployment and monitoring infrastructure

## Validation Notes

### Transparency vs. Opacity

Orca Core provides unprecedented transparency in payment decision-making:

- **✅ Open Source**: Complete source code available for inspection
- **✅ Structured Output**: Machine-readable JSON with canonical reason/action codes
- **✅ Human Explanations**: Plain-English explanations for every decision
- **✅ Audit Trails**: Complete metadata including timestamps, transaction IDs, and rule evaluations
- **✅ Extensible Rules**: Modular rule system allows custom business logic

### Evidence and Documentation

- **Schema Documentation**: Complete contract specification in [`docs/contract.md`](docs/contract.md)
- **Sample Fixtures**: Curated test cases in [`fixtures/week4/`](fixtures/week4/) with request/response pairs
- **Validation Results**: Comprehensive test suite with 90+ tests and 67% coverage
- **Performance Benchmarks**: Sub-millisecond decision evaluation with ML integration
- **Reviewer Feedback**: Merchant and developer feedback captured in [`docs/validation/`](docs/validation/)

## Phase 1 Scope

### Current Implementation

**Rules System:**
- **HighTicketRule**: Cart total > $500 → REVIEW
- **VelocityRule**: 24h velocity > 3 → REVIEW
- **HighRiskRule**: ML risk score > 0.80 → DECLINE

**ML Integration:**
- **Risk Prediction**: `predict_risk(features)` returns 0.15 by default
- **Configurable Thresholds**: All rules support custom thresholds
- **Meta Data**: Risk score always included in response metadata

**Decision Priority:**
1. **DECLINE** (highest) - HighRiskRule triggers
2. **REVIEW** - HighTicketRule or VelocityRule triggers
3. **APPROVE** (default) - No rules trigger

### Local Development Only

This is a **local development** implementation focused on:
- Core decision engine architecture
- Rule system extensibility
- ML hooks integration
- API contract stability
- Development tooling and testing

## Decision Rules

### HIGH_TICKET Rule
- **Condition**: Cart total > $500
- **Decision**: REVIEW
- **Reason**: "HIGH_TICKET: Cart total $X exceeds $500.00 threshold"
- **Action**: "ROUTE_TO_REVIEW"

### VELOCITY Rule
- **Condition**: `features['velocity_24h'] > 3`
- **Decision**: REVIEW
- **Reason**: "VELOCITY_FLAG: 24h velocity X exceeds 3.0 threshold"
- **Action**: "ROUTE_TO_REVIEW"

### HIGH_RISK Rule
- **Condition**: ML risk score > 0.80
- **Decision**: DECLINE
- **Reason**: "HIGH_RISK: ML risk score X exceeds 0.800 threshold"
- **Action**: "BLOCK"

## Development

### Setup

```bash
# Install development dependencies
make init

# Run tests
make test

# Run linting
make lint

# Format code
make format

# Run demo
make demo

# Check system health
make doctor
```

### Project Structure

```
orca-core/
├── src/orca_core/              # Main package
│   ├── __init__.py
│   ├── models.py               # Pydantic models
│   ├── engine.py               # Decision engine
│   ├── cli.py                  # CLI interface
│   ├── core/                   # Core modules
│   │   ├── __init__.py
│   │   ├── ml_hooks.py         # ML prediction functions
│   │   ├── explainer.py        # Decision explanation module
│   │   └── feature_extraction.py # Feature extraction utilities
│   └── rules/                  # Rules system
│       ├── __init__.py
│       ├── base.py             # Base rule class
│       ├── builtins.py         # Built-in rules
│       ├── high_ticket.py      # High ticket rule
│       ├── velocity.py         # Velocity rule
│       ├── high_risk.py        # High risk rule
│       └── registry.py         # Rules orchestrator
├── tests/                      # Test suite
│   ├── test_models.py          # Model tests
│   ├── test_engine.py          # Engine tests
│   ├── test_rules.py           # Rules tests
│   ├── test_ml_hooks.py        # ML tests
│   ├── test_explainer.py       # Explainer tests
│   ├── test_feature_extraction.py # Feature extraction tests
│   ├── test_fixtures_param.py  # Parametrized fixture tests
│   ├── test_high_risk_rule.py  # High risk rule tests
│   └── test_golden.py          # Golden/snapshot tests
├── demos/                      # Streamlit demo
├── fixtures/                   # Test fixtures
│   └── requests/               # Sample decision requests
├── scripts/                    # Development scripts
└── .github/workflows/          # CI/CD pipeline
```

## Troubleshooting

### System Health Check

```bash
# Run comprehensive system check
make doctor
```

This will verify:
- ✅ **Required Tools**: git, gh, python>=3.11, pip, pipx, uv, make, pre-commit, ruff, black, mypy, pytest, bandit, streamlit
- ⚠️ **Optional Tools**: node, docker
- 📊 **Versions**: All tool versions and installation status

### Common Issues

**1. Import Errors**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Reinstall dependencies
uv sync --dev
```

**2. Missing Tools**
```bash
# Install missing tools (Windows)
scripts/install_win.ps1

# Install missing tools (macOS)
scripts/install_mac.sh
```

**3. Test Failures**
```bash
# Run specific test file
uv run pytest tests/test_engine.py -v

# Run with coverage
uv run pytest --cov=src/orca_core
```

**4. Linting Issues**
```bash
# Auto-fix linting issues
uv run ruff check . --fix
uv run ruff format .
```

## API Reference

### Models

#### DecisionRequest

```python
class DecisionRequest(BaseModel):
    cart_total: float                    # Total cart value (required)
    currency: str = "USD"                # Currency code
    features: dict[str, float] = {}      # Feature values (e.g., velocity_24h)
    context: dict[str, Any] = {}         # Additional context
```

#### DecisionResponse

```python
class DecisionResponse(BaseModel):
    decision: str                        # Decision result (APPROVE/REVIEW/DECLINE)
    reasons: list[str] = []              # Reasoning for decision
    actions: list[str] = []              # Recommended actions
    meta: dict[str, Any] = {}            # Additional metadata (includes risk_score)
```

### Functions

#### evaluate_rules(request: DecisionRequest) -> DecisionResponse

Evaluates all configured rules against the provided request and returns a decision response with ML risk prediction.

#### predict_risk(features: dict[str, float]) -> float

ML hook for risk prediction. Returns risk score between 0.0 and 1.0 (0.0 = low risk, 1.0 = high risk).

#### explain_decision(response: DecisionResponse) -> str

Converts a decision response into a plain-English explanation. Maps technical reason codes to human-readable sentences and always includes a final decision summary.

## Testing

### Test Suite

- **90 tests** with **67% coverage**
- **Golden tests** for API contract stability
- **Unit tests** for all components
- **Integration tests** for rule combinations
- **Mock tests** for ML scenarios
- **Parametrized tests** for fixture validation
- **Explainer tests** for natural language output

### Running Tests

```bash
# Run all tests
make test

# Run specific test categories
uv run pytest tests/test_golden.py -v
uv run pytest tests/test_rules.py -v
uv run pytest tests/test_engine.py -v
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting: `make test && make lint`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- GitHub Issues: [Report bugs or request features](https://github.com/orca-team/orca-core/issues)
- Documentation: [Read the docs](https://orca-core.readthedocs.io)
