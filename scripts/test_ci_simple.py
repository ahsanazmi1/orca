"""Simple CI job tests to validate configuration."""

import json
import os
import sys
from pathlib import Path


def test_golden_snapshots():
    """Test golden snapshots validation."""
    print("\n🔍 Testing Golden Snapshots...")

    golden_dir = Path("samples/golden")
    golden_files = list(golden_dir.glob("*.json"))

    print(f"Found {len(golden_files)} golden files")

    for f in golden_files:
        with open(f) as file:
            data = json.load(file)

        assert "ml_prediction" in data, f"Missing ml_prediction in {f.name}"
        risk_score = data["ml_prediction"]["risk_score"]
        print(f"✅ {f.name}: {risk_score:.3f}")

    return True


def test_feature_spec():
    """Test feature specification validation."""
    print("\n🔍 Testing Feature Specification...")

    spec_path = Path("models/xgb/1.0.0/feature_spec.json")
    with open(spec_path) as f:
        spec = json.load(f)

    print(f"Features: {len(spec['feature_names'])}")
    print(f"AP2 mappings: {len(spec['ap2_mappings'])}")

    assert "feature_names" in spec
    assert "ap2_mappings" in spec

    return True


def test_shap_snapshots():
    """Test SHAP snapshots generation."""
    print("\n🔍 Testing SHAP Snapshots...")

    # Add src to path
    sys.path.append(".")

    # Set environment for SHAP
    os.environ["ORCA_ENABLE_SHAP"] = "true"
    os.environ["ORCA_USE_XGB"] = "true"

    try:
        from src.orca.ml.predict_risk import predict_with_shap

        features = {
            "amount": 1500.0,
            "velocity_24h": 4.0,
            "velocity_7d": 12.0,
            "cross_border": 1.0,
            "location_mismatch": 1.0,
            "payment_method_risk": 0.7,
            "chargebacks_12m": 3.0,
            "customer_age_days": 30.0,
            "loyalty_score": 0.1,
            "time_since_last_purchase": 0.1,
        }

        result = predict_with_shap(features)
        snapshot = {"risk_score": result["risk_score"], "key_signals": result["key_signals"][:5]}

        Path("tests/snapshots").mkdir(exist_ok=True)
        with open("tests/snapshots/shap_test.json", "w") as f:
            json.dump(snapshot, f, indent=2)

        print(
            f"SHAP snapshot: risk_score={result['risk_score']:.3f}, signals={len(result['key_signals'])}"
        )
        return True

    except Exception as e:
        print(f"❌ SHAP test failed: {e}")
        return False


def test_explain_nlg():
    """Test explain NLG field validation."""
    print("\n🔍 Testing Explain NLG...")

    with open("samples/ap2/approve_card_low_risk.json") as f:
        ap2_data = json.load(f)

    valid_fields = set()

    def extract_fields(obj, prefix=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{prefix}.{key}" if prefix else key
                valid_fields.add(current_path)
                if isinstance(value, dict | list):
                    extract_fields(value, current_path)

    extract_fields(ap2_data)

    print(f"Valid AP2 fields: {len(valid_fields)}")

    Path("tests/snapshots").mkdir(exist_ok=True)
    with open("tests/snapshots/valid_ap2_fields.json", "w") as f:
        json.dump(sorted(valid_fields), f, indent=2)

    return True


def main():
    """Run all CI job tests."""
    print("🚀 Testing CI Jobs (Simple Version)")
    print("=" * 50)

    results = {}

    try:
        results["golden_snapshots"] = test_golden_snapshots()
    except Exception as e:
        print(f"❌ Golden snapshots test failed: {e}")
        results["golden_snapshots"] = False

    try:
        results["feature_spec"] = test_feature_spec()
    except Exception as e:
        print(f"❌ Feature spec test failed: {e}")
        results["feature_spec"] = False

    try:
        results["shap_snapshots"] = test_shap_snapshots()
    except Exception as e:
        print(f"❌ SHAP snapshots test failed: {e}")
        results["shap_snapshots"] = False

    try:
        results["explain_nlg"] = test_explain_nlg()
    except Exception as e:
        print(f"❌ Explain NLG test failed: {e}")
        results["explain_nlg"] = False

    # Summary
    print("\n" + "=" * 50)
    print("📊 CI Job Test Summary")
    print("=" * 50)

    passed = 0
    total = len(results)

    for job, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{job:20} {status}")
        if success:
            passed += 1

    print(f"\nResults: {passed}/{total} jobs passed")

    if passed == total:
        print("🎉 All CI jobs passed!")
        return True
    else:
        print("❌ Some CI jobs failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
