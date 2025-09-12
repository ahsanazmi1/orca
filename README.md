# Orca Core Decision Engine

A production-ready decision engine for e-commerce applications, built with Python and designed for high-performance rule evaluation with ML integration.

## Features

- **Fast Decision Making**: Evaluate complex business rules in milliseconds
- **ML Integration**: Machine learning risk prediction with configurable thresholds
- **Modular Rules System**: Extensible rule registry with easy rule addition
- **Type Safety**: Built with Pydantic for robust data validation
- **CLI Interface**: Command-line tool for quick decision evaluation
- **Streamlit Demo**: Interactive web interface with ML toggle
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
# Evaluate a decision with high cart total
uv run python -m orca_core.cli decide '{"cart_total": 750.0, "currency": "USD", "features": {"velocity_24h": 4.0}}'

# Example output
{"actions":["ROUTE_TO_REVIEW","ROUTE_TO_REVIEW"],"decision":"REVIEW","meta":{"risk_score":0.15,"rules_evaluated":["HIGH_TICKET","VELOCITY"]},"reasons":["HIGH_TICKET: Cart total $750.00 exceeds $500.00 threshold","VELOCITY_FLAG: 24h velocity 4.0 exceeds 3.0 threshold"]}

# Evaluate a low-risk decision
uv run python -m orca_core.cli decide '{"cart_total": 250.0, "currency": "USD", "features": {"velocity_24h": 1.0}}'

# Example output
{"actions":["Process payment","Send confirmation"],"decision":"APPROVE","meta":{"approved_amount":250.0,"risk_score":0.15,"rules_evaluated":[]},"reasons":["Cart total $250.00 within approved threshold"]}

# Get plain-English explanation
uv run python -m orca_core.cli explain '{"cart_total": 750, "features": {"velocity_24h": 4}}'

# Example output
The cart total was unusually high, so the transaction was flagged for review. This customer made multiple purchases in a short time, which triggered a velocity check. Final decision: REVIEW.
```

#### Python API

```python
from orca_core import DecisionRequest, evaluate_rules

# Create a request
request = DecisionRequest(
    cart_total=750.0,
    currency="USD",
    features={"velocity_24h": 4.0, "customer_age": 30},
    context={"channel": "ecom", "user_id": "12345"}
)

# Evaluate decision
response = evaluate_rules(request)
print(f"Decision: {response.decision}")
print(f"Risk Score: {response.meta['risk_score']}")
print(f"Reasons: {response.reasons}")
```

#### Streamlit Demo

```bash
# Launch interactive demo
make demo
```

The demo includes:
- **ML Toggle**: Switch between "Rules only" and "Rules + ML" modes
- **Risk Score Display**: Color-coded risk metrics (🟢 Low, 🟡 Medium, 🔴 High)
- **Two-column Layout**: Input controls on left, JSON results on right
- **Real-time Updates**: Instant decision evaluation as you change inputs
- **Plain-English Explanations**: Toggle between JSON output and human-readable explanations

#### Week 3 — Explanation Demo

```bash
# Launch human-readable explanation demo
streamlit run apps/explain/app_streamlit.py
```

The explanation demo includes:
- **File Upload**: Upload transaction JSON files for analysis
- **Human Explanations**: Clear, non-technical explanations of decisions
- **Reason Mapping**: See how machine-readable reasons translate to human language
- **Example Files**: Pre-built examples for Card/ACH approve/decline scenarios
- **Copy/Download**: Copy explanations or download decision JSON files

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
