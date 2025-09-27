#!/usr/bin/env python3
"""
Test script for Phase 3 CloudEvent schemas validation.

This script validates all Phase 3 schemas against their corresponding example events
and ensures proper CloudEvent compliance.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

try:
    import jsonschema
    from jsonschema import validate, ValidationError
except ImportError:
    print("Error: jsonschema package not found. Install with: pip install jsonschema")
    sys.exit(1)


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Load and parse a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {e}")


def validate_cloudevent(event_data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """Validate a CloudEvent against its schema."""
    try:
        validate(instance=event_data, schema=schema)
        return True
    except ValidationError as e:
        print(f"Validation error: {e.message}")
        print(f"Path: {' -> '.join(str(p) for p in e.absolute_path)}")
        return False


def test_phase3_schemas():
    """Test all Phase 3 CloudEvent schemas and examples."""
    
    # Define schema and example mappings
    schema_example_pairs = [
        ("weave.bid_request.v1.schema.json", "weave.bid_request.example.json"),
        ("weave.bid_response.v1.schema.json", "weave.bid_response.example.json"),
        ("oasis.constraint.v1.schema.json", "oasis.constraint.example.json"),
        ("onyx.trust_signal.v1.schema.json", "onyx.trust_signal.example.json"),
        ("opal.explanation.v1.schema.json", "opal.explanation.example.json"),
        ("olive.policy_applied.v1.schema.json", "olive.policy_applied.example.json"),
    ]
    
    # Get the base directory (this script's directory)
    base_dir = Path(__file__).parent.parent
    
    schemas_dir = base_dir / "common" / "events" / "v1"
    examples_dir = base_dir / "examples" / "events"
    
    print("🧪 Testing Phase 3 CloudEvent Schemas")
    print("=" * 50)
    
    all_tests_passed = True
    
    for schema_file, example_file in schema_example_pairs:
        print(f"\n📋 Testing {schema_file}")
        print("-" * 30)
        
        # Load schema
        schema_path = schemas_dir / schema_file
        try:
            schema = load_json_file(schema_path)
            print(f"✅ Schema loaded: {schema_file}")
        except Exception as e:
            print(f"❌ Failed to load schema {schema_file}: {e}")
            all_tests_passed = False
            continue
        
        # Load example event
        example_path = examples_dir / example_file
        try:
            example_event = load_json_file(example_path)
            print(f"✅ Example loaded: {example_file}")
        except Exception as e:
            print(f"❌ Failed to load example {example_file}: {e}")
            all_tests_passed = False
            continue
        
        # Validate example against schema
        if validate_cloudevent(example_event, schema):
            print(f"✅ Validation passed: {example_file} matches {schema_file}")
        else:
            print(f"❌ Validation failed: {example_file} does not match {schema_file}")
            all_tests_passed = False
        
        # Test basic CloudEvent structure
        required_ce_fields = ["specversion", "id", "source", "type", "subject", "time", "data"]
        missing_fields = [field for field in required_ce_fields if field not in example_event]
        
        if missing_fields:
            print(f"❌ Missing CloudEvent fields: {missing_fields}")
            all_tests_passed = False
        else:
            print(f"✅ CloudEvent structure valid")
        
        # Test event type matches schema
        expected_type = schema_file.replace(".schema.json", "")
        actual_type = example_event.get("type", "")
        
        if actual_type == f"ocn.{expected_type}":
            print(f"✅ Event type matches: {actual_type}")
        else:
            print(f"❌ Event type mismatch: expected 'ocn.{expected_type}', got '{actual_type}'")
            all_tests_passed = False
    
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 All Phase 3 schema tests PASSED!")
        return True
    else:
        print("❌ Some Phase 3 schema tests FAILED!")
        return False


def test_existing_schemas():
    """Test existing schemas are still valid."""
    
    print("\n🔍 Testing existing schemas...")
    print("=" * 50)
    
    base_dir = Path(__file__).parent.parent
    schemas_dir = base_dir / "common" / "events" / "v1"
    
    existing_schemas = [
        "orca.decision.v1.schema.json",
        "orca.explanation.v1.schema.json",
        "weave.audit.v1.schema.json"
    ]
    
    all_existing_valid = True
    
    for schema_file in existing_schemas:
        schema_path = schemas_dir / schema_file
        try:
            schema = load_json_file(schema_path)
            print(f"✅ Existing schema valid: {schema_file}")
        except Exception as e:
            print(f"❌ Existing schema invalid: {schema_file}: {e}")
            all_existing_valid = False
    
    return all_existing_valid


def main():
    """Main test runner."""
    print("🚀 OCN Common Phase 3 Schema Validation Tests")
    print("=" * 60)
    
    # Test existing schemas
    existing_valid = test_existing_schemas()
    
    # Test Phase 3 schemas
    phase3_valid = test_phase3_schemas()
    
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"   Existing schemas: {'✅ PASS' if existing_valid else '❌ FAIL'}")
    print(f"   Phase 3 schemas:  {'✅ PASS' if phase3_valid else '❌ FAIL'}")
    
    if existing_valid and phase3_valid:
        print("\n🎉 All tests PASSED! Ready for Phase 3 development.")
        sys.exit(0)
    else:
        print("\n❌ Some tests FAILED! Please fix issues before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    main()
