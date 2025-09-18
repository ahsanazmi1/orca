"""Key management for Orca Core crypto operations.

This module handles loading and managing cryptographic keys for signing
decisions and generating receipt hashes.
"""

import base64
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


class KeyManager:
    """Manages cryptographic keys for Orca Core operations."""

    def __init__(self) -> None:
        """Initialize the key manager."""
        self._private_key: bytes | None = None
        self._public_key: bytes | None = None
        self._key_id: str | None = None

    def load_keys_from_env(self) -> bool:
        """
        Load keys from environment variables.

        Returns:
            True if keys loaded successfully, False otherwise
        """
        try:
            # Load private key from environment
            private_key_pem = os.getenv("ORCA_PRIVATE_KEY")
            if not private_key_pem:
                return False

            # Load public key from environment
            public_key_pem = os.getenv("ORCA_PUBLIC_KEY")
            if not public_key_pem:
                return False

            # Load key ID from environment
            key_id = os.getenv("ORCA_KEY_ID", "orca-default-key")

            # Parse and store keys
            self._private_key = private_key_pem.encode("utf-8")
            self._public_key = public_key_pem.encode("utf-8")
            self._key_id = key_id

            return True

        except Exception as e:
            print(f"Failed to load keys from environment: {e}")
            return False

    def load_test_keys(self) -> bool:
        """
        Load test keys for development and testing.

        Returns:
            True if test keys loaded successfully, False otherwise
        """
        try:
            # Generate test Ed25519 key pair
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key()

            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )

            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )

            # Store keys
            self._private_key = private_pem
            self._public_key = public_pem
            self._key_id = "orca-test-key"

            return True

        except Exception as e:
            print(f"Failed to generate test keys: {e}")
            return False

    def get_private_key(self) -> bytes | None:
        """
        Get the private key.

        Returns:
            Private key bytes or None if not loaded
        """
        return self._private_key

    def get_public_key(self) -> bytes | None:
        """
        Get the public key.

        Returns:
            Public key bytes or None if not loaded
        """
        return self._public_key

    def get_key_id(self) -> str | None:
        """
        Get the key ID.

        Returns:
            Key ID or None if not loaded
        """
        return self._key_id

    def is_loaded(self) -> bool:
        """
        Check if keys are loaded.

        Returns:
            True if keys are loaded, False otherwise
        """
        return self._private_key is not None and self._public_key is not None

    def get_public_key_fingerprint(self) -> str | None:
        """
        Get the public key fingerprint.

        Returns:
            Public key fingerprint or None if not loaded
        """
        if not self._public_key:
            return None

        try:
            # Parse public key
            public_key = serialization.load_pem_public_key(
                self._public_key, backend=default_backend()
            )

            # Get public key bytes
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )

            # Calculate SHA-256 fingerprint
            digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
            digest.update(public_bytes)
            fingerprint = digest.finalize()

            # Return base64-encoded fingerprint
            return base64.b64encode(fingerprint).decode("ascii")

        except Exception as e:
            print(f"Failed to calculate key fingerprint: {e}")
            return None


# Global key manager instance
_key_manager: KeyManager | None = None


def get_key_manager() -> KeyManager:
    """Get the global key manager instance."""
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyManager()
    return _key_manager


def initialize_keys() -> bool:
    """
    Initialize keys from environment or use test keys.

    Returns:
        True if keys initialized successfully, False otherwise
    """
    key_manager = get_key_manager()

    # Try to load from environment first
    if key_manager.load_keys_from_env():
        return True

    # Fall back to test keys
    if key_manager.load_test_keys():
        print("Warning: Using test keys for development")
        return True

    return False


def get_test_keypair() -> tuple[bytes, bytes]:
    """
    Generate a test keypair for deterministic testing.

    Returns:
        Tuple of (private_key_pem, public_key_pem)
    """
    # Generate Ed25519 key pair
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    # Serialize keys
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return private_pem, public_pem
