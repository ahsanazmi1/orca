# Phase 2: Explainability Architecture

This document describes the explainability architecture for Orca Core, including the AP2 decision flow, Azure setup, and configuration options.

## Architecture Overview

The Orca Core explainability system follows a multi-stage pipeline that transforms AP2 decision contracts into human-readable explanations through a combination of rule-based logic, machine learning, and large language models.

### AP2 Decision Flow Architecture

```mermaid
graph TD
    A[AP2 Decision Contract] --> B[Rules Engine]
    B --> C[Feature Extraction]
    C --> D{ML Mode}
    D -->|Stub| E[Deterministic ML Stub]
    D -->|XGBoost| F[XGBoost Model]
    E --> G[Risk Score]
    F --> H[Calibrator]
    H --> G
    G --> I[Decision Response]
    I --> J{Explain Mode}
    J -->|Template| K[Template Engine]
    J -->|LLM| L[Azure OpenAI]
    K --> M[Human Explanation]
    L --> N[Guardrails]
    N --> O[Sanitized Explanation]
    O --> M
    M --> P[AP2 Response with Explanation]
```

### AP2 → Feature Map → XGBoost → Calibration → Decision → NLG Flow

```mermaid
graph LR
    A[AP2 Contract] --> B[Feature Extraction]
    B --> C[Feature Map]
    C --> D[XGBoost Model]
    D --> E[Raw Risk Score]
    E --> F[Calibration]
    F --> G[Calibrated Score]
    G --> H[Threshold Policy]
    H --> I[Decision Result]
    I --> J[NLG Engine]
    J --> K[Human Explanation]

    subgraph "Feature Mapping"
        C1[intent.metadata.velocity_24h → velocity_24h]
        C2[cart.amount → amount]
        C3[payment.method → payment_method_risk]
        C4[intent.actor.metadata.loyalty_score → loyalty_score]
    end

    subgraph "Calibration & Thresholds"
        H1[approve >= 0.85]
        H2[review 0.65–0.85]
        H3[decline < 0.65]
    end
```

### Detailed Component Flow

1. **AP2 Input Processing**: AP2 decision contract is received and validated
2. **Rules Evaluation**: Business rules are applied to determine initial decision
3. **Feature Engineering**: AP2 fields are mapped to ML features using feature specification
4. **ML Prediction**: Either stub or XGBoost model generates risk score
5. **Calibration**: XGBoost scores are calibrated using Platt scaling for better probability estimates
6. **Threshold Policy**: Calibrated scores are compared against configurable thresholds
7. **Decision Synthesis**: Rules and ML results are combined into AP2 decision response
8. **Explanation Generation**: Human-readable explanations are created with AP2 field references
9. **Guardrail Validation**: LLM explanations are validated for AP2 field accuracy
10. **Response Assembly**: Final AP2 decision contract with explanation is packaged

### Component Details

#### 1. Rules Engine
- **Purpose**: Applies business logic rules to transaction data
- **Components**: ACH rules, card rules, velocity rules, high-risk rules, high-ticket rules
- **Output**: Rule-based decisions and metadata

#### 2. Feature Extraction
- **Purpose**: Transforms AP2 decision contract fields into ML-ready features
- **AP2 Field Mapping**:
  - `cart.amount` → `amount`: Transaction amount (Decimal)
  - `intent.metadata.velocity_24h` → `velocity_24h`: 24-hour transaction frequency
  - `intent.metadata.velocity_7d` → `velocity_7d`: 7-day transaction frequency
  - `cart.geo.country != intent.geo.country` → `cross_border`: International transaction flag
  - `cart.currency` → `currency`: Transaction currency
  - `payment.method` → `payment_method_risk`: Payment method risk score
  - `intent.actor.metadata.loyalty_score` → `loyalty_score`: Customer loyalty metric
  - `intent.actor.metadata.chargebacks_12m` → `chargebacks_12m`: 12-month chargeback count
  - `intent.actor.metadata.age_days` → `customer_age_days`: Account age in days
  - `intent.actor.metadata.time_since_last_purchase` → `time_since_last_purchase`: Days since last purchase

