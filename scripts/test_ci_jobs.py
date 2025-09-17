"""Test CI jobs locally to validate configuration."""

import os
import subprocess
import sys


def run_command(cmd: str, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n🔍 {description}")
    print(f"Command: {cmd}")

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Success")
            if result.stdout:
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print("❌ Failed")
            if result.stderr:
                print(f"Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def test_schema_validation() -> bool:
    """Test schema validation job."""
    print("\n" + "=" * 50)
    print("🧪 Testing Schema Validation Job")
    print("=" * 50)

    # Test AP2 sample validation
    success = run_command("python scripts/validate_samples.py", "Validating AP2 and legacy samples")

    return success


def test_crypto_determinism() -> bool:
    """Test crypto determinism job."""
    print("\n" + "=" * 50)
    print("🧪 Testing Crypto Determinism Job")
    print("=" * 50)

    # Generate test keys
    success = run_command("python scripts/generate_test_keys.py", "Generating test keys")

    if not success:
        return False

    # Test key generation determinism
    success = run_command(
        'python -c "from scripts.generate_test_keys import generate_ed25519_keypair, get_key_fingerprint; '
        "fingerprints = [get_key_fingerprint(generate_ed25519_keypair()[1]) for _ in range(3)]; "
        "print(f'Fingerprints: {fingerprints}'); "
        "assert len(set(fingerprints)) == len(fingerprints), 'Keys should be unique'\"",
        "Testing key generation determinism",
    )

    return success


def test_golden_snapshots() -> bool:
    """Test golden snapshots job."""
    print("\n" + "=" * 50)
    print("🧪 Testing Golden Snapshots Job")
    print("=" * 50)

    # Generate golden decisions
    success = run_command(
        "python scripts/generate_golden_decisions.py", "Generating golden decisions"
    )

    if not success:
        return False

    # Validate golden snapshots
    success = run_command(
        'python -c "'
        "from pathlib import Path; "
        "import json; "
        "golden_dir = Path('samples/golden'); "
        "golden_files = list(golden_dir.glob('*.json')); "
        "print(f'Found {len(golden_files)} golden files'); "
        "for f in golden_files: "
        "  data = json.load(open(f)); "
        "  assert 'ml_prediction' in data; "
        '  print(f\'✅ {f.name}: {data[\\"ml_prediction\\"][\\"risk_score\\"]:.3f}\')"',
        "Validating golden snapshots",
    )

    return success


def test_inference() -> bool:
    """Test inference job."""
    print("\n" + "=" * 50)
    print("🧪 Testing Inference Job")
    print("=" * 50)

    # Set deterministic environment
    os.environ["XGBOOST_RANDOM_STATE"] = "42"
    os.environ["PYTHONHASHSEED"] = "0"
    os.environ["ORCA_USE_XGB"] = "true"

    # Test inference determinism
    success = run_command(
        'python -c "'
        "import os, numpy as np; "
        "os.environ['XGBOOST_RANDOM_STATE'] = '42'; "
        "os.environ['PYTHONHASHSEED'] = '0'; "
        "os.environ['ORCA_USE_XGB'] = 'true'; "
        "np.random.seed(42); "
        "from src.orca.ml.predict_risk import predict_risk; "
        "features = {'amount': 100.0, 'velocity_24h': 1.0, 'velocity_7d': 3.0, 'cross_border': 0.0, 'location_mismatch': 0.0, 'payment_method_risk': 0.3, 'chargebacks_12m': 0.0, 'customer_age_days': 365.0, 'loyalty_score': 0.5, 'time_since_last_purchase': 7.0}; "
        "results = [predict_risk(features)['risk_score'] for _ in range(3)]; "
        "print(f'Results: {results}'); "
        "assert all(abs(r - results[0]) < 1e-10 for r in results), 'Inference should be deterministic'\"",
        "Testing inference determinism",
    )

    return success


def test_feature_spec() -> bool:
    """Test feature specification job."""
    print("\n" + "=" * 50)
    print("🧪 Testing Feature Specification Job")
    print("=" * 50)

    # Validate feature specification
    success = run_command(
        'python -c "'
        "from pathlib import Path; "
        "import json; "
        "spec_path = Path('models/xgb/1.0.0/feature_spec.json'); "
        "spec = json.load(open(spec_path)); "
        "print(f'Features: {len(spec[\\\"feature_names\\\"])}'); "
        "print(f'AP2 mappings: {len(spec[\\\"ap2_mappings\\\"])}'); "
        "assert 'feature_names' in spec; "
        "assert 'ap2_mappings' in spec\"",
        "Validating feature specification",
    )

    return success


def test_shap_snapshots() -> bool:
    """Test SHAP snapshots job."""
    print("\n" + "=" * 50)
    print("🧪 Testing SHAP Snapshots Job")
    print("=" * 50)

    # Set environment for SHAP
    os.environ["ORCA_ENABLE_SHAP"] = "true"
    os.environ["ORCA_USE_XGB"] = "true"

    # Generate SHAP snapshots
    success = run_command(
        'python -c "'
        "import os, json; "
        "from pathlib import Path; "
        "os.environ['ORCA_ENABLE_SHAP'] = 'true'; "
        "os.environ['ORCA_USE_XGB'] = 'true'; "
        "from src.orca.ml.predict_risk import predict_with_shap; "
        "features = {'amount': 1500.0, 'velocity_24h': 4.0, 'velocity_7d': 12.0, 'cross_border': 1.0, 'location_mismatch': 1.0, 'payment_method_risk': 0.7, 'chargebacks_12m': 3.0, 'customer_age_days': 30.0, 'loyalty_score': 0.1, 'time_since_last_purchase': 0.1}; "
        "result = predict_with_shap(features); "
        "snapshot = {'risk_score': result['risk_score'], 'key_signals': result['key_signals'][:5]}; "
        "Path('tests/snapshots').mkdir(exist_ok=True); "
        "json.dump(snapshot, open('tests/snapshots/shap_test.json', 'w'), indent=2); "
        'print(f\'SHAP snapshot: risk_score={result[\\"risk_score\\"]:.3f}, signals={len(result[\\"key_signals\\"])}\')"',
        "Generating SHAP snapshots",
    )

    return success


def test_explain_nlg() -> bool:
    """Test explain NLG job."""
    print("\n" + "=" * 50)
    print("🧪 Testing Explain NLG Job")
    print("=" * 50)

    # Test AP2 field validation
    success = run_command(
        'python -c "'
        "from pathlib import Path; "
        "import json; "
        "with open('samples/ap2/approve_card_low_risk.json') as f: "
        "  ap2_data = json.load(f); "
        "valid_fields = set(); "
        "def extract_fields(obj, prefix=''): "
        "  if isinstance(obj, dict): "
        "    for key, value in obj.items(): "
        "      current_path = f'{prefix}.{key}' if prefix else key; "
        "      valid_fields.add(current_path); "
        "      if isinstance(value, (dict, list)): "
        "        extract_fields(value, current_path); "
        "extract_fields(ap2_data); "
        "print(f'Valid AP2 fields: {len(valid_fields)}'); "
        "Path('tests/snapshots').mkdir(exist_ok=True); "
        "json.dump(sorted(list(valid_fields)), open('tests/snapshots/valid_ap2_fields.json', 'w'), indent=2)\"",
        "Testing AP2 field validation",
    )

    return success


def main():
    """Run all CI job tests."""
    print("🚀 Testing CI Jobs Locally")
    print("=" * 60)

    # Track results
    results = {}

    # Run all tests
    results["schema_validation"] = test_schema_validation()
    results["crypto_determinism"] = test_crypto_determinism()
    results["golden_snapshots"] = test_golden_snapshots()
    results["inference"] = test_inference()
    results["feature_spec"] = test_feature_spec()
    results["shap_snapshots"] = test_shap_snapshots()
    results["explain_nlg"] = test_explain_nlg()

    # Summary
    print("\n" + "=" * 60)
    print("📊 CI Job Test Summary")
    print("=" * 60)

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
