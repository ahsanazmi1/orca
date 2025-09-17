"""Tests for Orca Core configuration module."""

import os
from unittest.mock import patch

from orca_core.config import (
    ORCA_DECISION_MODE,
    OrcaSettings,
    decision_mode,
    get_azure_ml_config,
    get_azure_openai_config,
    get_explanation_config,
    get_settings,
    is_ai_enabled,
    validate_configuration,
)


class TestOrcaSettings:
    """Test OrcaSettings class."""

    def test_default_settings(self):
        """Test default settings initialization."""
        with patch.dict(os.environ, {}, clear=True):
            settings = OrcaSettings()

            assert settings.decision_mode == ORCA_DECISION_MODE.RULES_ONLY
            assert settings.azure_openai_deployment == "gpt-4o-mini"
            assert settings.explain_max_tokens == 300
            assert settings.explain_strict_json is True
            assert settings.explain_refuse_on_uncertainty is True
            assert settings.debug_ui_enabled is False
            assert settings.debug_ui_port == 8501

    def test_environment_variable_parsing(self):
        """Test parsing of environment variables."""
        env_vars = {
            "ORCA_MODE": "RULES_PLUS_AI",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_OPENAI_DEPLOYMENT": "gpt-4",
            "ORCA_EXPLAIN_MAX_TOKENS": "500",
            "ORCA_EXPLAIN_STRICT_JSON": "false",
            "ORCA_EXPLAIN_REFUSE_ON_UNCERTAINTY": "false",
            "DEBUG_UI_ENABLED": "true",
            "DEBUG_UI_PORT": "8502",
            "AZURE_ML_ENDPOINT": "https://test-ml.azureml.net",
            "AZURE_ML_KEY": "ml-key",
            "AZURE_ML_MODEL_NAME": "test-model",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = OrcaSettings()

            assert settings.decision_mode == ORCA_DECISION_MODE.RULES_PLUS_AI
            assert settings.azure_openai_endpoint == "https://test.openai.azure.com"
            assert settings.azure_openai_api_key == "test-key"
            assert settings.azure_openai_deployment == "gpt-4"
            assert settings.explain_max_tokens == 500
            assert settings.explain_strict_json is False
            assert settings.explain_refuse_on_uncertainty is False
            assert settings.debug_ui_enabled is True
            assert settings.debug_ui_port == 8502
            assert settings.azure_ml_endpoint == "https://test-ml.azureml.net"
            assert settings.azure_ml_key == "ml-key"
            assert settings.azure_ml_model_name == "test-model"

    def test_invalid_decision_mode(self):
        """Test handling of invalid decision mode."""
        with patch.dict(os.environ, {"ORCA_MODE": "INVALID_MODE"}, clear=True):
            settings = OrcaSettings()
            # Should default to RULES_ONLY
            assert settings.decision_mode == ORCA_DECISION_MODE.RULES_ONLY

    def test_is_ai_enabled(self):
        """Test AI enabled check."""
        with patch.dict(os.environ, {"ORCA_MODE": "RULES_ONLY"}, clear=True):
            settings = OrcaSettings()
            assert settings.is_ai_enabled is False

        with patch.dict(os.environ, {"ORCA_MODE": "RULES_PLUS_AI"}, clear=True):
            settings = OrcaSettings()
            assert settings.is_ai_enabled is True

    def test_azure_config_checks(self):
        """Test Azure configuration validation."""
        # No config
        with patch.dict(os.environ, {}, clear=True):
            settings = OrcaSettings()
            assert settings.has_azure_openai_config is False
            assert settings.has_azure_ml_config is False

        # Partial OpenAI config
        with patch.dict(
            os.environ, {"AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com"}, clear=True
        ):
            settings = OrcaSettings()
            assert settings.has_azure_openai_config is False

        # Complete OpenAI config
        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_API_KEY": "test-key",
            },
            clear=True,
        ):
            settings = OrcaSettings()
            assert settings.has_azure_openai_config is True

        # Complete ML config
        with patch.dict(
            os.environ,
            {"AZURE_ML_ENDPOINT": "https://test-ml.azureml.net", "AZURE_ML_KEY": "ml-key"},
            clear=True,
        ):
            settings = OrcaSettings()
            assert settings.has_azure_ml_config is True

    def test_validate_config(self):
        """Test configuration validation."""
        # Valid RULES_ONLY config
        with patch.dict(os.environ, {"ORCA_MODE": "RULES_ONLY"}, clear=True):
            settings = OrcaSettings()
            issues = settings.validate_config()
            assert len(issues) == 0

        # Invalid RULES_PLUS_AI config (missing Azure services)
        with patch.dict(os.environ, {"ORCA_MODE": "RULES_PLUS_AI"}, clear=True):
            settings = OrcaSettings()
            issues = settings.validate_config()
            assert len(issues) == 2
            assert "Azure OpenAI configuration missing" in issues[0]
            assert "Azure ML configuration missing" in issues[1]

        # Valid RULES_PLUS_AI config
        with patch.dict(
            os.environ,
            {
                "ORCA_MODE": "RULES_PLUS_AI",
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_API_KEY": "test-key",
                "AZURE_ML_ENDPOINT": "https://test-ml.azureml.net",
                "AZURE_ML_KEY": "ml-key",
            },
            clear=True,
        ):
            settings = OrcaSettings()
            issues = settings.validate_config()
            assert len(issues) == 0


