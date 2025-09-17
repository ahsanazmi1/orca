"""Script to generate golden decision JSONs with ML model information."""

import json
import sys
from pathlib import Path

sys.path.append(".")

from src.orca.core.decision_contract import AP2DecisionContract
from src.orca.core.rules_engine import evaluate_ap2_rules
from src.orca.ml.predict_risk import load_model_version, predict_risk


def generate_golden_decision(ap2_file: Path, output_file: Path, enable_shap: bool = False) -> None:
    """Generate golden decision JSON for an AP2 sample file."""
    print(f"Processing {ap2_file.name}...")

    # Load AP2 contract
    with open(ap2_file) as f:
        ap2_data = json.load(f)

    # Create a minimal decision outcome for the contract
    from uuid import uuid4

    from src.orca.core.decision_contract import DecisionMeta, DecisionOutcome

    decision_meta = DecisionMeta(model="rules_only", trace_id=str(uuid4()), version="0.1.0")

    decision_outcome = DecisionOutcome(
        result="APPROVE", risk_score=0.0, reasons=[], actions=[], meta=decision_meta
    )

    # Add decision to AP2 data
    ap2_data["decision"] = decision_outcome.model_dump()

    ap2_contract = AP2DecisionContract(**ap2_data)

    # Evaluate with rules engine
    decision_outcome = evaluate_ap2_rules(ap2_contract)

    # Get ML prediction if model is available
    ml_result = None
    try:
        # Load model if available
        if load_model_version("1.0.0"):
            # Extract features for ML prediction
            features = {
                "amount": float(ap2_contract.cart.amount),
                "velocity_24h": 1.0,  # Default values for missing features
                "velocity_7d": 3.0,
                "cross_border": 0.0,
                "location_mismatch": 0.0,
                "payment_method_risk": 0.3,
                "chargebacks_12m": 0.0,
                "customer_age_days": 365.0,
                "loyalty_score": 0.5,
                "time_since_last_purchase": 7.0,
            }

            # Predict with ML
            if enable_shap:
                from src.orca.ml.predict_risk import predict_with_shap

                ml_result = predict_with_shap(features)
            else:
                ml_result = predict_risk(features)
    except Exception as e:
        print(f"ML prediction failed for {ap2_file.name}: {e}")
        ml_result = None

    # Create golden decision structure
    golden_decision = {
        "ap2_version": ap2_contract.ap2_version,
        "intent": ap2_contract.intent.model_dump(),
        "cart": ap2_contract.cart.model_dump(),
        "payment": ap2_contract.payment.model_dump(),
        "decision": {
            "result": decision_outcome.result,
            "risk_score": decision_outcome.risk_score,
            "reasons": [reason.model_dump() for reason in decision_outcome.reasons],
            "actions": [action.model_dump() for action in decision_outcome.actions],
            "meta": {
                "model": "xgboost" if ml_result else "rules_only",
                "model_version": ml_result.get("model_meta", {}).get("model_version", "1.0.0")
                if ml_result
                else "1.0.0",
                "model_sha256": ml_result.get("model_meta", {}).get("model_sha256", "abc123def456")
                if ml_result
                else "rules-only",
                "model_trained_on": ml_result.get("model_meta", {}).get("trained_on", "2024-01-01")
                if ml_result
                else "deterministic",
                "trace_id": decision_outcome.meta.trace_id,
                "processing_time_ms": decision_outcome.meta.processing_time_ms,
                "version": decision_outcome.meta.version,
                "rules_evaluated": [],
                "feature_snapshot": {},
            },
        },
        "signing": {"vc_proof": None, "receipt_hash": None},
    }

    # Add ML-specific information if available
    if ml_result:
        golden_decision["ml_prediction"] = {
            "risk_score": ml_result["risk_score"],
            "key_signals": ml_result["key_signals"],
            "model_meta": ml_result["model_meta"],
        }

        # Add SHAP values if enabled
        if enable_shap and ml_result.get("shap_values"):
            golden_decision["ml_prediction"]["shap_values"] = ml_result["shap_values"]

    # Write golden decision
    with open(output_file, "w") as f:
        json.dump(golden_decision, f, indent=2, default=str)

    print(f"✅ Generated {output_file.name}")


def main():
    """Generate golden decisions for all AP2 samples."""
    samples_dir = Path("samples/ap2")
    golden_dir = Path("samples/golden")
    golden_dir.mkdir(exist_ok=True)

    # Process each AP2 sample
    for ap2_file in samples_dir.glob("*.json"):
        golden_file = golden_dir / f"{ap2_file.stem}_golden.json"

        # Enable SHAP for the high amount sample
        enable_shap = "high_amount" in ap2_file.name

        generate_golden_decision(ap2_file, golden_file, enable_shap)

    print(f"\n🎉 Generated {len(list(samples_dir.glob('*.json')))} golden decision files!")


if __name__ == "__main__":
    main()
