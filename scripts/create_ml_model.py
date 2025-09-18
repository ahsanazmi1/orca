#!/usr/bin/env python3
"""
Create and deploy a simple ML model for Orca risk prediction.
"""

import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from typing import Any  # noqa: E402

from src.orca_core.ml.model import get_model_info, predict_risk  # noqa: E402


def create_sample_data() -> list[dict[str, Any]]:
    """Create sample training data for the ML model."""
    sample_data = []

    # Generate sample transactions with various risk levels
    scenarios = [
        # Low risk scenarios
        {"amount": 50.0, "velocity_24h": 1.0, "cross_border": 0.0, "expected_risk": 0.35},
        {"amount": 100.0, "velocity_24h": 1.0, "cross_border": 0.0, "expected_risk": 0.35},
        {"amount": 200.0, "velocity_24h": 2.0, "cross_border": 0.0, "expected_risk": 0.35},
        # Medium risk scenarios
        {"amount": 600.0, "velocity_24h": 1.0, "cross_border": 0.0, "expected_risk": 0.55},
        {"amount": 100.0, "velocity_24h": 3.0, "cross_border": 0.0, "expected_risk": 0.45},
        {"amount": 100.0, "velocity_24h": 1.0, "cross_border": 1.0, "expected_risk": 0.45},
        # High risk scenarios
        {"amount": 600.0, "velocity_24h": 3.0, "cross_border": 0.0, "expected_risk": 0.65},
        {"amount": 600.0, "velocity_24h": 1.0, "cross_border": 1.0, "expected_risk": 0.65},
        {"amount": 100.0, "velocity_24h": 3.0, "cross_border": 1.0, "expected_risk": 0.55},
        # Very high risk scenarios
        {"amount": 600.0, "velocity_24h": 3.0, "cross_border": 1.0, "expected_risk": 0.75},
        {"amount": 1000.0, "velocity_24h": 5.0, "cross_border": 1.0, "expected_risk": 0.75},
    ]

    for scenario in scenarios:
        # Use our stub model to get the actual risk score
        features = {
            "amount": scenario["amount"],
            "velocity_24h": scenario["velocity_24h"],
            "cross_border": scenario["cross_border"],
        }
        result = predict_risk(features)

        sample_data.append(
            {
                "features": features,
                "risk_score": result["risk_score"],
                "reason_codes": result["reason_codes"],
                "version": result["version"],
            }
        )

    # Return sample data for testing
    return sample_data


def main() -> None:
    """Main function to create ML model data."""
    print("🤖 Creating ML model data for Orca risk prediction...")

    # Create sample data
    sample_data = create_sample_data()

    # Save to file
    output_file = Path(__file__).parent.parent / "data" / "ml_training_data.json"
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(sample_data, f, indent=2)

    print(f"✅ Created {len(sample_data)} training samples")
    print(f"📁 Saved to: {output_file}")

    # Show model info
    model_info = get_model_info()
    print("\n📊 Model Information:")
    print(f"   Name: {model_info['name']}")
    print(f"   Version: {model_info['version']}")
    print(f"   Type: {model_info['type']}")
    print(f"   Features: {', '.join(model_info['features'])}")

    # Show sample predictions
    print("\n🧪 Sample Predictions:")
    for i, sample in enumerate(sample_data[:3]):
        features = sample["features"]
        risk_score = sample["risk_score"]
        reason_codes = sample["reason_codes"]
        print(
            f"   {i+1}. Amount: ${features['amount']}, "
            f"Velocity: {features['velocity_24h']}, "
            f"Cross-border: {features['cross_border']}"
        )
        print(f"      → Risk Score: {risk_score:.2f}, Reasons: {reason_codes}")


if __name__ == "__main__":
    main()
