"""Versioning and Backward Compatibility for Orca Core.

This module provides versioning utilities for AP2 contracts and ML models,
ensuring backward compatibility and smooth migration paths.
"""

from typing import Any

from packaging import version

# Version constants
AP2_VERSION = "0.1.0"
ML_MODEL_VERSION = "1.0.0"  # Default model version
LEGACY_VERSION = "0.0.1"  # Legacy contract version

# Content type headers
AP2_CONTENT_TYPE = "application/vnd.ocn.ap2+json; version=1"
LEGACY_CONTENT_TYPE = "application/json"

# Feature flags
LEGACY_JSON_FLAG = "--legacy-json"
AP2_JSON_FLAG = "--ap2-json"


class VersionManager:
    """Manages versioning for AP2 contracts and ML models."""

    def __init__(self) -> None:
        """Initialize version manager."""
        self.ap2_version = AP2_VERSION
        self.ml_model_version = ML_MODEL_VERSION
        self.legacy_version = LEGACY_VERSION

    def get_ap2_version(self) -> str:
        """Get current AP2 version."""
        return self.ap2_version

    def get_ml_model_version(self) -> str:
        """Get current ML model version."""
        return self.ml_model_version

    def get_legacy_version(self) -> str:
        """Get legacy contract version."""
        return self.legacy_version

    def get_content_type(self, use_ap2: bool = True) -> str:
        """Get appropriate content type header.

        Args:
            use_ap2: Whether to use AP2 content type

        Returns:
            Content type string
        """
        return AP2_CONTENT_TYPE if use_ap2 else LEGACY_CONTENT_TYPE

    def is_ap2_compatible(self, version_str: str) -> bool:
        """Check if a version is AP2 compatible.

        Args:
            version_str: Version string to check

        Returns:
            True if AP2 compatible
        """
        try:
            v = version.parse(version_str)
            ap2_v = version.parse(self.ap2_version)
            return bool(v >= ap2_v)
        except version.InvalidVersion:
            return False

    def is_legacy_version(self, version_str: str) -> bool:
        """Check if a version is legacy.

        Args:
            version_str: Version string to check

        Returns:
            True if legacy version
        """
        try:
            v = version.parse(version_str)
            legacy_v = version.parse(self.legacy_version)
            return bool(v < legacy_v)
        except version.InvalidVersion:
            return True  # Assume legacy if can't parse

    def get_model_version_from_meta(self, model_meta: dict[str, Any]) -> str:
        """Extract model version from model metadata.

        Args:
            model_meta: Model metadata dictionary

        Returns:
            Model version string
        """
        return str(model_meta.get("model_version", self.ml_model_version))

    def create_version_info(
        self, contract_type: str = "ap2", model_meta: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create version information dictionary.

        Args:
            contract_type: Type of contract ("ap2" or "legacy")
            model_meta: Optional model metadata

        Returns:
            Version information dictionary
        """
        version_info = {
            "contract_version": self.ap2_version if contract_type == "ap2" else self.legacy_version,
            "contract_type": contract_type,
            "content_type": self.get_content_type(contract_type == "ap2"),
        }

        if model_meta:
            version_info["model_version"] = self.get_model_version_from_meta(model_meta)
            version_info["model_sha256"] = model_meta.get("model_sha256", "unknown")
            version_info["trained_on"] = model_meta.get("trained_on", "unknown")

        return version_info

    def validate_version_compatibility(
        self, input_version: str, target_version: str
    ) -> tuple[bool, str]:
        """Validate version compatibility.

        Args:
            input_version: Input version string
            target_version: Target version string

        Returns:
            Tuple of (is_compatible, message)
        """
        try:
            input_v = version.parse(input_version)
            target_v = version.parse(target_version)

            if input_v == target_v:
                return True, "Versions match exactly"
            elif input_v < target_v:
                return (
                    True,
                    f"Input version {input_version} is compatible with target {target_version}",
                )
            else:
                return False, f"Input version {input_version} is newer than target {target_version}"

        except version.InvalidVersion as e:
            return False, f"Invalid version format: {e}"

    def get_migration_path(self, from_version: str, to_version: str) -> str | None:
        """Get migration path between versions.

        Args:
            from_version: Source version
            to_version: Target version

        Returns:
            Migration path description or None
        """
        if self.is_legacy_version(from_version) and self.is_ap2_compatible(to_version):
            return "legacy_to_ap2"
        elif self.is_ap2_compatible(from_version) and self.is_legacy_version(to_version):
            return "ap2_to_legacy"
        elif from_version == to_version:
            return "no_migration"
        else:
            return "unknown_migration"

    def get_supported_versions(self) -> dict[str, Any]:
        """Get information about supported versions.

        Returns:
            Dictionary of supported versions and their capabilities
        """
        return {
            "ap2": {
                "version": self.ap2_version,
                "content_type": AP2_CONTENT_TYPE,
                "features": [
                    "structured_decision_contract",
                    "ap2_mandates",
                    "signing_and_receipts",
                    "shap_explanations",
                    "feature_drift_guard",
                ],
                "migration_from": ["legacy"],
            },
            "legacy": {
                "version": self.legacy_version,
                "content_type": LEGACY_CONTENT_TYPE,
                "features": [
                    "basic_decision_response",
                    "simple_reason_codes",
                    "fallback_compatibility",
                ],
                "migration_to": ["ap2"],
            },
            "ml_models": {
                "current_version": self.ml_model_version,
                "supported_versions": ["1.0.0"],
                "features": [
                    "xgboost_inference",
                    "calibrated_scores",
                    "shap_explanations",
                    "feature_drift_guard",
                ],
            },
        }


# Global version manager instance
_version_manager: VersionManager | None = None


def get_version_manager() -> VersionManager:
    """Get global version manager instance."""
    global _version_manager
    if _version_manager is None:
        _version_manager = VersionManager()
    return _version_manager


def get_ap2_version() -> str:
    """Get current AP2 version."""
    return get_version_manager().get_ap2_version()


def get_ml_model_version() -> str:
    """Get current ML model version."""
    return get_version_manager().get_ml_model_version()


def get_content_type(use_ap2: bool = True) -> str:
    """Get appropriate content type header."""
    return get_version_manager().get_content_type(use_ap2)


def is_ap2_compatible(version_str: str) -> bool:
    """Check if a version is AP2 compatible."""
    return get_version_manager().is_ap2_compatible(version_str)


def is_legacy_version(version_str: str) -> bool:
    """Check if a version is legacy."""
    return get_version_manager().is_legacy_version(version_str)


def create_version_info(
    contract_type: str = "ap2", model_meta: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Create version information dictionary."""
    return get_version_manager().create_version_info(contract_type, model_meta)


def get_migration_path(from_version: str, to_version: str) -> str | None:
    """Get migration path between versions."""
    return get_version_manager().get_migration_path(from_version, to_version)


def get_supported_versions() -> dict[str, Any]:
    """Get information about supported versions."""
    return get_version_manager().get_supported_versions()


def attach_model_version_to_decision_meta(
    decision_meta: dict[str, Any], model_meta: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Attach model version information to decision metadata.

    Args:
        decision_meta: Decision metadata dictionary
        model_meta: Optional model metadata

    Returns:
        Updated decision metadata with model version info
    """
    # Create a copy to avoid modifying the original
    updated_meta = decision_meta.copy()

    # Add model version information
    if model_meta:
        updated_meta["model_version"] = model_meta.get("model_version", get_ml_model_version())
        updated_meta["model_sha256"] = model_meta.get("model_sha256", "unknown")
        updated_meta["model_trained_on"] = model_meta.get("trained_on", "unknown")
    else:
        updated_meta["model_version"] = get_ml_model_version()

    # Add versioning info
    version_info = create_version_info("ap2", model_meta)
    updated_meta["version_info"] = version_info

    return updated_meta


def validate_contract_version(contract_data: dict[str, Any]) -> tuple[bool, str]:
    """Validate contract version compatibility.

    Args:
        contract_data: Contract data dictionary

    Returns:
        Tuple of (is_valid, message)
    """
    # Check for AP2 contract
    if "ap2_version" in contract_data:
        ap2_version = contract_data["ap2_version"]
        if is_ap2_compatible(ap2_version):
            return True, f"AP2 contract version {ap2_version} is compatible"
        else:
            return False, f"AP2 contract version {ap2_version} is not supported"

    # Check for legacy contract
    elif "version" in contract_data:
        legacy_version = contract_data["version"]
        if is_legacy_version(legacy_version):
            return True, f"Legacy contract version {legacy_version} is compatible"
        else:
            return False, f"Legacy contract version {legacy_version} is not supported"

    # No version information
    else:
        return False, "No version information found in contract"


def get_contract_type(contract_data: dict[str, Any]) -> str:
    """Determine contract type from contract data.

    Args:
        contract_data: Contract data dictionary

    Returns:
        Contract type ("ap2", "legacy", or "unknown")
    """
    if "ap2_version" in contract_data and "intent" in contract_data and "cart" in contract_data:
        return "ap2"
    elif "decision" in contract_data and "version" in contract_data:
        return "legacy"
    else:
        return "unknown"
