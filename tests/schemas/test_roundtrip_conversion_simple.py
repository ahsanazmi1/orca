"""Simple round-trip conversion tests for legacy ↔ AP2 contracts."""

from typing import Any

from src.orca.core.decision_contract import AP2DecisionContract
from src.orca.core.decision_legacy_adapter import DecisionLegacyAdapter
from src.orca.core.versioning import get_version_manager, validate_contract_version


class TestSimpleRoundTripConversion:
    """Test simple round-trip conversion between legacy and AP2 formats."""

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

    def test_legacy_to_ap2_conversion(self):
        """Test that legacy contract converts to AP2 correctly."""
        legacy_contract = self.create_legacy_contract()

        # Convert to AP2
        ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

        # Verify AP2 structure
        assert isinstance(ap2_contract, AP2DecisionContract)
        assert ap2_contract.ap2_version == "0.1.0"
        assert ap2_contract.cart.amount == legacy_contract["cart_total"]
        assert ap2_contract.cart.currency == legacy_contract["currency"]
        # Card maps to IMMEDIATE, ACH maps to DEFERRED
        expected_modality = "immediate" if legacy_contract["rail"] == "Card" else "deferred"
        assert ap2_contract.payment.modality.value == expected_modality
        # online maps to web, pos maps to pos
        expected_channel = "web" if legacy_contract["channel"] == "online" else "pos"
        assert ap2_contract.intent.channel.value == expected_channel

    def test_ap2_to_legacy_conversion(self):
        """Test that AP2 contract converts to legacy correctly."""
        legacy_contract = self.create_legacy_contract()

        # Convert to AP2
        ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

        # Convert back to legacy
        converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

        # Verify legacy structure
        assert hasattr(converted_legacy, "decision")
        assert hasattr(converted_legacy, "reasons")
        assert hasattr(converted_legacy, "actions")
        assert hasattr(converted_legacy, "meta")
        assert converted_legacy.decision == "APPROVE"  # Default decision

    def test_round_trip_semantic_equivalence(self):
        """Test that round-trip conversion maintains semantic equivalence."""
        legacy_contract = self.create_legacy_contract()

        # Convert to AP2
        ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

        # Verify key fields are preserved in AP2
        assert ap2_contract.cart.amount == legacy_contract["cart_total"]
        assert ap2_contract.cart.currency == legacy_contract["currency"]
        # Card maps to IMMEDIATE, ACH maps to DEFERRED
        expected_modality = "immediate" if legacy_contract["rail"] == "Card" else "deferred"
        assert ap2_contract.payment.modality.value == expected_modality
        # online maps to web, pos maps to pos
        expected_channel = "web" if legacy_contract["channel"] == "online" else "pos"
        assert ap2_contract.intent.channel.value == expected_channel

        # Convert back to legacy
        converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

        # Verify semantic equivalence
        assert converted_legacy.decision == "APPROVE"
        assert isinstance(converted_legacy.reasons, list)
        assert isinstance(converted_legacy.actions, list)
        assert isinstance(converted_legacy.meta, dict)

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

        # Verify legacy response is valid
        assert converted_legacy.decision in ["APPROVE", "REVIEW", "DECLINE"]
        assert isinstance(converted_legacy.reasons, list)
        assert isinstance(converted_legacy.actions, list)

    def test_round_trip_with_different_rails(self):
        """Test round-trip conversion with different payment rails."""
        rails = ["Card", "ACH"]

        for rail in rails:
            legacy_contract = self.create_legacy_contract()
            legacy_contract["rail"] = rail

            # Convert to AP2
            ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

            # Verify rail is preserved (Card -> immediate, ACH -> deferred)
            expected_modality = "immediate" if rail == "Card" else "deferred"
            assert ap2_contract.payment.modality.value == expected_modality

            # Convert back to legacy
            converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

            # Verify response is valid
            assert converted_legacy.decision == "APPROVE"

    def test_round_trip_with_different_channels(self):
        """Test round-trip conversion with different channels."""
        channels = ["online", "pos"]

        for channel in channels:
            legacy_contract = self.create_legacy_contract()
            legacy_contract["channel"] = channel

            # Convert to AP2
            ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

            # Verify channel is preserved (online -> web, pos -> pos)
            expected_channel = "web" if channel == "online" else "pos"
            assert ap2_contract.intent.channel.value == expected_channel

            # Convert back to legacy
            converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

            # Verify response is valid
            assert converted_legacy.decision == "APPROVE"

    def test_round_trip_with_different_amounts(self):
        """Test round-trip conversion with different amounts."""
        amounts = [10.0, 100.0, 1000.0, 10000.0]

        for amount in amounts:
            legacy_contract = self.create_legacy_contract()
            legacy_contract["cart_total"] = amount

            # Convert to AP2
            ap2_contract = DecisionLegacyAdapter.legacy_request_to_ap2_contract(legacy_contract)

            # Verify amount is preserved
            assert ap2_contract.cart.amount == amount

            # Convert back to legacy
            converted_legacy = DecisionLegacyAdapter.ap2_contract_to_legacy_response(ap2_contract)

            # Verify response is valid
            assert converted_legacy.decision == "APPROVE"

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
        assert converted_legacy.decision == "APPROVE"
