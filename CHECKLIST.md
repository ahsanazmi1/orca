# Orca Development Checklist

## Phase 1 — Core Decision Engine ✅
- [x] Basic decision engine implementation
- [x] Rule-based scoring system
- [x] CLI interface
- [x] Streamlit demo app
- [x] Test coverage and validation
- [x] Documentation and examples

## Phase 2 — AI/LLM Integration (Weeks 4–8)

### ML Scoring Stubs
- [ ] `risk_score` added to decision contract with `meta.model_version` + `meta.features_used`
- [ ] `predict_risk(features)` stub implemented with deterministic output
- [ ] Feature extractor created for cart + context
- [ ] CLI + UI toggle `--use-ml` surfaces `risk_score`
- [ ] README updated with ML stub usage

### LLM Explanations
- [ ] Adapter added for plain-English explanations (merchant/dev styles)
- [ ] CLI extended with `--explain merchant|developer`
- [ ] Safe fallback when no provider configured

### Debug UI
- [ ] Streamlit Debug App (`apps/debug/app_streamlit.py`) created
- [ ] Copy/Download decision.json supported
- [ ] Debug reports saved
- [ ] Screenshots saved under `/docs/ui/phase2/`

### Azure Scaffolding (Local Prep Only)
- [ ] `/infra/azure/` scaffolding added (AKS, ACR, Key Vault, RG)
- [ ] GitHub Actions CI workflow added
- [ ] GitHub Actions OIDC workflow scaffolded
- [ ] Infra docs created

### Validation — Stripe Radar vs Orca
- [ ] Side-by-side comparison written
- [ ] 3 sample cases captured (approve, decline, borderline)

### Tests & Quality
- [ ] Unit tests cover ML stubs, toggle, LLM adapter
- [ ] Pre-commit + CI passes clean

---

## Phase 3 — Production Deployment (Future)
- [ ] Production Azure deployment
- [ ] Monitoring and alerting
- [ ] Performance optimization
- [ ] Security hardening
- [ ] Load testing and scaling

## Phase 4 — Advanced Features (Future)
- [ ] Real ML model integration
- [ ] Advanced analytics dashboard
- [ ] Multi-tenant support
- [ ] API rate limiting and quotas
- [ ] Advanced rule configuration UI
