"""Schema validation tests for Week 2 Rules + Rails rail and channel enums."""

import pytest
from pydantic import ValidationError

from orca_core.models import DecisionRequest, DecisionResponse


class TestRailChannelValidation:
    """Test rail and channel enum validation."""

    def test_valid_rail_values(self):
        """Test that valid rail values pass validation."""
        # Test Card rail
        request_card = DecisionRequest(cart_total=100.0, rail="Card", channel="online")
        assert request_card.rail == "Card"
        assert request_card.channel == "online"

        # Test ACH rail
        request_ach = DecisionRequest(cart_total=100.0, rail="ACH", channel="pos")
        assert request_ach.rail == "ACH"
        assert request_ach.channel == "pos"

    def test_valid_channel_values(self):
        """Test that valid channel values pass validation."""
        # Test online channel
        request_online = DecisionRequest(cart_total=100.0, rail="Card", channel="online")
        assert request_online.channel == "online"

        # Test pos channel
        request_pos = DecisionRequest(cart_total=100.0, rail="ACH", channel="pos")
        assert request_pos.channel == "pos"

    def test_invalid_rail_value(self):
        """Test that invalid rail values fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionRequest(cart_total=100.0, rail="InvalidRail", channel="online")
        assert "Input should be 'Card' or 'ACH'" in str(exc_info.value)

    def test_invalid_channel_value(self):
        """Test that invalid channel values fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            DecisionRequest(cart_total=100.0, rail="Card", channel="InvalidChannel")
        assert "Input should be 'online' or 'pos'" in str(exc_info.value)

    def test_missing_rail_field(self):
        """Test that missing rail field uses default value."""
        # With backward compatibility, missing rail field should use default "Card"
        request = DecisionRequest(
            cart_total=100.0,
            channel="online",
            # Missing rail field - should default to "Card"
        )
        assert request.rail == "Card"

    def test_missing_channel_field(self):
        """Test that missing channel field uses default value."""
        # With backward compatibility, missing channel field should use default "online"
        request = DecisionRequest(
            cart_total=100.0,
            rail="Card",
            # Missing channel field - should default to "online"
        )
        assert request.channel == "online"

    def test_response_rail_field(self):
        """Test that DecisionResponse can include rail field."""
        response = DecisionResponse(decision="APPROVE", rail="Card")
        assert response.rail == "Card"

        response_ach = DecisionResponse(decision="APPROVE", rail="ACH")
        assert response_ach.rail == "ACH"

    def test_response_rail_optional(self):
        """Test that DecisionResponse rail field is optional."""
        response = DecisionResponse(
            decision="APPROVE"
            # rail field not provided
        )
        assert response.rail is None

    def test_case_sensitivity(self):
        """Test that enum values are case-sensitive."""
        # These should fail due to case sensitivity
        with pytest.raises(ValidationError):
            DecisionRequest(
                cart_total=100.0,
                rail="card",  # lowercase
                channel="online",
            )

        with pytest.raises(ValidationError):
            DecisionRequest(
                cart_total=100.0,
                rail="Card",
                channel="ONLINE",  # uppercase
            )

    def test_all_combinations_valid(self):
        """Test all valid combinations of rail and channel."""
        combinations = [("Card", "online"), ("Card", "pos"), ("ACH", "online"), ("ACH", "pos")]

        for rail, channel in combinations:
            request = DecisionRequest(cart_total=100.0, rail=rail, channel=channel)
            assert request.rail == rail
            assert request.channel == channel