#### 3. Machine Learning Pipeline
- **Stub Mode**: Deterministic scoring based on business rules
- **XGBoost Mode**: Gradient boosting model with calibration
- **Calibration**: Platt scaling for probability calibration
- **Threshold Policy**: Configurable decision thresholds
  - **Approve**: `risk_score >= 0.85` (configurable)
  - **Review**: `0.65 <= risk_score < 0.85` (configurable)
  - **Decline**: `risk_score < 0.65` (configurable)

#### 4. Explanation Generation
- **Template Mode**: Pre-defined human-readable templates with AP2 field references
- **LLM Mode**: Azure OpenAI-generated explanations with AP2 field validation guardrails
- **Key Signals Mapping**: Each key signal must point to a valid AP2 JSONPath
  - Example: `"ap2_path": "intent.metadata.velocity_24h"`
  - Validation: Ensures all referenced fields exist in AP2 contract
  - Guardrails: Prevents hallucination of non-existent AP2 fields

## Azure Setup

### Prerequisites
- Azure subscription with OpenAI service access
- Azure CLI installed and configured
- Orca Core project dependencies installed

### Configuration Steps

#### Step 1: Run the Azure Configuration Script
```bash
make configure-azure-openai
```

This interactive script will prompt you for:
- Azure OpenAI endpoint URL
- API key
- Deployment name
- Azure subscription details
- Resource group information

#### Step 2: Manual Environment Variable Setup (Alternative)
If you prefer to set environment variables manually:

```bash
# Copy the example configuration
cp .env.example .env.local

# Edit .env.local with your actual values
# The file includes all Phase 2 configuration options

# Or set environment variables directly:
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_API_KEY="your-api-key"
export AZURE_OPENAI_DEPLOYMENT="your-deployment-name"
export AZURE_OPENAI_API_VERSION="2024-02-15-preview"

# Optional: Customize model parameters
export AZURE_OPENAI_TEMPERATURE="0.7"
export AZURE_OPENAI_MAX_TOKENS="500"
```

#### Step 3: Verify Configuration
```bash
# Check configuration status
python -m orca_core.cli config

# Test Azure OpenAI connection
make test-llm
```

#### Step 4: Test the Setup
```bash
# Test with a simple decision
python -m orca_core.cli decide '{"cart_total": 100.0}' --mode ai --explain yes

# Test batch processing
python -m orca_core.cli decide-batch --glob "fixtures/requests/*.json" --mode ai
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI service endpoint | Yes |
| `AZURE_OPENAI_API_KEY` | API key for authentication | Yes |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name | Yes |
| `AZURE_OPENAI_API_VERSION` | API version to use | Yes |
| `AZURE_OPENAI_TEMPERATURE` | Model temperature (default: 0.7) | No |
| `AZURE_OPENAI_MAX_TOKENS` | Maximum tokens per response (default: 500) | No |

## Configuration Options

### Toggle Between Stub and XGBoost Models

The Orca Core system supports two ML modes: a fast deterministic stub model and a sophisticated XGBoost model. The choice depends on your performance and accuracy requirements.

#### Method 1: Environment Variables
```bash
# Use XGBoost model (recommended for production)
export ORCA_USE_XGB=true

# Use stub model (recommended for development/testing)
export ORCA_USE_XGB=false
```

#### Method 2: CLI Override
```bash
# Use XGBoost for a single decision
python -m orca_core.cli decide '{"cart_total": 100.0}' --ml xgb