class TestConfigurationFunctions:
    """Test configuration helper functions."""

    def test_get_settings_caching(self):
        """Test that get_settings() returns cached instance."""
        with patch.dict(os.environ, {}, clear=True):
            settings1 = get_settings()
            settings2 = get_settings()
            assert settings1 is settings2

    def test_decision_mode_function(self):
        """Test decision_mode() function."""
        # Clear the cache to ensure fresh settings
        get_settings.cache_clear()

        with patch.dict(os.environ, {"ORCA_MODE": "RULES_PLUS_AI"}, clear=True):
            mode = decision_mode()
            assert mode == ORCA_DECISION_MODE.RULES_PLUS_AI

    def test_is_ai_enabled_function(self):
        """Test is_ai_enabled() function."""
        # Clear the cache to ensure fresh settings
        get_settings.cache_clear()

        with patch.dict(os.environ, {"ORCA_MODE": "RULES_ONLY"}, clear=True):
            assert is_ai_enabled() is False

        # Clear cache again for second test
        get_settings.cache_clear()

        with patch.dict(os.environ, {"ORCA_MODE": "RULES_PLUS_AI"}, clear=True):
            assert is_ai_enabled() is True

    def test_validate_configuration_function(self):
        """Test validate_configuration() function."""
        # Clear the cache to ensure fresh settings
        get_settings.cache_clear()

        with patch.dict(os.environ, {"ORCA_MODE": "RULES_ONLY"}, clear=True):
            issues = validate_configuration()
            assert len(issues) == 0

        # Clear cache again for second test
        get_settings.cache_clear()

        with patch.dict(os.environ, {"ORCA_MODE": "RULES_PLUS_AI"}, clear=True):
            issues = validate_configuration()
            assert len(issues) == 2

    def test_xgb_config_properties(self):
        """Test XGBoost configuration properties."""
        with patch.dict(os.environ, {}, clear=True):
            settings = OrcaSettings()
            assert settings.use_xgb is False
            assert settings.xgb_model_dir == "models"

        with patch.dict(
            os.environ, {"ORCA_USE_XGB": "true", "ORCA_XGB_MODEL_DIR": "custom_models"}, clear=True
        ):
            settings = OrcaSettings()
            assert settings.use_xgb is True
            assert settings.xgb_model_dir == "custom_models"

    @patch("os.path.exists")
    def test_has_xgb_config(self, mock_exists):
        """Test XGBoost model availability check."""
        with patch.dict(os.environ, {"ORCA_XGB_MODEL_DIR": "test_models"}, clear=True):
            settings = OrcaSettings()

            # All files exist
            mock_exists.return_value = True
            assert settings.has_xgb_config is True

            # Some files missing
            def side_effect(path):
                return not path.endswith("metadata.json")

            mock_exists.side_effect = side_effect
            assert settings.has_xgb_config is False

    def test_azure_infrastructure_config(self):
        """Test Azure infrastructure configuration."""
        env_vars = {
            "AZURE_SUBSCRIPTION_ID": "sub-123",
            "AZURE_RESOURCE_GROUP": "rg-test",
            "AZURE_ACR_NAME": "acr-test",
            "AZURE_AKS_NAME": "aks-test",
            "AZURE_KEYVAULT_NAME": "kv-test",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = OrcaSettings()
            assert settings.azure_subscription_id == "sub-123"
            assert settings.azure_resource_group == "rg-test"
            assert settings.azure_acr_name == "acr-test"
            assert settings.azure_aks_name == "aks-test"
            assert settings.azure_keyvault_name == "kv-test"

    def test_boolean_environment_parsing(self):
        """Test parsing of boolean environment variables."""
        # Test various boolean representations (only "true" is considered True)
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", False),  # "1" is not considered True in the implementation
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("", False),
        ]

        for value, expected in test_cases:
            with patch.dict(
                os.environ,
                {
                    "ORCA_EXPLAIN_STRICT_JSON": value,
                    "ORCA_EXPLAIN_REFUSE_ON_UNCERTAINTY": value,
                    "DEBUG_UI_ENABLED": value,
                    "ORCA_USE_XGB": value,
                },
                clear=True,
            ):
                settings = OrcaSettings()
                assert settings.explain_strict_json is expected
                assert settings.explain_refuse_on_uncertainty is expected
                assert settings.debug_ui_enabled is expected
                assert settings.use_xgb is expected

    def test_integer_environment_parsing(self):
        """Test parsing of integer environment variables."""
        with patch.dict(
            os.environ, {"ORCA_EXPLAIN_MAX_TOKENS": "500", "DEBUG_UI_PORT": "9000"}, clear=True
        ):
            settings = OrcaSettings()
            assert settings.explain_max_tokens == 500
            assert settings.debug_ui_port == 9000

    def test_default_values(self):
        """Test default values for optional environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            settings = OrcaSettings()
            assert settings.azure_openai_deployment == "gpt-4o-mini"
            assert settings.azure_ml_model_name == "orca-risk-model"
            assert settings.xgb_model_dir == "models"
            assert settings.debug_ui_port == 8501


class TestConfigurationHelperFunctions:
    """Test configuration helper functions."""

    def test_get_azure_openai_config(self):
        """Test get_azure_openai_config function."""
        # Clear the cache to ensure fresh settings
        get_settings.cache_clear()

        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_API_KEY": "test-key",
                "AZURE_OPENAI_DEPLOYMENT": "gpt-4",
            },
            clear=True,
        ):
            endpoint, api_key, deployment = get_azure_openai_config()
            assert endpoint == "https://test.openai.azure.com"
            assert api_key == "test-key"
            assert deployment == "gpt-4"

    def test_get_azure_ml_config(self):
        """Test get_azure_ml_config function."""
        # Clear the cache to ensure fresh settings
        get_settings.cache_clear()

        with patch.dict(
            os.environ,
            {
                "AZURE_ML_ENDPOINT": "https://test-ml.azureml.net",
                "AZURE_ML_KEY": "ml-key",
                "AZURE_ML_MODEL_NAME": "test-model",
            },
            clear=True,
        ):
            endpoint, api_key, model_name = get_azure_ml_config()
            assert endpoint == "https://test-ml.azureml.net"
            assert api_key == "ml-key"
            assert model_name == "test-model"

    def test_get_explanation_config(self):
        """Test get_explanation_config function."""
        # Clear the cache to ensure fresh settings
        get_settings.cache_clear()

        with patch.dict(
            os.environ,
            {
                "ORCA_EXPLAIN_MAX_TOKENS": "500",
                "ORCA_EXPLAIN_STRICT_JSON": "false",
                "ORCA_EXPLAIN_REFUSE_ON_UNCERTAINTY": "false",
            },
            clear=True,
        ):
            max_tokens, strict_json, refuse_uncertainty = get_explanation_config()
            assert max_tokens == 500
            assert strict_json is False
            assert refuse_uncertainty is False

    def test_get_azure_openai_config_none_values(self):
        """Test get_azure_openai_config with None values."""
        # Clear the cache to ensure fresh settings
        get_settings.cache_clear()

        with patch.dict(os.environ, {}, clear=True):
            endpoint, api_key, deployment = get_azure_openai_config()
            assert endpoint is None
            assert api_key is None
            assert deployment == "gpt-4o-mini"  # default value

    def test_get_azure_ml_config_none_values(self):
        """Test get_azure_ml_config with None values."""
        # Clear the cache to ensure fresh settings
        get_settings.cache_clear()

        with patch.dict(os.environ, {}, clear=True):
            endpoint, api_key, model_name = get_azure_ml_config()
            assert endpoint is None
            assert api_key is None
            assert model_name == "orca-risk-model"  # default value

    def test_get_explanation_config_defaults(self):
        """Test get_explanation_config with default values."""
        # Clear the cache to ensure fresh settings
        get_settings.cache_clear()

        with patch.dict(os.environ, {}, clear=True):
            max_tokens, strict_json, refuse_uncertainty = get_explanation_config()
            assert max_tokens == 300
            assert strict_json is True
            assert refuse_uncertainty is True
