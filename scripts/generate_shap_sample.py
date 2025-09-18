"""Script to generate a SHAP-enabled sample with top-5 contributions."""

import json
import os
from pathlib import Path

# Set environment variable for SHAP
os.environ["ORCA_ENABLE_SHAP"] = "true"

import sys

sys.path.append(".")

from src.orca.ml.predict_risk import predict_with_shap


def generate_shap_sample():
    """Generate a SHAP-enabled sample with realistic features."""
    print("🔍 Generating SHAP-enabled sample...")

    # Create realistic features for a high-risk scenario
    features = {
        "amount": 1500.0,  # High amount
        "velocity_24h": 4.0,  # High velocity
        "velocity_7d": 12.0,  # High weekly velocity
        "cross_border": 1.0,  # Cross-border transaction
        "location_mismatch": 1.0,  # Location mismatch
        "payment_method_risk": 0.7,  # High payment method risk
        "chargebacks_12m": 3.0,  # Multiple chargebacks
        "customer_age_days": 30.0,  # New customer
        "loyalty_score": 0.1,  # Low loyalty
        "time_since_last_purchase": 0.1,  # Very recent purchase
    }

    # Predict with SHAP
    result = predict_with_shap(features)

    # Create SHAP sample structure
    shap_sample = {
        "scenario": "high_risk_complex",
        "description": "High-risk transaction with multiple risk factors for SHAP analysis",
        "features": features,
        "ml_prediction": {
            "risk_score": result["risk_score"],
            "model_type": result["model_type"],
            "version": result["version"],
            "key_signals": result["key_signals"][:5],  # Top 5 signals
            "model_meta": result["model_meta"],
        },
    }

    # Add SHAP values if available
    if result.get("shap_values"):
        shap_values = result["shap_values"]
        shap_sample["shap_analysis"] = {
            "base_value": shap_values.get("base_value", 0.0),
            "feature_contributions": [],
        }

        # Get top 5 SHAP contributions
        shap_contributions = []
        feature_names = shap_values.get("feature_names", [])
        shap_vals = shap_values.get("shap_values", [])

        for feature_name, value in zip(feature_names, shap_vals, strict=True):
            shap_contributions.append(
                {
                    "feature_name": feature_name,
                    "feature_value": features.get(feature_name, 0.0),
                    "shap_value": value,
                    "ap2_path": f"feature.{feature_name}",  # Simplified AP2 path
                }
            )

        # Sort by absolute SHAP value and take top 5
        shap_contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        shap_sample["shap_analysis"]["feature_contributions"] = shap_contributions[:5]

        print(f"✅ Generated SHAP sample with {len(shap_contributions[:5])} top contributions")
        print(f"📊 Risk Score: {result['risk_score']:.3f}")
        print(f"📊 Base Value: {shap_values.get('base_value', 0.0):.3f}")

        # Print top contributions
        print("\n🔍 Top 5 SHAP Contributions:")
        for i, contrib in enumerate(shap_contributions[:5], 1):
            print(
                f"  {i}. {contrib['feature_name']}: {contrib['shap_value']:.3f} "
                f"(value: {contrib['feature_value']})"
            )

    # Save SHAP sample
    output_file = Path("samples/golden/shap_high_risk_sample.json")
    with open(output_file, "w") as f:
        json.dump(shap_sample, f, indent=2, default=str)

    print(f"💾 Saved SHAP sample to {output_file}")
    return shap_sample


if __name__ == "__main__":
    generate_shap_sample()
