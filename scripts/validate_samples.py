"""Script to validate all sample files against schemas."""

import json
import sys
from pathlib import Path

sys.path.append(".")

from src.orca.core.decision_contract import AP2DecisionContract, LegacyDecisionRequest


def validate_ap2_sample(file_path: Path) -> tuple[bool, str]:
    """Validate an AP2 sample file."""
    try:
        with open(file_path) as f:
            data = json.load(f)

        # Create a minimal decision outcome for validation
        from uuid import uuid4

        from src.orca.core.decision_contract import DecisionMeta, DecisionOutcome

        decision_meta = DecisionMeta(model="rules_only", trace_id=str(uuid4()), version="0.1.0")

        decision_outcome = DecisionOutcome(
            result="APPROVE", risk_score=0.0, reasons=[], actions=[], meta=decision_meta
        )

        # Add decision to data
        data["decision"] = decision_outcome.model_dump()

        # Validate AP2 contract
        ap2_contract = AP2DecisionContract(**data)
        return True, "Valid AP2 contract"

    except Exception as e:
        return False, f"Validation error: {e}"


def validate_legacy_sample(file_path: Path) -> tuple[bool, str]:
    """Validate a legacy sample file."""
    try:
        with open(file_path) as f:
            data = json.load(f)

        # Validate legacy request
        legacy_request = LegacyDecisionRequest(**data)
        return True, "Valid legacy request"

    except Exception as e:
        return False, f"Validation error: {e}"


def validate_golden_sample(file_path: Path) -> tuple[bool, str]:
    """Validate a golden decision sample file."""
    try:
        with open(file_path) as f:
            data = json.load(f)

        # Check required fields
        required_fields = ["ap2_version", "intent", "cart", "payment", "decision"]
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"

        # Check decision structure
        decision = data["decision"]
        if "result" not in decision or "risk_score" not in decision:
            return False, "Invalid decision structure"

        # Check ML prediction if present
        if "ml_prediction" in data:
            ml_pred = data["ml_prediction"]
            if "risk_score" not in ml_pred or "key_signals" not in ml_pred:
                return False, "Invalid ML prediction structure"

        return True, "Valid golden decision"

    except Exception as e:
        return False, f"Validation error: {e}"


def main():
    """Validate all sample files."""
    print("🔍 Validating sample files...")

    # Validate AP2 samples
    ap2_dir = Path("samples/ap2")
    print(f"\n📁 Validating AP2 samples in {ap2_dir}:")
    ap2_valid = 0
    ap2_total = 0

    for ap2_file in ap2_dir.glob("*.json"):
        ap2_total += 1
        is_valid, message = validate_ap2_sample(ap2_file)
        status = "✅" if is_valid else "❌"
        print(f"  {status} {ap2_file.name}: {message}")
        if is_valid:
            ap2_valid += 1

    # Validate legacy samples
    legacy_dir = Path("samples/legacy")
    print(f"\n📁 Validating legacy samples in {legacy_dir}:")
    legacy_valid = 0
    legacy_total = 0

    for legacy_file in legacy_dir.glob("*.json"):
        legacy_total += 1
        is_valid, message = validate_legacy_sample(legacy_file)
        status = "✅" if is_valid else "❌"
        print(f"  {status} {legacy_file.name}: {message}")
        if is_valid:
            legacy_valid += 1

    # Validate golden samples
    golden_dir = Path("samples/golden")
    print(f"\n📁 Validating golden samples in {golden_dir}:")
    golden_valid = 0
    golden_total = 0

    for golden_file in golden_dir.glob("*.json"):
        golden_total += 1
        is_valid, message = validate_golden_sample(golden_file)
        status = "✅" if is_valid else "❌"
        print(f"  {status} {golden_file.name}: {message}")
        if is_valid:
            golden_valid += 1

    # Summary
    print("\n📊 Validation Summary:")
    print(f"  AP2 samples: {ap2_valid}/{ap2_total} valid")
    print(f"  Legacy samples: {legacy_valid}/{legacy_total} valid")
    print(f"  Golden samples: {golden_valid}/{golden_total} valid")

    total_valid = ap2_valid + legacy_valid + golden_valid
    total_samples = ap2_total + legacy_total + golden_total

    print(f"  Overall: {total_valid}/{total_samples} valid")

    if total_valid == total_samples:
        print("🎉 All samples are valid!")
        return True
    else:
        print("❌ Some samples failed validation")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
