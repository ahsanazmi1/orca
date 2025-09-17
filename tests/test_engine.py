"""Tests for Orca engine."""

from orca.engine import decide


def test_low_amount_approves() -> None:
    """Test that low amounts are approved."""
    d = decide({"amount": 10})
    assert d.decision == "APPROVE"


def test_high_amount_review() -> None:
    """Test that high amounts require review."""
    d = decide({"amount": 1500})
    assert d.decision == "REVIEW"


def test_standard_amount_approves() -> None:
    """Test that standard amounts are approved."""
    d = decide({"amount": 500})
    assert d.decision == "APPROVE"
