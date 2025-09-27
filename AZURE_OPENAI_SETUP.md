# Azure OpenAI Setup for Orca Phase 3 Negotiation

This document explains how to configure Azure OpenAI integration for Orca's Phase 3 negotiation features, including LLM-powered explanations for rail selection.

## Prerequisites

1. **Azure Subscription**: You need an active Azure subscription
2. **Azure OpenAI Resource**: Create an Azure OpenAI resource in your Azure portal
3. **Deployed Model**: Deploy a GPT model (GPT-4 or GPT-3.5-turbo) in your Azure OpenAI resource

## Environment Variables

Set the following environment variables to enable LLM explanations:

```bash
# Azure OpenAI Configuration
export AZURE_OPENAI_API_KEY="your-api-key-here"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_API_VERSION="2024-02-15-preview"
export AZURE_OPENAI_DEPLOYMENT_NAME="your-deployment-name"

# Optional: Enable XGBoost model (for production risk scoring)
export ORCA_USE_XGB="true"

# Optional: Set deterministic seed for consistent results
export ORCA_DETERMINISTIC_SEED="42"
```

## Configuration Methods

### Method 1: Interactive Configuration Script

Run the provided configuration script:

```bash
cd agents/orca
python scripts/configure_azure_openai.py
```

This script will:
- Collect your Azure OpenAI configuration interactively
- Validate the endpoint and API key
- Write configuration to the appropriate files
- Test the connection

### Method 2: Manual Environment Setup

1. **Get your Azure OpenAI credentials**:
   - Navigate to your Azure OpenAI resource in the Azure portal
   - Go to "Keys and Endpoint"
   - Copy your API key and endpoint URL

2. **Set environment variables**:
   ```bash
   export AZURE_OPENAI_API_KEY="your-api-key"
   export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
   export AZURE_OPENAI_DEPLOYMENT_NAME="your-deployment-name"
   ```

3. **Verify configuration**:
   ```bash
   python -c "
   from src.orca_core.llm.explain import is_llm_configured
   print('LLM configured:', is_llm_configured())
   "
   ```

## Features Enabled with Azure OpenAI

When properly configured, the following Phase 3 features are enhanced:

### 1. **Enhanced Rail Selection Explanations**
- **Human-readable explanations** for why specific rails are chosen
- **Detailed reasoning** about cost, speed, and risk trade-offs
- **Risk mitigation explanations** for declined rails

### 2. **Structured JSON Explanations**
The LLM generates explanations with the following structure:
```json
{
  "reason": "ACH selected for cost efficiency",
  "key_signals": {
    "cost_signals": ["low processing cost"],
    "speed_signals": ["fast settlement"],
    "risk_signals": ["low ML risk score"],
    "ml_risk_score": 0.23,
    "composite_score": 0.78
  },
  "mitigation": {
    "declined_rails": [
      {
        "rail": "Credit",
        "reason": "Composite score 0.65 vs 0.78",
        "primary_factors": ["high processing cost", "chargeback risk"]
      }
    ],
    "risk_mitigation": "ML risk score 0.23 within acceptable threshold"
  },
  "confidence": {
    "score_difference": 0.13,
    "decision_strength": "high",
    "alternative_count": 2
  }
}
```

### 3. **MCP Integration**
The `negotiateCheckout` MCP verb returns enhanced explanations:
- **Chosen rail** with detailed rationale
- **Candidate scores** for all evaluated rails
- **Structured explanation** with JSON metadata

## Testing LLM Integration

### 1. **Test Basic Configuration**
```bash
cd agents/orca
python -c "
from src.orca_core.llm.explain import is_llm_configured, get_llm_explainer
print('LLM configured:', is_llm_configured())
explainer = get_llm_explainer()
print('Configuration status:', explainer.get_configuration_status())
"
```

### 2. **Test Negotiation with LLM**
```bash
python -c "
from src.orca_core.models import NegotiationRequest
from src.orca_core.engine import determine_optimal_rail

request = NegotiationRequest(
    cart_total=1000.0,
    features={'transaction_amount': 1000.0, 'merchant_risk_score': 0.3},
    context={'deterministic_seed': 42},
    available_rails=['ACH', 'Credit']
)

response = determine_optimal_rail(request)
print('Selected rail:', response.optimal_rail)
print('Explanation length:', len(response.explanation))
print('Has structured JSON:', 'Structured Analysis:' in response.explanation)
"
```

### 3. **Run Comprehensive Tests**
```bash
# Run all negotiation tests (includes LLM tests)
pytest tests/test_negotiation.py::TestLLMExplanationJSON -v

# Run specific LLM integration tests
pytest tests/test_negotiation.py::TestLLMExplanationJSON::test_llm_explanation_json_structure -v
```

## Fallback Behavior

If Azure OpenAI is not configured or unavailable:

1. **Deterministic explanations** are used as fallback
2. **All negotiation logic** continues to work normally
3. **MCP integration** remains functional
4. **Tests continue to pass** with fallback explanations

The system gracefully degrades without Azure OpenAI, ensuring reliability in all environments.

## Troubleshooting

### Common Issues

1. **"LLM explanation service not configured"**
   - Check that all environment variables are set
   - Verify API key is valid and has proper permissions
   - Ensure deployment name matches your Azure OpenAI deployment

2. **"LLM explanation failed, using fallback"**
   - Check Azure OpenAI service status
   - Verify quota limits haven't been exceeded
   - Review API version compatibility

3. **Connection timeout errors**
   - Verify endpoint URL is correct
   - Check network connectivity to Azure
   - Ensure firewall allows Azure OpenAI traffic

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
export ORCA_LOG_LEVEL="DEBUG"
python your_script.py
```

## Security Considerations

1. **Never commit API keys** to version control
2. **Use environment variables** or secure key management
3. **Rotate API keys** regularly
4. **Monitor usage** to prevent unexpected charges
5. **Set appropriate quotas** in Azure OpenAI

## Cost Management

- **Monitor token usage** through Azure OpenAI metrics
- **Set spending limits** in Azure portal
- **Use appropriate model sizes** (GPT-3.5-turbo is more cost-effective than GPT-4)
- **Implement rate limiting** for production deployments

## Support

For issues with:
- **Azure OpenAI setup**: Check Azure documentation
- **Orca integration**: Review test outputs and logs
- **Configuration problems**: Run the interactive configuration script
