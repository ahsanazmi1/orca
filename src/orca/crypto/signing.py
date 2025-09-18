"""VC signing functionality for Orca Core decisions.

This module provides verifiable credential (VC) signing for AP2 decision contracts.
"""

import base64
import json
from datetime import UTC, datetime
from typing import Any

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from .keys import get_key_manager


class VCSigner:
    """Signs AP2 decision contracts with verifiable credentials."""

    def __init__(self) -> None:
        """Initialize the VC signer."""
        self.key_manager = get_key_manager()

    def sign_decision(self, decision_json: dict[str, Any]) -> dict[str, Any] | None:
        """
        Sign a decision contract with a verifiable credential proof.

        Args:
            decision_json: AP2 decision contract as dictionary

        Returns:
            VC proof dictionary or None if signing failed
        """
        if not self.key_manager.is_loaded():
            print("Warning: Keys not loaded, cannot sign decision")
            return None

        try:
            # Create the proof structure
            proof = self._create_proof(decision_json)

            # Sign the proof
            signature = self._sign_proof(proof)

            # Add signature to proof
            proof["proofValue"] = signature

            return proof

        except Exception as e:
            print(f"Failed to sign decision: {e}")
            return None

    def _create_proof(self, decision_json: dict[str, Any]) -> dict[str, Any]:
        """
        Create the proof structure for signing.

        Args:
            decision_json: Decision contract data

        Returns:
            Proof structure dictionary
        """
        # Get key information
        key_id = self.key_manager.get_key_id()
        public_key = self.key_manager.get_public_key()

        if not public_key:
            raise ValueError("Public key not available")

        # Calculate public key fingerprint
        fingerprint = self.key_manager.get_public_key_fingerprint()
        if not fingerprint:
            raise ValueError("Could not calculate key fingerprint")

        # Create proof structure
        proof = {
            "type": "Ed25519Signature2020",
            "created": datetime.now(UTC).isoformat(),
            "verificationMethod": f"{key_id}#{fingerprint}",
            "proofPurpose": "assertionMethod",
            "proofValue": "",  # Will be filled after signing
        }

        return proof

    def _sign_proof(self, proof: dict[str, Any]) -> str:
        """
        Sign the proof structure.

        Args:
            proof: Proof structure to sign

        Returns:
            Base64-encoded signature
        """
        private_key_pem = self.key_manager.get_private_key()
        if not private_key_pem:
            raise ValueError("Private key not available")

        # Parse private key
        private_key = serialization.load_pem_private_key(
            private_key_pem, password=None, backend=default_backend()
        )

        # Create canonical JSON for signing
        canonical_json = self._create_canonical_json(proof)

        # Sign the canonical JSON
        # For Ed25519 keys, we can sign directly
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        if isinstance(private_key, Ed25519PrivateKey):
            signature = private_key.sign(canonical_json.encode("utf-8"))
        else:
            raise ValueError(f"Unsupported key type: {type(private_key)}")

        # Return base64-encoded signature
        return base64.b64encode(signature).decode("ascii")

    def _create_canonical_json(self, proof: dict[str, Any]) -> str:
        """
        Create canonical JSON representation for signing.

        Args:
            proof: Proof structure

        Returns:
            Canonical JSON string
        """
        # Create a copy without the signature
        proof_copy = proof.copy()
        proof_copy.pop("proofValue", None)

        # Sort keys for canonical representation
        canonical = json.dumps(proof_copy, sort_keys=True, separators=(",", ":"))

        return canonical

    def verify_signature(self, decision_json: dict[str, Any], proof: dict[str, Any]) -> bool:
        """
        Verify a decision signature.

        Args:
            decision_json: Decision contract data
            proof: VC proof with signature

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Get public key
            public_key_pem = self.key_manager.get_public_key()
            if not public_key_pem:
                return False

            # Parse public key
            public_key = serialization.load_pem_public_key(
                public_key_pem, backend=default_backend()
            )

            # Get signature
            signature_b64 = proof.get("proofValue")
            if not signature_b64:
                return False

            # Decode signature
            signature = base64.b64decode(signature_b64)

            # Create canonical JSON for verification
            proof_copy = proof.copy()
            proof_copy.pop("proofValue", None)
            canonical_json = json.dumps(proof_copy, sort_keys=True, separators=(",", ":"))

            # Verify signature
            # For Ed25519 keys, we can verify directly
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

            if isinstance(public_key, Ed25519PublicKey):
                public_key.verify(signature, canonical_json.encode("utf-8"))
            else:
                raise ValueError(f"Unsupported key type: {type(public_key)}")

            return True

        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False


# Global VC signer instance
_vc_signer: VCSigner | None = None


def get_vc_signer() -> VCSigner:
    """Get the global VC signer instance."""
    global _vc_signer
    if _vc_signer is None:
        _vc_signer = VCSigner()
    return _vc_signer


def sign_decision(decision_json: dict[str, Any]) -> dict[str, Any] | None:
    """
    Sign a decision contract with VC proof.

    Args:
        decision_json: AP2 decision contract as dictionary

    Returns:
        VC proof dictionary or None if signing failed
    """
    signer = get_vc_signer()
    return signer.sign_decision(decision_json)
