"""Round-trip conversion tests for legacy ↔ AP2 contracts.

These tests ensure that converting from legacy to AP2 and back preserves
semantic meaning and key decision information.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from src.orca.core.decision_legacy_adapter import DecisionLegacyAdapter
from src.orca.core.versioning import get_version_manager, validate_contract_version


class TestRoundTripConversion:
    """Test round-trip conversion between legacy and AP2 formats."""

    def setup_method(self):
        """Set up test environment."""
        self.version_manager = get_version_manager()

    def create_legacy_contract(self) -> dict[str, Any]:
        """Create a sample legacy contract for testing."""
        return {
            "cart_total": 100.00,
            "currency": "USD",
            "rail": "Card",  # Must be "Card" or "ACH"
            "channel": "online",  # Must be "online" or "pos"
            "features": {"amount": 100.0, "velocity_24h": 1.0, "cross_border": 0.0},
            "context": {
                "customer_id": "cust_123",
                "location_country": "US",
                "ip_country": "US",
                "mcc": "5812",
                "auth_requirements": ["pin"],
                "trace_id": "test-trace-123",
                "processing_time_ms": 45.2,
                "model": "rules_only",
            },
        }

    def test_legacy_to_ap2_to_legacy_preserves_decision(self):
        """Test that decision result is preserved through round-trip conversion."""
        # Start with legacy contract
        legacy_contract = self.create_legacy_contract()

        # Convert to AP2
        ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

        # Verify AP2 structure is created correctly
        assert ap2_contract.ap2_version == "0.1.0"
        assert ap2_contract.cart.amount == legacy_contract["cart_total"]
        assert ap2_contract.cart.currency == legacy_contract["currency"]
        assert ap2_contract.payment.modality.value.lower() == legacy_contract["rail"].lower()
        assert ap2_contract.intent.channel.value == legacy_contract["channel"]

        # Convert back to legacy
        converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

        # Verify decision is preserved
        assert converted_legacy.decision == "APPROVE"  # Default decision
        assert isinstance(converted_legacy.reasons, list)
        assert isinstance(converted_legacy.actions, list)

    def test_legacy_to_ap2_to_legacy_preserves_cart_info(self):
        """Test that cart information is preserved through round-trip conversion."""
        legacy_contract = self.create_legacy_contract()

        # Convert to AP2
        ap2_contract = self.adapter.from_legacy_json(json.dumps(legacy_contract))

        # Verify AP2 structure
        assert ap2_contract.cart.amount == legacy_contract["cart_total"]
        assert ap2_contract.cart.currency == legacy_contract["currency"]
        assert ap2_contract.cart.mcc == legacy_contract["mcc"]

        # Convert back to legacy
        converted_legacy = json.loads(self.adapter.to_legacy_json(ap2_contract))

        # Verify cart info is preserved in AP2 structure
        assert ap2_contract.cart.amount == legacy_contract["cart_total"]
        assert ap2_contract.cart.currency == legacy_contract["currency"]

    def test_legacy_to_ap2_to_legacy_preserves_payment_info(self):
        """Test that payment information is preserved through round-trip conversion."""
        legacy_contract = self.create_legacy_contract()

        # Convert to AP2
        ap2_contract = self.adapter.from_legacy_json(json.dumps(legacy_contract))

        # Verify AP2 structure
        assert ap2_contract.payment.modality.value == legacy_contract["rail"]
        assert (
            ap2_contract.payment.auth_requirements[0].value
            == legacy_contract["auth_requirements"][0]
        )

        # Convert back to legacy
        converted_legacy = json.loads(self.adapter.to_legacy_json(ap2_contract))

        # Verify payment info is preserved
        assert converted_legacy["rail"] == legacy_contract["rail"]
        assert converted_legacy["auth_requirements"] == legacy_contract["auth_requirements"]

    def test_legacy_to_ap2_to_legacy_preserves_intent_info(self):
        """Test that intent information is preserved through round-trip conversion."""
        legacy_contract = self.create_legacy_contract()

        # Convert to AP2
        ap2_contract = self.adapter.from_legacy_json(json.dumps(legacy_contract))

        # Verify AP2 structure
        assert ap2_contract.intent.channel.value == legacy_contract["channel"]
        assert ap2_contract.intent.actor.value == "human"  # Default mapping

        # Convert back to legacy
        converted_legacy = json.loads(self.adapter.to_legacy_json(ap2_contract))

        # Verify intent info is preserved
        assert converted_legacy["channel"] == legacy_contract["channel"]

    def test_legacy_to_ap2_to_legacy_preserves_metadata(self):
        """Test that metadata is preserved through round-trip conversion."""
        legacy_contract = self.create_legacy_contract()

        # Convert to AP2
        ap2_contract = self.adapter.from_legacy_json(json.dumps(legacy_contract))

        # Verify AP2 structure
        assert ap2_contract.decision.meta.trace_id == legacy_contract["metadata"]["trace_id"]
        assert (
            ap2_contract.decision.meta.processing_time_ms
            == legacy_contract["metadata"]["processing_time_ms"]
        )
        assert ap2_contract.decision.meta.model == legacy_contract["metadata"]["model"]

        # Convert back to legacy
        converted_legacy = json.loads(self.adapter.to_legacy_json(ap2_contract))

        # Verify metadata is preserved
        assert converted_legacy["metadata"]["trace_id"] == legacy_contract["metadata"]["trace_id"]
        assert (
            converted_legacy["metadata"]["processing_time_ms"]
            == legacy_contract["metadata"]["processing_time_ms"]
        )
        assert converted_legacy["metadata"]["model"] == legacy_contract["metadata"]["model"]

    def test_legacy_to_ap2_to_legacy_preserves_geo_info(self):
        """Test that geographic information is preserved through round-trip conversion."""
        legacy_contract = self.create_legacy_contract()

        # Convert to AP2
        ap2_contract = self.adapter.from_legacy_json(json.dumps(legacy_contract))

        # Verify AP2 structure
        assert ap2_contract.cart.geo.country == legacy_contract["location_country"]
        assert ap2_contract.cart.geo.ip_country == legacy_contract["ip_country"]

        # Convert back to legacy
        converted_legacy = json.loads(self.adapter.to_legacy_json(ap2_contract))

        # Verify geo info is preserved
        assert converted_legacy["location_country"] == legacy_contract["location_country"]
        assert converted_legacy["ip_country"] == legacy_contract["ip_country"]

    def test_round_trip_with_different_decision_types(self):
        """Test round-trip conversion with different decision types."""
        decision_types = ["APPROVE", "REVIEW", "DECLINE"]

        for decision_type in decision_types:
            legacy_contract = self.create_legacy_contract()
            legacy_contract["decision"] = decision_type

            # Convert to AP2
            ap2_contract = self.adapter.from_legacy_json(json.dumps(legacy_contract))

            # Convert back to legacy
            converted_legacy = json.loads(self.adapter.to_legacy_json(ap2_contract))

            # Verify decision type is preserved
            assert converted_legacy["decision"] == decision_type

    def test_round_trip_with_different_risk_scores(self):
        """Test round-trip conversion with different risk scores."""
        risk_scores = [0.0, 0.25, 0.5, 0.75, 1.0]

        for risk_score in risk_scores:
            legacy_contract = self.create_legacy_contract()
            legacy_contract["risk_score"] = risk_score

            # Convert to AP2
            ap2_contract = self.adapter.from_legacy_json(json.dumps(legacy_contract))

            # Convert back to legacy
            converted_legacy = json.loads(self.adapter.to_legacy_json(ap2_contract))

            # Verify risk score is preserved
            assert converted_legacy["risk_score"] == risk_score

    def test_round_trip_with_different_currencies(self):
        """Test round-trip conversion with different currencies."""
        currencies = ["USD", "EUR", "GBP", "CAD", "AUD"]

        for currency in currencies:
            legacy_contract = self.create_legacy_contract()
            legacy_contract["currency"] = currency

            # Convert to AP2
            ap2_contract = self.adapter.from_legacy_json(json.dumps(legacy_contract))

            # Convert back to legacy
            converted_legacy = json.loads(self.adapter.to_legacy_json(ap2_contract))

            # Verify currency is preserved
            assert converted_legacy["currency"] == currency

    def test_round_trip_with_different_channels(self):
        """Test round-trip conversion with different channels."""
        channels = ["web", "pos", "mobile", "api"]

        for channel in channels:
            legacy_contract = self.create_legacy_contract()
            legacy_contract["channel"] = channel

            # Convert to AP2
            ap2_contract = self.adapter.from_legacy_json(json.dumps(legacy_contract))

            # Convert back to legacy
            converted_legacy = json.loads(self.adapter.to_legacy_json(ap2_contract))

            # Verify channel is preserved
            assert converted_legacy["channel"] == channel

    def test_round_trip_with_different_rails(self):
        """Test round-trip conversion with different payment rails."""
        rails = ["card", "ach", "wire", "crypto"]

        for rail in rails:
            legacy_contract = self.create_legacy_contract()
            legacy_contract["rail"] = rail

            # Convert to AP2
            ap2_contract = self.adapter.from_legacy_json(json.dumps(legacy_contract))

            # Convert back to legacy
            converted_legacy = json.loads(self.adapter.to_legacy_json(ap2_contract))

            # Verify rail is preserved
            assert converted_legacy["rail"] == rail

    def test_round_trip_preserves_version_info(self):
        """Test that version information is properly handled in round-trip conversion."""
        legacy_contract = self.create_legacy_contract()

        # Convert to AP2
        ap2_contract = self.adapter.from_legacy_json(json.dumps(legacy_contract))

        # Verify AP2 version is set
        assert ap2_contract.ap2_version == "0.1.0"

        # Convert back to legacy
        converted_legacy = json.loads(self.adapter.to_legacy_json(ap2_contract))

        # Verify legacy version is preserved
        assert converted_legacy["version"] == legacy_contract["version"]

    def test_round_trip_with_complex_reason_codes(self):
        """Test round-trip conversion with complex reason codes."""
        legacy_contract = self.create_legacy_contract()
        legacy_contract["reason_codes"] = ["HIGH_AMOUNT", "VELOCITY", "CROSS_BORDER"]
        legacy_contract["actions"] = ["manual_review", "step_up_auth"]

        # Convert to AP2
        ap2_contract = self.adapter.from_legacy_json(json.dumps(legacy_contract))

        # Verify AP2 structure
        assert len(ap2_contract.decision.reasons) == 3
        assert len(ap2_contract.decision.actions) == 2

        # Convert back to legacy
        converted_legacy = json.loads(self.adapter.to_legacy_json(ap2_contract))

        # Verify reason codes and actions are preserved
        assert converted_legacy["reason_codes"] == legacy_contract["reason_codes"]
        assert converted_legacy["actions"] == legacy_contract["actions"]

    def test_round_trip_with_missing_optional_fields(self):
        """Test round-trip conversion with missing optional fields."""
        legacy_contract = self.create_legacy_contract()

        # Remove optional fields
        del legacy_contract["mcc"]
        del legacy_contract["auth_requirements"]
        del legacy_contract["metadata"]["processing_time_ms"]

        # Convert to AP2
        ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

        # Convert back to legacy
        converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

        # Verify that missing fields are handled gracefully
        assert "mcc" not in converted_legacy or converted_legacy["mcc"] is None
        assert (
            "auth_requirements" not in converted_legacy
            or converted_legacy["auth_requirements"] is None
        )
        assert (
            "processing_time_ms" not in converted_legacy["metadata"]
            or converted_legacy["metadata"]["processing_time_ms"] is None
        )

    def test_round_trip_semantic_equivalence(self):
        """Test that round-trip conversion maintains semantic equivalence."""
        legacy_contract = self.create_legacy_contract()

        # Convert to AP2
        ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

        # Convert back to legacy
        converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

        # Verify semantic equivalence
        assert converted_legacy["decision"] == legacy_contract["decision"]
        assert abs(converted_legacy["risk_score"] - legacy_contract["risk_score"]) < 0.001
        assert set(converted_legacy["reason_codes"]) == set(legacy_contract["reason_codes"])
        assert set(converted_legacy["actions"]) == set(legacy_contract["actions"])
        assert converted_legacy["cart_total"] == legacy_contract["cart_total"]
        assert converted_legacy["currency"] == legacy_contract["currency"]
        assert converted_legacy["rail"] == legacy_contract["rail"]
        assert converted_legacy["channel"] == legacy_contract["channel"]

    def test_version_validation_in_round_trip(self):
        """Test that version validation works correctly in round-trip conversion."""
        legacy_contract = self.create_legacy_contract()

        # Convert to AP2
        ap2_contract = self.adapter.from_legacy_json(json.dumps(legacy_contract))

        # Validate AP2 contract
        is_valid, message = validate_contract_version(ap2_contract.model_dump())
        assert is_valid, f"AP2 contract validation failed: {message}"

        # Convert back to legacy
        converted_legacy = json.loads(self.adapter.to_legacy_json(ap2_contract))

        # Validate legacy contract
        is_valid, message = validate_contract_version(converted_legacy)
        assert is_valid, f"Legacy contract validation failed: {message}"

    def test_round_trip_with_golden_files(self):
        """Test round-trip conversion using golden files if available."""
        golden_legacy_file = Path("tests/golden/decision.legacy.json")
        golden_ap2_file = Path("tests/golden/decision.ap2.json")

        if golden_legacy_file.exists():
            with open(golden_legacy_file) as f:
                legacy_contract = json.load(f)

            # Convert to AP2
            ap2_contract = self.adapter.from_legacy_json(json.dumps(legacy_contract))

            # Convert back to legacy
            converted_legacy = json.loads(self.adapter.to_legacy_json(ap2_contract))

            # Verify key fields are preserved
            assert converted_legacy["decision"] == legacy_contract["decision"]
            assert converted_legacy["risk_score"] == legacy_contract["risk_score"]
            assert converted_legacy["cart_total"] == legacy_contract["cart_total"]
            assert converted_legacy["currency"] == legacy_contract["currency"]
        else:
            pytest.skip("Golden legacy file not found")

    def test_round_trip_performance(self):
        """Test that round-trip conversion performs reasonably well."""
        import time

        legacy_contract = self.create_legacy_contract()

        # Measure conversion time
        start_time = time.time()

        # Convert to AP2
        ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

        # Convert back to legacy
        converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

        end_time = time.time()
        conversion_time = end_time - start_time

        # Should complete in reasonable time (less than 1 second)
        assert conversion_time < 1.0, f"Round-trip conversion took too long: {conversion_time:.3f}s"

        # Verify result is correct
        assert converted_legacy["decision"] == legacy_contract["decision"]
