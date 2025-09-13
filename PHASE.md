# Orca Phase 2 — AI/LLM Integration (Weeks 4–8)

## Scope
This phase introduces AI/LLM capabilities to the Orca Core decision engine, focusing on machine learning scoring stubs, natural language explanations, and enhanced debugging tools.

## Goals
- **ML Scoring Integration**: Add risk scoring capabilities with feature extraction and model versioning
- **LLM Explanations**: Provide human-readable explanations in merchant and developer styles
- **Debug UI Enhancement**: Create comprehensive debugging interface with toggles and reporting
- **Azure Infrastructure**: Prepare scaffolding for cloud deployment with CI/CD pipelines
- **Validation Framework**: Compare Orca's transparency against opaque solutions like Stripe Radar

## Deliverables

### ML Scoring Stubs
- Risk score integration in decision contract
- Feature extraction from cart and context data
- Deterministic ML model stub with versioning
- CLI and UI toggles for ML scoring

### LLM Explanations
- Adapter for plain-English explanations
- Merchant and developer explanation styles
- Safe fallback mechanisms
- CLI integration with explanation flags

### Debug UI
- Streamlit-based debugging interface
- Interactive toggles for rail, channel, ML, and explanation styles
- Decision JSON export and clipboard functionality
- Case reporting and screenshot capture

### Azure Scaffolding
- Infrastructure as Code templates (Bicep/Terraform)
- GitHub Actions CI/CD workflows
- OIDC authentication setup
- Documentation for Azure deployment

### Validation & Testing
- Stripe Radar vs Orca comparison
- Comprehensive test coverage
- Pre-commit hooks and quality gates
- Sample fixtures and documentation

## Stage & Commit
- **Branch**: `phase-2-orca-ai-llm`
- **Status**: In Progress
- **Last Updated**: $(date)
- **Next Milestone**: ML Scoring Stubs Implementation
