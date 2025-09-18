"""Orca decision engine."""

from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class Decision:
    """Decision result from Orca engine."""

    decision: Literal["APPROVE", "DECLINE", "REVIEW"]
    risk_score: float
    reasons: list[str]
    actions: list[str]
    meta: dict[str, Any]


def decide(features: dict[str, Any]) -> Decision:
    """Make a decision based on input features."""

    # Simple rules engine for Phase 1
    amount = features.get("amount", 0)

    if amount < 100:
        return Decision(
            decision="APPROVE",
            risk_score=0.1,
            reasons=["low_amount"],
            actions=["ROUTE:PROCESSOR_A"],
            meta={
                "trace_id": features.get("trace_id", "unknown"),
                "routing_hint": "LOW_RISK_ROUTING",
                "explain": "Low amount transaction approved automatically",
            },
        )
    elif amount > 1000:
        return Decision(
            decision="REVIEW",
            risk_score=0.7,
            reasons=["high_amount"],
            actions=["STEP_UP:3DS"],
            meta={
                "trace_id": features.get("trace_id", "unknown"),
                "routing_hint": "HIGH_RISK_ROUTING",
                "explain": "High amount requires manual review",
            },
        )
    else:
        return Decision(
            decision="APPROVE",
            risk_score=0.3,
            reasons=["standard_amount"],
            actions=["ROUTE:PROCESSOR_A"],
            meta={
                "trace_id": features.get("trace_id", "unknown"),
                "routing_hint": "LOW_RISK_ROUTING",
                "explain": "Standard amount approved with standard routing",
            },
        )
