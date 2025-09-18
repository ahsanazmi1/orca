"""Receipt hashing functionality for Orca Core decisions.

This module provides receipt hashing for AP2 decision contracts to create
immutable audit trails without storing sensitive data.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any


class ReceiptHasher:
    """Creates receipt hashes for AP2 decision contracts."""

    def __init__(self) -> None:
        """Initialize the receipt hasher."""
        pass

    def make_receipt(self, decision_json: dict[str, Any]) -> str:
        """
        Create a receipt hash for a decision contract.

        Args:
            decision_json: AP2 decision contract as dictionary

        Returns:
            SHA-256 hash of the receipt
        """
        # Create receipt data (excluding sensitive fields)
        receipt_data = self._create_receipt_data(decision_json)

        # Create canonical JSON
        canonical_json = json.dumps(receipt_data, sort_keys=True, separators=(",", ":"))

        # Calculate SHA-256 hash
        receipt_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        return receipt_hash

    def _create_receipt_data(self, decision_json: dict[str, Any]) -> dict[str, Any]:
        """
        Create receipt data from decision contract, excluding sensitive fields.

        Args:
            decision_json: Decision contract data

        Returns:
            Receipt data dictionary
        """

        # Create a deep copy to avoid modifying original
        # Handle datetime, Decimal, and UUID serialization
        def json_serializer(obj: Any) -> Any:
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, "__class__") and obj.__class__.__name__ == "Decimal":
                return str(obj)
            elif hasattr(obj, "__class__") and obj.__class__.__name__ == "UUID":
                return str(obj)
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        receipt_data: dict[str, Any] = json.loads(
            json.dumps(decision_json, default=json_serializer)
        )

        # Remove sensitive fields from cart
        if "cart" in receipt_data:
            cart = receipt_data["cart"]
            if "items" in cart:
                # Keep only essential item information
                sanitized_items = []
                for item in cart["items"]:
                    sanitized_item = {
                        "id": item.get("id"),
                        "quantity": item.get("quantity"),
                        # Exclude unit_price and total_price for privacy
                    }
                    sanitized_items.append(sanitized_item)
                cart["items"] = sanitized_items

            # Keep amount but remove individual item prices
            if "amount" in cart:
                cart["amount"] = str(cart["amount"])  # Ensure string format

        # Remove sensitive fields from payment
        if "payment" in receipt_data:
            payment = receipt_data["payment"]
            # Remove instrument references
            payment.pop("instrument_ref", None)
            payment.pop("instrument_token", None)
            # Keep only modality and auth requirements
            payment = {
                "modality": payment.get("modality"),
                "auth_requirements": payment.get("auth_requirements", []),
            }
            receipt_data["payment"] = payment

        # Remove sensitive fields from intent
        if "intent" in receipt_data:
            intent = receipt_data["intent"]
            # Remove nonce for privacy
            intent.pop("nonce", None)
            # Keep only essential intent information
            intent = {
                "actor": intent.get("actor"),
                "intent_type": intent.get("intent_type"),
                "channel": intent.get("channel"),
                "agent_presence": intent.get("agent_presence"),
                "timestamps": intent.get("timestamps", {}),
            }
            receipt_data["intent"] = intent

        # Keep decision outcome but remove sensitive metadata
        if "decision" in receipt_data:
            decision = receipt_data["decision"]
            if "meta" in decision:
                meta = decision["meta"]
                # Keep only essential metadata
                meta = {
                    "model": meta.get("model"),
                    "version": meta.get("version"),
                    "processing_time_ms": meta.get("processing_time_ms"),
                }
                decision["meta"] = meta

        # Remove signing information (will be added after signing)
        receipt_data.pop("signing", None)

        # Remove top-level metadata that might contain sensitive info
        receipt_data.pop("metadata", None)

        # Add receipt metadata (without timestamp for determinism)
        receipt_data["receipt_metadata"] = {"version": "1.0.0", "hash_algorithm": "SHA-256"}

        return receipt_data

    def verify_receipt(self, decision_json: dict[str, Any], receipt_hash: str) -> bool:
        """
        Verify a receipt hash against a decision contract.

        Args:
            decision_json: Decision contract data
            receipt_hash: Receipt hash to verify

        Returns:
            True if receipt hash is valid, False otherwise
        """
        try:
            # Calculate expected hash
            expected_hash = self.make_receipt(decision_json)

            # Compare hashes
            return expected_hash == receipt_hash

        except Exception as e:
            print(f"Receipt verification failed: {e}")
            return False

    def create_receipt_summary(self, decision_json: dict[str, Any]) -> dict[str, Any]:
        """
        Create a summary of the decision for receipt purposes.

        Args:
            decision_json: Decision contract data

        Returns:
            Receipt summary dictionary
        """
        summary = {
            "timestamp": datetime.now(UTC).isoformat(),
            "ap2_version": decision_json.get("ap2_version"),
            "decision_result": decision_json.get("decision", {}).get("result"),
            "risk_score": decision_json.get("decision", {}).get("risk_score"),
            "cart_amount": decision_json.get("cart", {}).get("amount"),
            "cart_currency": decision_json.get("cart", {}).get("currency"),
            "payment_modality": decision_json.get("payment", {}).get("modality"),
            "intent_channel": decision_json.get("intent", {}).get("channel"),
            "reasons_count": len(decision_json.get("decision", {}).get("reasons", [])),
            "actions_count": len(decision_json.get("decision", {}).get("actions", [])),
        }

        return summary


# Global receipt hasher instance
_receipt_hasher: ReceiptHasher | None = None


def get_receipt_hasher() -> ReceiptHasher:
    """Get the global receipt hasher instance."""
    global _receipt_hasher
    if _receipt_hasher is None:
        _receipt_hasher = ReceiptHasher()
    return _receipt_hasher


def make_receipt(decision_json: dict[str, Any]) -> str:
    """
    Create a receipt hash for a decision contract.

    Args:
        decision_json: AP2 decision contract as dictionary

    Returns:
        SHA-256 hash of the receipt
    """
    hasher = get_receipt_hasher()
    return hasher.make_receipt(decision_json)
