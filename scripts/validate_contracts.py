#!/usr/bin/env python3
"""
Contract validation script for CI/CD.

This script validates AP2 contracts and CloudEvents against ocn-common schemas.
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orca.core.contract_validation import get_contract_validator


def validate_files(file_paths: list[str], schema_type: str) -> tuple[int, int]:
    """
    Validate files against a schema type.

    Args:
        file_paths: List of file paths to validate
        schema_type: Type of schema to validate against

    Returns:
        Tuple of (valid_count, total_count)
    """
    validator = get_contract_validator()
    valid_count = 0
    total_count = len(file_paths)

    for file_path in file_paths:
        try:
            if validator.validate_file(file_path, schema_type):
                print(f"✅ {file_path}")
                valid_count += 1
            else:
                print(f"❌ {file_path}")
        except Exception as e:
            print(f"❌ {file_path}: {e}")

    return valid_count, total_count


def main() -> int:
    """Main validation function."""
    parser = argparse.ArgumentParser(description="Validate contracts against ocn-common schemas")
    parser.add_argument(
        "--schema-type",
        required=True,
        help="Schema type (ap2_decision, ap2_explanation, cloudevent:orca.decision.v1, etc.)",
    )
    parser.add_argument("--files", nargs="+", required=True, help="Files to validate")
    parser.add_argument(
        "--exit-on-failure", action="store_true", help="Exit with error code if validation fails"
    )

    args = parser.parse_args()

    print(f"🔍 Validating {len(args.files)} files against {args.schema_type} schema...")

    valid_count, total_count = validate_files(args.files, args.schema_type)

    print("\n📊 Validation Results:")
    print(f"   Valid: {valid_count}/{total_count}")
    print(f"   Failed: {total_count - valid_count}/{total_count}")

    if valid_count == total_count:
        print("✅ All files validated successfully!")
        return 0
    else:
        print("❌ Some files failed validation")
        if args.exit_on_failure:
            return 1
        else:
            return 0


if __name__ == "__main__":
    sys.exit(main())
