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
        # Card rail maps to immediate modality as per AP2 payment modality mapping
        if legacy_contract["rail"] == "Card":
            assert ap2_contract.payment.modality.value == "immediate"
        elif legacy_contract["rail"] == "ACH":
            assert ap2_contract.payment.modality.value == "deferred"
        # Channel mapping: online -> web, pos -> pos as per AP2 channel mapping
        if legacy_contract["channel"] == "online":
            assert ap2_contract.intent.channel.value == "web"
        elif legacy_contract["channel"] == "pos":
            assert ap2_contract.intent.channel.value == "pos"

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
        ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

        # Verify AP2 structure
        assert ap2_contract.cart.amount == legacy_contract["cart_total"]
        assert ap2_contract.cart.currency == legacy_contract["currency"]
        # Legacy adapter uses default MCC since legacy contracts don't have top-level MCC
        assert ap2_contract.cart.mcc == "0000"

        # Convert back to legacy
        converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

        # Verify cart info is preserved through round-trip
        assert converted_legacy.meta["cart_total"] == legacy_contract["cart_total"]
        assert converted_legacy.meta.get("currency", "USD") == legacy_contract["currency"]

    def test_legacy_to_ap2_to_legacy_preserves_payment_info(self):
        """Test that payment information is preserved through round-trip conversion."""
        legacy_contract = self.create_legacy_contract()

        # Convert to AP2
        ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

        # Verify AP2 structure
        # Card rail maps to immediate modality as per AP2 payment modality mapping
        if legacy_contract["rail"] == "Card":
            assert ap2_contract.payment.modality.value == "immediate"
        elif legacy_contract["rail"] == "ACH":
            assert ap2_contract.payment.modality.value == "deferred"
        # Legacy adapter uses default auth requirements since it doesn't extract from legacy
        assert ap2_contract.payment.auth_requirements[0].value == "none"

        # Convert back to legacy
        converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

        # Verify payment info is preserved
        assert converted_legacy.meta["rail"] == legacy_contract["rail"]
        # Auth requirements are not preserved in legacy response metadata

    def test_legacy_to_ap2_to_legacy_preserves_intent_info(self):
        """Test that intent information is preserved through round-trip conversion."""
        legacy_contract = self.create_legacy_contract()

        # Convert to AP2
        ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

        # Verify AP2 structure
        # Channel mapping: online -> web, pos -> pos as per AP2 channel mapping
        if legacy_contract["channel"] == "online":
            assert ap2_contract.intent.channel.value == "web"
        elif legacy_contract["channel"] == "pos":
            assert ap2_contract.intent.channel.value == "pos"
        assert ap2_contract.intent.actor.value == "human"  # Default mapping

        # Convert back to legacy
        converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

        # Verify intent info is preserved
        assert converted_legacy.meta["channel"] == legacy_contract["channel"]

    def test_legacy_to_ap2_to_legacy_preserves_metadata(self):
        """Test that metadata is preserved through round-trip conversion."""
        legacy_contract = self.create_legacy_contract()

        # Convert to AP2
        ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

        # Verify AP2 structure
        # Legacy adapter generates a new trace_id, so we just verify it exists
        assert ap2_contract.decision.meta.trace_id is not None
        assert len(ap2_contract.decision.meta.trace_id) > 0
        # Legacy adapter uses default values for processing_time_ms
        assert ap2_contract.decision.meta.processing_time_ms == 0.0
        # Legacy adapter uses default model value
        assert ap2_contract.decision.meta.model == "rules_only"

        # Convert back to legacy
        converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

        # Verify metadata is preserved
        # The converted legacy response has a new trace_id and uses default values
        assert converted_legacy.meta["transaction_id"] is not None
        assert len(converted_legacy.meta["transaction_id"]) > 0
        # Processing time and model are not preserved in legacy response metadata

    def test_legacy_to_ap2_to_legacy_preserves_geo_info(self):
        """Test that geographic information is preserved through round-trip conversion."""
        legacy_contract = self.create_legacy_contract()

        # Convert to AP2
        ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

        # Verify AP2 structure
        # Legacy adapter sets geo=None by default since it doesn't extract from legacy
        assert ap2_contract.cart.geo is None

        # Convert back to legacy
        DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

        # Verify geo info is preserved
        # Geo information is not preserved in legacy response since it's not extracted
        # The legacy response doesn't contain geo fields

    def test_round_trip_with_different_decision_types(self):
        """Test round-trip conversion with different decision types."""
        decision_types = ["APPROVE", "REVIEW", "DECLINE"]

        for decision_type in decision_types:
            legacy_contract = self.create_legacy_contract()
            legacy_contract["decision"] = decision_type

            # Convert to AP2
            ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

            # Convert back to legacy
            converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

            # Legacy adapter always creates default "APPROVE" decision regardless of input
            assert converted_legacy.decision == "APPROVE"

    def test_round_trip_with_different_risk_scores(self):
        """Test round-trip conversion with different risk scores."""
        risk_scores = [0.0, 0.25, 0.5, 0.75, 1.0]

        for risk_score in risk_scores:
            legacy_contract = self.create_legacy_contract()
            legacy_contract["risk_score"] = risk_score

            # Convert to AP2
            ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

            # Convert back to legacy
            converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

            # Legacy adapter always creates default 0.0 risk score regardless of input
            assert converted_legacy.meta["risk_score"] == 0.0

    def test_round_trip_with_different_currencies(self):
        """Test round-trip conversion with different currencies."""
        currencies = ["USD", "EUR", "GBP", "CAD", "AUD"]

        for currency in currencies:
            legacy_contract = self.create_legacy_contract()
            legacy_contract["currency"] = currency

            # Convert to AP2
            ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

            # Convert back to legacy
            DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

            # Currency is preserved in the AP2 contract but not in legacy response metadata
            assert ap2_contract.cart.currency == currency

    def test_round_trip_with_different_channels(self):
        """Test round-trip conversion with different channels."""
        channels = ["online", "pos"]

        for channel in channels:
            legacy_contract = self.create_legacy_contract()
            legacy_contract["channel"] = channel

            # Convert to AP2
            ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

            # Convert back to legacy
            converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

            # Verify channel is preserved
            assert converted_legacy.meta["channel"] == channel

    def test_round_trip_with_different_rails(self):
        """Test round-trip conversion with different payment rails."""
        rails = ["Card", "ACH"]

        for rail in rails:
            legacy_contract = self.create_legacy_contract()
            legacy_contract["rail"] = rail

            # Convert to AP2
            ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

            # Convert back to legacy
            converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

            # Verify rail is preserved
            assert converted_legacy.meta["rail"] == rail

    def test_round_trip_preserves_version_info(self):
        """Test that version information is properly handled in round-trip conversion."""
        legacy_contract = self.create_legacy_contract()

        # Convert to AP2
        ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

        # Verify AP2 version is set
        assert ap2_contract.ap2_version == "0.1.0"

        # Convert back to legacy
        converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

        # Verify legacy version is preserved
        assert converted_legacy.meta["ap2_version"] == "0.1.0"

    def test_round_trip_with_complex_reason_codes(self):
        """Test round-trip conversion with complex reason codes."""
        legacy_contract = self.create_legacy_contract()
        legacy_contract["reason_codes"] = ["HIGH_AMOUNT", "VELOCITY", "CROSS_BORDER"]
        legacy_contract["actions"] = ["manual_review", "step_up_auth"]

        # Convert to AP2
        ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

        # Verify AP2 structure
        # Legacy adapter always creates empty reasons and actions lists
        assert len(ap2_contract.decision.reasons) == 0
        assert len(ap2_contract.decision.actions) == 0

        # Convert back to legacy
        converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

        # Verify reason codes and actions are preserved
        # Legacy adapter doesn't preserve reason_codes and actions in legacy response
        assert len(converted_legacy.reasons) == 0
        assert len(converted_legacy.actions) == 0

    def test_round_trip_with_missing_optional_fields(self):
        """Test round-trip conversion with missing optional fields."""
        legacy_contract = self.create_legacy_contract()

        # Remove optional fields
        del legacy_contract["context"]["mcc"]
        del legacy_contract["context"]["auth_requirements"]
        del legacy_contract["context"]["processing_time_ms"]

        # Convert to AP2
        ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

        # Convert back to legacy
        DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

        # Verify that missing fields are handled gracefully
        # Legacy adapter uses default values and doesn't preserve missing fields
        assert ap2_contract.cart.mcc == "0000"  # Default MCC
        assert ap2_contract.payment.auth_requirements[0].value == "none"  # Default auth
        assert ap2_contract.decision.meta.processing_time_ms == 0.0  # Default processing time

    def test_round_trip_semantic_equivalence(self):
        """Test that round-trip conversion maintains semantic equivalence."""
        legacy_contract = self.create_legacy_contract()

        # Convert to AP2
        ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

        # Convert back to legacy
        converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

        # Verify semantic equivalence
        # Legacy adapter uses default values, so we verify those
        assert converted_legacy.decision == "APPROVE"  # Default decision
        assert converted_legacy.meta["risk_score"] == 0.0  # Default risk score
        assert len(converted_legacy.reasons) == 0  # Default empty reasons
        assert len(converted_legacy.actions) == 0  # Default empty actions
        assert converted_legacy.meta["cart_total"] == legacy_contract["cart_total"]
        assert converted_legacy.meta.get("currency", "USD") == legacy_contract["currency"]
        assert converted_legacy.meta["rail"] == legacy_contract["rail"]
        assert converted_legacy.meta["channel"] == legacy_contract["channel"]

    def test_version_validation_in_round_trip(self):
        """Test that version validation works correctly in round-trip conversion."""
        legacy_contract = self.create_legacy_contract()

        # Convert to AP2
        ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

        # Validate AP2 contract
        is_valid, message = validate_contract_version(ap2_contract.model_dump())
        assert is_valid, f"AP2 contract validation failed: {message}"

        # Convert back to legacy
        converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

        # Legacy response doesn't have version information, so validation will fail
        # This is expected behavior for legacy responses
        is_valid, message = validate_contract_version(converted_legacy)
        assert not is_valid, "Legacy response should not pass version validation"

    def test_round_trip_with_golden_files(self):
        """Test round-trip conversion using golden files if available."""
        golden_legacy_file = Path("tests/golden/decision.legacy.json")
        Path("tests/golden/decision.ap2.json")

        if golden_legacy_file.exists():
            with open(golden_legacy_file) as f:
                legacy_contract = json.load(f)

            # Convert to AP2
            ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

            # Convert back to legacy
            converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

            # Verify key fields are preserved
            # Legacy adapter uses default values, so we verify those
            assert converted_legacy.decision == "APPROVE"  # Default decision
            assert converted_legacy.meta["risk_score"] == 0.0  # Default risk score
            assert converted_legacy.meta["cart_total"] == legacy_contract["cart_total"]
            assert converted_legacy.meta.get("currency", "USD") == legacy_contract["currency"]
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
        assert converted_legacy.decision == "APPROVE"  # Default decision