# Use stub for a single decision
python -m orca_core.cli decide '{"cart_total": 100.0}' --ml stub
```

#### Method 3: Configuration File
Create a `.env` file in the project root:
```env
ORCA_USE_XGB=true
ORCA_MODE=RULES_PLUS_AI
ORCA_EXPLAIN_ENABLED=true
```

#### Method 4: Makefile Commands
```bash
# Test with XGBoost model
make test-xgb

# Test with stub model
make test-llm-stub

# Test with LLM explanations
make test-llm
```

### Model Comparison

| Aspect | Stub Model | XGBoost Model |
|--------|------------|---------------|
| **Speed** | ~1ms | ~10-50ms |
| **Accuracy** | Deterministic | High accuracy |
| **Memory** | Minimal | ~50MB |
| **Dependencies** | None | XGBoost, scikit-learn |
| **Use Case** | Development, testing | Production, compliance |
| **Explainability** | Rule-based | Feature importance + LLM |

### Stub Model Logic

The stub model uses deterministic business rules:

```python
# Example stub scoring logic
def predict_risk_stub(features):
    base_score = 0.35

    # Amount-based scoring
    if features.get('amount', 0) > 1000:
        base_score += 0.2

    # Velocity-based scoring
    if features.get('velocity_24h', 0) > 5:
        base_score += 0.1

    # Cross-border penalty
    if features.get('cross_border', 0) == 1:
        base_score += 0.1

    # Clamp to [0, 1] range
    return min(max(base_score, 0.0), 1.0)
