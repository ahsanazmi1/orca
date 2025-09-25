"""
Tests for example validation against schemas.
"""

import json
from pathlib import Path

import pytest

from src.ocn_common.contracts import validate_cloudevent, validate_json


class TestExampleValidation:
    """Test that all examples validate against their schemas."""

    def test_ap2_examples_validate(self):
        """Test that AP2 examples validate against mandate schemas."""
        examples_dir = Path(__file__).parent.parent / "examples" / "ap2"

        if not examples_dir.exists():
            pytest.skip("Examples directory not found")

        for example_file in examples_dir.glob("*.json"):
            with open(example_file) as f:
                ap2_data = json.load(f)

            # Validate individual mandate components
            assert validate_json(ap2_data["intent"], "intent_mandate") is True
            assert validate_json(ap2_data["cart"], "cart_mandate") is True
            assert validate_json(ap2_data["payment"], "payment_mandate") is True

    def test_cloudevent_examples_validate(self):
        """Test that CloudEvent examples validate against their schemas."""
        examples_dir = Path(__file__).parent.parent / "examples" / "events"

        if not examples_dir.exists():
            pytest.skip("Examples directory not found")

        # Test decision CloudEvent
        decision_file = examples_dir / "decision_approve.json"
        if decision_file.exists():
            with open(decision_file) as f:
                decision_ce = json.load(f)
            assert validate_cloudevent(decision_ce, "ocn.orca.decision.v1") is True

        # Test explanation CloudEvent
        explanation_file = examples_dir / "explanation_approve.json"
        if explanation_file.exists():
            with open(explanation_file) as f:
                explanation_ce = json.load(f)
            assert validate_cloudevent(explanation_ce, "ocn.orca.explanation.v1") is True

        # Test audit CloudEvent
        audit_file = examples_dir / "audit_approve.json"
        if audit_file.exists():
            with open(audit_file) as f:
                audit_ce = json.load(f)
            assert validate_cloudevent(audit_ce, "ocn.weave.audit.v1") is True
