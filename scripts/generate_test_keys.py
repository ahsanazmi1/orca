"""Generate test cryptographic keys for local development.

This script generates Ed25519 key pairs for testing decision signing
and verifiable credentials in local development environments.

WARNING: These are TEST keys only. Never use for production.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


def generate_ed25519_keypair() -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """Generate a new Ed25519 key pair."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


def save_private_key(private_key: ed25519.Ed25519PrivateKey, file_path: Path) -> None:
    """Save private key to PEM file."""
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    with open(file_path, "wb") as f:
        f.write(pem)

    # Set restrictive permissions
    os.chmod(file_path, 0o600)


def save_public_key(public_key: ed25519.Ed25519PublicKey, file_path: Path) -> None:
    """Save public key to PEM file."""
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    with open(file_path, "wb") as f:
        f.write(pem)

    # Set restrictive permissions
    os.chmod(file_path, 0o644)


def get_key_fingerprint(public_key: ed25519.Ed25519PublicKey) -> str:
    """Generate a fingerprint for the public key."""
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )

    # Simple fingerprint using first 16 bytes
    fingerprint = public_bytes[:16].hex().upper()
    return f"{fingerprint[:8]}-{fingerprint[8:16]}-{fingerprint[16:24]}-{fingerprint[24:32]}"


def create_key_info(
    private_key: ed25519.Ed25519PrivateKey, public_key: ed25519.Ed25519PublicKey, key_id: str
) -> dict[str, Any]:
    """Create key metadata information."""
    fingerprint = get_key_fingerprint(public_key)

    return {
        "key_id": key_id,
        "algorithm": "Ed25519",
        "key_type": "signing",
        "fingerprint": fingerprint,
        "created_at": datetime.now().isoformat(),
        "environment": "development",
        "purpose": "test_decision_signing",
        "warning": "TEST KEY ONLY - DO NOT USE IN PRODUCTION",
        "public_key_info": {"format": "PEM", "encoding": "SubjectPublicKeyInfo"},
        "private_key_info": {"format": "PEM", "encoding": "PKCS8", "encryption": "none"},
    }


def main() -> bool:
    """Generate test keys for local development."""
    print("🔐 Generating test cryptographic keys for local development...")
    print("⚠️  WARNING: These are TEST keys only. Never use for production!")

    # Create keys directory
    keys_dir = Path("keys")
    keys_dir.mkdir(exist_ok=True)

    # Generate key pair
    print("\n1️⃣ Generating Ed25519 key pair...")
    private_key, public_key = generate_ed25519_keypair()

    # Create key ID
    key_id = f"test-key-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Save keys
    private_key_path = keys_dir / "test_signing_key.pem"
    public_key_path = keys_dir / "test_public_key.pem"
    key_info_path = keys_dir / "test_key_info.json"

    print(f"2️⃣ Saving private key to {private_key_path}...")
    save_private_key(private_key, private_key_path)

    print(f"3️⃣ Saving public key to {public_key_path}...")
    save_public_key(public_key, public_key_path)

    # Create key info
    print("4️⃣ Creating key metadata...")
    key_info = create_key_info(private_key, public_key, key_id)

    with open(key_info_path, "w") as f:
        json.dump(key_info, f, indent=2)

    # Display key information
    print("\n✅ Test keys generated successfully!")
    print(f"📁 Keys directory: {keys_dir.absolute()}")
    print(f"🔑 Key ID: {key_info['key_id']}")
    print(f"🔍 Fingerprint: {key_info['fingerprint']}")
    print(f"📄 Private key: {private_key_path}")
    print(f"📄 Public key: {public_key_path}")
    print(f"📄 Key info: {key_info_path}")

    # Display usage instructions
    print("\n📋 Usage Instructions:")
    print("1. Copy .env.example to .env:")
    print("   cp .env.example .env")
    print("\n2. Update .env with key path:")
    print("   ORCA_SIGNING_KEY_PATH=./keys/test_signing_key.pem")
    print("   ORCA_SIGN_DECISIONS=true")
    print("\n3. Test decision signing:")
    print("   python -m orca.cli decide-file samples/ap2/approve_card_low_risk.json")

    # Security warnings
    print("\n⚠️  Security Warnings:")
    print("• These are TEST keys only - never use in production")
    print("• Keep private key secure (permissions set to 600)")
    print("• Never commit keys to version control")
    print("• Rotate test keys regularly")
    print("• Use Azure Key Vault for production keys")

    # Verify key generation
    print("\n🔍 Verifying key generation...")
    try:
        # Test loading the private key
        with open(private_key_path, "rb") as f:
            loaded_private = serialization.load_pem_private_key(
                f.read(), password=None, backend=default_backend()
            )

        # Test loading the public key
        with open(public_key_path, "rb") as f:
            loaded_public = serialization.load_pem_public_key(f.read(), backend=default_backend())

        # Verify they match
        if loaded_private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        ) == loaded_public.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        ):
            print("✅ Key pair verification successful!")
        else:
            print("❌ Key pair verification failed!")
            return False

    except Exception as e:
        print(f"❌ Key verification failed: {e}")
        return False

    print("\n🎉 Test key generation completed successfully!")
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