```

### XGBoost Model Features

The XGBoost model provides:

- **Gradient Boosting**: Ensemble of decision trees
- **Calibration**: Platt scaling for probability calibration
- **Feature Importance**: Identifies key decision factors
- **Model Persistence**: Trained models saved to disk
- **Versioning**: Model metadata and version tracking

### Decision Modes

| Mode | Description | ML Model | Explanations |
|------|-------------|----------|--------------|
| `RULES_ONLY` | Rule-based decisions only | Stub | Template |
| `RULES_PLUS_AI` | Rules + AI explanations | XGBoost | LLM + Guardrails |

### Explanation Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `template` | Pre-defined templates | Fast, consistent explanations |
| `llm` | AI-generated explanations | Detailed, contextual explanations |

## Usage Examples

### Basic Decision with Stub Model
```bash
python -m orca_core.cli decide '{"cart_total": 100.0, "currency": "USD"}'
```

### Decision with XGBoost and LLM Explanations
```bash
python -m orca_core.cli decide '{"cart_total": 1000.0, "velocity_24h": 5}' --ml xgb --mode ai --explain yes
```

### Batch Processing
```bash
python -m orca_core.cli decide-batch --glob "fixtures/requests/*.json" --ml xgb --format table
```

### File-based Decision
```bash
python -m orca_core.cli decide-file fixtures/requests/high_risk_decline.json --ml xgb
```

## Model Training

### Train XGBoost Model
```bash
python -m orca_core.cli train-xgb --samples 10000 --model-dir models/
```

### Generate Model Evaluation Plots
```bash
python -m orca_core.cli generate-plots
```

## Debug and Monitoring

### Debug UI
```bash
python -m orca_core.cli debug-ui --port 8501
```

### Model Information
```bash
python -m orca_core.cli model-info
```

### Configuration Status
```bash
python -m orca_core.cli config
```

## Key Signals Mapping Rules

The explainability system enforces strict mapping rules to ensure all explanations reference valid AP2 fields.

### AP2 Field Reference Validation

Each key signal in explanations must include a valid `ap2_path` that points to an actual field in the AP2 decision contract:

```json
{
  "key_signals": [
    {
      "feature_name": "velocity_24h",
      "ap2_path": "intent.metadata.velocity_24h",
      "value": 8.0,
      "importance": 0.85,
      "contribution": 0.15
    },
    {
      "feature_name": "amount",
      "ap2_path": "cart.amount",
      "value": 2500.0,
      "importance": 0.75,
      "contribution": 0.12
    }
  ]
}
```

### Valid AP2 Paths

| AP2 Path | Description | Example Value |
|----------|-------------|---------------|
| `intent.metadata.velocity_24h` | 24-hour transaction velocity | 8.0 |
| `intent.metadata.velocity_7d` | 7-day transaction velocity | 25.0 |
| `cart.amount` | Transaction amount | "2500.00" |
| `cart.currency` | Transaction currency | "USD" |
| `payment.method` | Payment method | "card" |
| `payment.modality` | Payment timing | "immediate" |
| `intent.actor.metadata.loyalty_score` | Customer loyalty | 0.2 |
| `intent.actor.metadata.age_days` | Account age | 30.0 |
| `intent.actor.metadata.chargebacks_12m` | 12-month chargebacks | 2.0 |
| `intent.channel` | Transaction channel | "web" |
| `intent.geo.country` | Customer country | "US" |
| `cart.geo.country` | Merchant country | "US" |

### Invalid AP2 Paths (Will Cause Validation Errors)

| Invalid Path | Reason |
|--------------|--------|
| `user.profile` | Non-existent field |
| `transaction.metadata` | Non-existent field |
| `system.config` | Non-existent field |
| `payment.card_number` | Sensitive data not in AP2 |
| `customer.email` | PII not in AP2 |

### Guardrail Validation Process

1. **Path Extraction**: Extract all `ap2_path` values from key signals
2. **Schema Validation**: Check if paths exist in AP2 contract schema
3. **Field Existence**: Verify fields exist in actual AP2 contract instance
4. **Type Validation**: Ensure referenced values match expected types
5. **Hallucination Detection**: Flag explanations with invalid field references

## Guardrails

The LLM explanation system includes comprehensive guardrails to ensure safe, accurate, and compliant explanations.

### Guardrail Components

#### 1. JSON Schema Validation
- Ensures responses follow the expected structure
- Validates required fields are present
- Checks data types and formats

#### 2. Hallucination Detection
- Identifies potentially false or fabricated information
- Uses confidence scoring to detect uncertainty
- Flags responses that may contain inaccurate details

#### 3. Content Validation
- **PII Detection**: Identifies personally identifiable information
- **Legal Advice**: Detects attempts to provide legal guidance
- **Guarantees**: Identifies promises or guarantees that shouldn't be made
- **Forbidden Patterns**: Blocks specific problematic phrases

#### 4. Uncertainty Detection
- Identifies when the model expresses uncertainty
- Flags responses with low confidence scores
- Ensures explanations are definitive when required

#### 5. Sanitization
- Removes or replaces problematic content
- Maintains explanation quality while ensuring safety
- Provides fallback explanations when needed

### Guardrail Configuration

```python
# Example guardrail settings
GUARDRAIL_CONFIG = {
    "max_hallucination_score": 0.3,
    "forbidden_patterns": [
        "guarantee", "promise", "legal advice",
        "definitely", "certainly", "always"
    ],
    "uncertainty_threshold": 0.7,
    "pii_patterns": [
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"  # Credit card
    ],
    "max_response_length": 500,
    "min_confidence_score": 0.8
}
```

### Guardrail Response Types

| Response Type | Description | Action |
|---------------|-------------|---------|
| `VALID` | All checks passed | Use LLM explanation |
| `HALLUCINATION` | Potential false information | Use template fallback |
| `CONTENT_VIOLATION` | Forbidden content detected | Sanitize and use |
| `UNCERTAINTY` | Model expresses uncertainty | Use template fallback |
| `SCHEMA_ERROR` | Invalid JSON format | Use template fallback |

### Customizing Guardrails

You can customize guardrail behavior by setting environment variables:

```bash
# Adjust hallucination sensitivity
export ORCA_GUARDRAIL_HALLUCINATION_THRESHOLD=0.2

# Add custom forbidden patterns
export ORCA_GUARDRAIL_FORBIDDEN_PATTERNS="custom_pattern1,custom_pattern2"

