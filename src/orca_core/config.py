"""
Orca Core Configuration Module

This module handles configuration management for the Orca decision engine,
including feature flags, environment variables, and Azure service settings.
"""

import os
from enum import Enum
from functools import lru_cache


class ORCA_DECISION_MODE(Enum):
    """Decision engine operational modes."""

    RULES_ONLY = "RULES_ONLY"
    RULES_PLUS_AI = "RULES_PLUS_AI"


class OrcaSettings:
    """Configuration settings for Orca Core."""

    def __init__(self) -> None:
        # Feature flags
        self.decision_mode = self._get_decision_mode()

        # Azure OpenAI Configuration
        self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

        # Orca Explanation Configuration
        self.explain_max_tokens = int(os.getenv("ORCA_EXPLAIN_MAX_TOKENS", "300"))
        self.explain_strict_json = os.getenv("ORCA_EXPLAIN_STRICT_JSON", "true").lower() == "true"
        self.explain_refuse_on_uncertainty = (
            os.getenv("ORCA_EXPLAIN_REFUSE_ON_UNCERTAINTY", "true").lower() == "true"
        )

        # Azure Infrastructure Configuration
        self.azure_subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        self.azure_resource_group = os.getenv("AZURE_RESOURCE_GROUP")
        self.azure_acr_name = os.getenv("AZURE_ACR_NAME")
        self.azure_aks_name = os.getenv("AZURE_AKS_NAME")
        self.azure_keyvault_name = os.getenv("AZURE_KEYVAULT_NAME")

        # Azure ML Configuration (from README)
        self.azure_ml_endpoint = os.getenv("AZURE_ML_ENDPOINT")
        self.azure_ml_key = os.getenv("AZURE_ML_KEY")
        self.azure_ml_model_name = os.getenv("AZURE_ML_MODEL_NAME", "orca-risk-model")

        # Debug UI Configuration
        self.debug_ui_enabled = os.getenv("DEBUG_UI_ENABLED", "false").lower() == "true"
        self.debug_ui_port = int(os.getenv("DEBUG_UI_PORT", "8501"))

        # XGBoost Configuration
        self.use_xgb = os.getenv("ORCA_USE_XGB", "false").lower() == "true"
        self.xgb_model_dir = os.getenv("ORCA_XGB_MODEL_DIR", "models")

    def _get_decision_mode(self) -> ORCA_DECISION_MODE:
        """Parse decision mode from environment variable."""
        mode_str = os.getenv("ORCA_MODE", "RULES_ONLY").upper()
        try:
            return ORCA_DECISION_MODE(mode_str)
        except ValueError:
            # Default to RULES_ONLY if invalid mode specified
            return ORCA_DECISION_MODE.RULES_ONLY

    @property
    def is_ai_enabled(self) -> bool:
        """Check if AI features are enabled."""
        return self.decision_mode == ORCA_DECISION_MODE.RULES_PLUS_AI

    @property
    def has_azure_openai_config(self) -> bool:
        """Check if Azure OpenAI is properly configured."""
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)

    @property
    def has_azure_ml_config(self) -> bool:
        """Check if Azure ML is properly configured."""
        return bool(self.azure_ml_endpoint and self.azure_ml_key)

    @property
    def has_xgb_config(self) -> bool:
        """Check if XGBoost model is available."""
        import os

        model_dir = os.path.join(self.xgb_model_dir)
        required_files = ["xgb_model.joblib", "calibrator.joblib", "scaler.joblib", "metadata.json"]
        return all(os.path.exists(os.path.join(model_dir, f)) for f in required_files)

    def validate_config(self) -> list[str]:
        """Validate configuration and return list of issues."""
        issues = []

        if self.is_ai_enabled:
            if not self.has_azure_openai_config:
                issues.append(
                    "Azure OpenAI configuration missing (AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY)"
                )

            if not self.has_azure_ml_config:
                issues.append("Azure ML configuration missing (AZURE_ML_ENDPOINT, AZURE_ML_KEY)")

        return issues


@lru_cache(maxsize=1)
def get_settings() -> OrcaSettings:
    """
    Get cached Orca settings instance.

    This function uses lru_cache to ensure settings are read only once at startup
    and cached for the lifetime of the application.

    Returns:
        OrcaSettings: Cached configuration instance
    """
    return OrcaSettings()


def decision_mode() -> ORCA_DECISION_MODE:
    """
    Get the current decision mode.

    Returns:
        ORCA_DECISION_MODE: Current operational mode
    """
    return get_settings().decision_mode


def is_ai_enabled() -> bool:
    """
    Check if AI features are enabled.

    Returns:
        bool: True if RULES_PLUS_AI mode is active
    """
    return get_settings().is_ai_enabled


def validate_configuration() -> list[str]:
    """
    Validate the current configuration.

    Returns:
        list[str]: List of configuration issues (empty if valid)
    """
    return get_settings().validate_config()


# Convenience functions for common configuration checks
def get_azure_openai_config() -> tuple[str | None, str | None, str]:
    """Get Azure OpenAI configuration."""
    settings = get_settings()
    return (
        settings.azure_openai_endpoint,
        settings.azure_openai_api_key,
        settings.azure_openai_deployment,
    )


def get_azure_ml_config() -> tuple[str | None, str | None, str]:
    """Get Azure ML configuration."""
    settings = get_settings()
    return (settings.azure_ml_endpoint, settings.azure_ml_key, settings.azure_ml_model_name)


def get_explanation_config() -> tuple[int, bool, bool]:
    """Get explanation configuration."""
    settings = get_settings()
    return (
        settings.explain_max_tokens,
        settings.explain_strict_json,
        settings.explain_refuse_on_uncertainty,
    )
