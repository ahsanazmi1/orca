# Changelog

All notable changes to the Orca Core Decision Engine will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **AP2 Contract Support**: AP2-compliant decision contracts with structured mandates
- **Real ML Model System**: XGBoost model with calibration, SHAP support, and feature drift guard
- **Model Versioning**: ML model versioning with semantic versioning and artifact management
- **Decision Signing**: Verifiable credential proofs and receipt hashing for audit trails
- **Legacy Adapter**: Backward compatibility adapter for legacy contract migration
- **Feature Mapping**: AP2 field path mapping for ML features and explanations
- **Content Type Headers**: AP2 content type (`application/vnd.ocn.ap2+json; version=1`) for REST APIs
- **Migration Guide**: Comprehensive migration documentation and best practices
- **Round-trip Tests**: Legacy ↔ AP2 conversion tests preserving semantics
- **ML risk stub for Azure ML integration**
- **LLM explanations using Azure OpenAI**
- **Debug UI for decision analysis and debugging**
- **Azure scaffolding for cloud-native deployment**
- **Feature flags for RULES_ONLY and RULES_PLUS_AI modes**
- **Environment variable configuration for Azure services**
- **Enhanced ML risk assessment capabilities**
- **Advanced feature engineering pipeline**

### Changed
- Enhanced decision engine with AI/LLM explainability
- Improved risk assessment with real-time ML model integration
- Extended API with Azure service integration points

### Security
- Added secure configuration management for Azure API keys
- Implemented fallback behavior for AI service unavailability

## [1.0.0] - 2025-01-15

### Added
- Core decision engine with rule-based evaluation
- ML integration hooks with configurable risk prediction
- FastAPI web service with health check and decision endpoints
- CLI interface for command-line decision evaluation
- Streamlit demo with interactive rail/channel toggles
- Human-readable explanation system
- Comprehensive test suite with 90+ tests
- Modular rules system with extensible registry
- Pydantic models for type-safe data validation
- Performance benchmarks with sub-millisecond evaluation
- Development tooling with Makefile targets
- CI/CD pipeline with automated testing and linting

### Features
- **HighTicketRule**: Cart total > $500 → REVIEW
- **VelocityRule**: 24h velocity > 3 → REVIEW
- **HighRiskRule**: ML risk score > 0.80 → DECLINE
- **LoyaltyBoost**: Customer loyalty tier approval boost
- **ACH Limit**: ACH transaction limit enforcement
- **Location Mismatch**: IP/billing country mismatch detection

### Technical
- Python 3.11+ support with uv package management
- Pydantic v2 for data validation and serialization
- FastAPI for high-performance web API
- Streamlit for interactive demos
- pytest for comprehensive testing
- ruff and black for code formatting and linting
- mypy for static type checking
