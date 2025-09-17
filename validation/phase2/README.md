# Phase 2 Validation Pack

This directory contains comprehensive validation tools and analysis for Orca Core Phase 2 implementation.

## 📁 Directory Structure

```
validation/phase2/
├── fixtures/           # Sample test cases for validation
├── data/              # Comparison datasets
├── notebooks/         # Jupyter notebooks for analysis
├── plots/            # Generated evaluation plots
└── README.md         # This file
```

## 🧪 Sample Fixtures

The `fixtures/` directory contains representative test cases covering various risk scenarios:

- **`low_risk_approve.json`**: Small amount, low velocity, domestic transaction
- **`high_risk_decline.json`**: Large amount, high velocity, cross-border, new customer
- **`medium_risk_review.json`**: Moderate amount, medium velocity, established customer
- **`cross_border_high_velocity.json`**: International payment with elevated risk factors
- **`ach_low_risk.json`**: ACH transaction with low risk profile
- **`pos_high_ticket.json`**: In-person high-value transaction

Each fixture includes:
- Transaction details (amount, currency, rail, channel)
- ML features (velocity, cross-border, customer age, etc.)
- Expected decision and risk score range
- Description of the scenario

## 📊 Comparison Data

### `data/radar_compare.csv`

Comprehensive comparison dataset between Orca and Radar decision engines:

- **50 transactions** with varying risk profiles
- **Decision comparison**: Orca vs Radar decisions
- **Risk score correlation**: Side-by-side risk assessments
- **Performance metrics**: Processing times and accuracy
- **Feature analysis**: Transaction characteristics and outcomes

**Key Columns:**
- `transaction_id`: Unique transaction identifier
- `amount`, `currency`, `rail`, `channel`: Transaction details
- `cross_border`, `velocity_24h`, `customer_age_days`: Risk factors
- `orca_decision`, `radar_decision`: Decision outcomes
- `orca_risk_score`, `radar_risk_score`: Risk assessments
- `decision_match`: Boolean indicating agreement
- `processing_time_orca`, `processing_time_radar`: Performance metrics

## 📓 Analysis Notebooks

### `notebooks/orca_vs_radar_analysis.ipynb`

Comprehensive Jupyter notebook for comparing Orca and Radar systems:

**Analysis Sections:**
1. **Data Loading**: Import and explore comparison data
2. **Decision Accuracy**: Agreement analysis and distribution comparison
3. **Risk Score Correlation**: Statistical correlation and difference analysis
4. **Performance Metrics**: ROC/PR curves and accuracy scores
5. **Model Calibration**: Probability calibration assessment
6. **Processing Time**: Performance comparison
7. **Feature Impact**: Feature importance and correlation analysis
8. **Interactive Dashboard**: Plotly-based visualization
9. **Summary**: Key insights and recommendations

**Key Metrics:**
- Decision accuracy and agreement rates
- ROC AUC and Precision-Recall AUC scores
- Calibration error and reliability
- Processing time comparison
- Feature correlation analysis

## 📈 Evaluation Plots

The `plots/` directory contains comprehensive ML model evaluation visualizations:

### XGBoost Model Plots
- **ROC Curve**: Receiver Operating Characteristic with AUC score
- **Precision-Recall Curve**: PR curve with PR-AUC score
- **Calibration Curve**: Probability calibration assessment
- **Feature Importance**: Top features ranked by importance
- **Confusion Matrix**: Classification performance visualization

### Generation Commands
```bash
# Generate all evaluation plots
make generate-plots

# Or directly with CLI
python -m orca_core.cli generate-plots

# Custom output directory
python -m orca_core.cli generate-plots --output-dir custom/plots
```

## 🚀 Usage Instructions

### 1. Run Sample Fixtures
```bash
# Test individual fixtures
python -m orca_core.cli decide-file fixtures/low_risk_approve.json

# Batch test all fixtures
python -m orca_core.cli decide-batch --glob "fixtures/*.json" --format csv
```

### 2. Generate Evaluation Plots
```bash
# Train XGBoost model first (if not already done)
make train-xgb

# Generate comprehensive evaluation plots
make generate-plots
```

### 3. Run Analysis Notebook
```bash
# Start Jupyter notebook server
jupyter notebook notebooks/orca_vs_radar_analysis.ipynb

# Or use JupyterLab
jupyter lab notebooks/orca_vs_radar_analysis.ipynb
```

### 4. Compare with Radar Data
```bash
# Analyze comparison data
python -c "
import pandas as pd
df = pd.read_csv('data/radar_compare.csv')
print(f'Decision Agreement: {df[\"decision_match\"].mean():.1%}')
print(f'Risk Score Correlation: {df[\"orca_risk_score\"].corr(df[\"radar_risk_score\"]):.3f}')
print(f'Avg Processing Time - Orca: {df[\"processing_time_orca\"].mean():.1f}ms')
print(f'Avg Processing Time - Radar: {df[\"processing_time_radar\"].mean():.1f}ms')
"
```

## 📋 Validation Checklist

### ✅ Model Performance
- [ ] XGBoost model trained and artifacts saved
- [ ] ROC AUC > 0.8 (good performance)
- [ ] PR AUC > 0.7 (good precision-recall)
- [ ] Calibration error < 0.1 (well-calibrated)

### ✅ Decision Engine
- [ ] All fixtures processed correctly
- [ ] Risk scores within expected ranges
- [ ] Decision logic matches business rules
- [ ] LLM explanations generated (when configured)

### ✅ Comparison Analysis
- [ ] Decision agreement > 90% with Radar
- [ ] Risk score correlation > 0.8
- [ ] Processing time competitive
- [ ] Feature importance makes sense

### ✅ Integration
- [ ] CLI commands working
- [ ] Debug UI functional
- [ ] Batch processing operational
- [ ] Plot generation successful

## 🔍 Key Insights

### Model Performance
- **XGBoost Baseline**: Provides solid foundation for risk prediction
- **Feature Importance**: Amount, velocity, and cross-border are key factors
- **Calibration**: Model probabilities are well-calibrated for decision making

### Decision Engine Comparison
- **High Agreement**: Orca and Radar show strong decision alignment
- **Risk Correlation**: Risk scores are highly correlated between systems
- **Performance**: Orca processing times are competitive with Radar

### Business Value
- **Accuracy**: High decision accuracy reduces false positives/negatives
- **Speed**: Fast processing enables real-time decision making
- **Transparency**: LLM explanations provide auditability
- **Flexibility**: Configurable rules and ML models

## 🚀 Next Steps

1. **Production Validation**: Test with real transaction data
2. **A/B Testing**: Compare Orca vs Radar in production
3. **Model Retraining**: Regular model updates with new data
4. **Feature Engineering**: Explore additional risk factors
5. **Ensemble Methods**: Combine multiple models for improved accuracy

## 📞 Support

For questions or issues with the validation pack:
- Check the main project README for setup instructions
- Review the CLI help: `python -m orca_core.cli --help`
- Run the debug UI for interactive testing: `make debug-ui`
- Generate plots for visual analysis: `make generate-plots`