# Set uncertainty threshold
export ORCA_GUARDRAIL_UNCERTAINTY_THRESHOLD=0.8
```

## Performance Considerations

### Model Selection Guidelines

| Scenario | Recommended Model | Reason |
|----------|------------------|---------|
| Development/Testing | Stub | Fast, deterministic |
| Production (Low Volume) | XGBoost | Better accuracy |
| Production (High Volume) | Stub | Performance |
| Compliance/Audit | XGBoost + LLM | Detailed explanations |

### Caching
- XGBoost models are cached after first load
- LLM responses can be cached for identical requests
- Feature extraction results are cached per session

## Troubleshooting

### Common Issues

1. **Azure OpenAI Connection Failed**
   ```bash
   # Check configuration
   python -m orca_core.cli config

   # Verify API key
   curl -H "api-key: $AZURE_OPENAI_API_KEY" "$AZURE_OPENAI_ENDPOINT/openai/deployments/$AZURE_OPENAI_DEPLOYMENT/chat/completions?api-version=$AZURE_OPENAI_API_VERSION"
   ```

2. **Model Loading Errors**
   ```bash
   # Check model files
   ls -la models/

   # Retrain model
   python -m orca_core.cli train-xgb
   ```

3. **Guardrail Failures**
   - Check guardrail configuration
   - Review explanation content for violations
   - Adjust thresholds if needed

### Logging
Enable debug logging:
```bash
export ORCA_LOG_LEVEL=DEBUG
python -m orca_core.cli decide '{"cart_total": 100.0}'
```

## Security Considerations

1. **API Key Management**: Store API keys securely, never commit to version control
2. **Data Privacy**: Ensure transaction data is handled according to privacy requirements
3. **Audit Trail**: Log all decisions and explanations for compliance
4. **Access Control**: Implement proper authentication and authorization

## Quick Reference

### Essential Commands

```bash
# Setup
make configure-azure-openai    # Configure Azure OpenAI
make test-config              # Verify configuration

# Model Training
make train-xgb               # Train XGBoost model
make model-info              # Show model information
make generate-plots          # Generate evaluation plots

# Testing
make test-xgb                # Test with XGBoost
make test-llm                # Test with LLM explanations
make test-llm-stub           # Test with stub model

# Debugging
make debug-ui                # Launch debug UI
python -m orca_core.cli config  # Check configuration
```

### Environment Variables Quick Reference

| Variable | Purpose | Default |
|----------|---------|---------|
| `ORCA_USE_XGB` | Enable XGBoost model | `false` |
| `ORCA_MODE` | Decision mode | `RULES_ONLY` |
| `ORCA_EXPLAIN_ENABLED` | Enable explanations | `false` |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint | Required |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | Required |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name | Required |

### Common Use Cases

#### Development/Testing
```bash
# Fast testing with stub model
export ORCA_USE_XGB=false
python -m orca_core.cli decide '{"cart_total": 100.0}'
```

#### Production with AI Explanations
```bash
# Full AI pipeline
export ORCA_USE_XGB=true
export ORCA_MODE=RULES_PLUS_AI
python -m orca_core.cli decide '{"cart_total": 1000.0}' --explain yes
```

#### Batch Processing
```bash
# Process multiple requests
python -m orca_core.cli decide-batch --glob "data/*.json" --ml xgb --format csv
```

## Future Enhancements

1. **Multi-model Support**: Support for additional ML models
2. **Custom Templates**: User-defined explanation templates
3. **A/B Testing**: Compare explanation effectiveness
4. **Real-time Monitoring**: Live performance and accuracy metrics
5. **Federated Learning**: Distributed model training
6. **Custom Guardrails**: User-defined safety rules
7. **Explanation Analytics**: Track explanation quality and usage
8. **Multi-language Support**: Explanations in multiple languages
