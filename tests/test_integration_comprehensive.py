"""Comprehensive integration tests for end-to-end workflows."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from orca_core.config import ORCA_DECISION_MODE, decision_mode, get_settings, is_ai_enabled
from orca_core.engine import evaluate_rules
from orca_core.llm.explain import get_llm_explainer
from orca_core.ml.features import FeatureExtractor
from orca_core.ml.model import predict_risk
from orca_core.ml.train_xgb import XGBoostTrainer
from orca_core.models import DecisionRequest, DecisionResponse


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_complete_decision_workflow_rules_only(self):
        """Test complete decision workflow in rules-only mode."""
        with patch.dict(os.environ, {"ORCA_DECISION_MODE": "RULES_ONLY"}):
            # Clear cache to ensure fresh settings
            get_settings.cache_clear()

            request = DecisionRequest(
                cart_total=100.0,
                currency="USD",
                rail="Card",
                channel="online",
                features={"amount": 100.0, "velocity_24h": 1.0, "cross_border": 0},
            )

            response = evaluate_rules(request)

            assert isinstance(response, DecisionResponse)
            assert response.decision in ["APPROVE", "DECLINE", "REVIEW"]
            assert isinstance(response.reasons, list)
            assert isinstance(response.actions, list)
            assert "meta" in response.model_dump()
            assert "risk_score" in response.meta

    def test_complete_decision_workflow_ai_mode(self):
        """Test complete decision workflow in AI mode."""
        with patch.dict(os.environ, {"ORCA_DECISION_MODE": "RULES_PLUS_AI"}):
            # Clear cache to ensure fresh settings
            get_settings.cache_clear()

            request = DecisionRequest(
                cart_total=100.0,
                currency="USD",
                rail="Card",
                channel="online",
                features={"amount": 100.0, "velocity_24h": 1.0, "cross_border": 0},
            )

            response = evaluate_rules(request)

            assert isinstance(response, DecisionResponse)
            assert response.decision in ["APPROVE", "DECLINE", "REVIEW"]
            assert "ai" in response.meta
            assert "risk_score" in response.meta["ai"]
            assert "reason_codes" in response.meta["ai"]
            assert "version" in response.meta["ai"]
            assert "model_type" in response.meta["ai"]

    def test_ml_model_integration_stub(self):
        """Test ML model integration with stub model."""
        with patch.dict(os.environ, {"ORCA_USE_XGB": "false"}):
            features = {"amount": 100.0, "velocity_24h": 1.0, "cross_border": 0}

            result = predict_risk(features)

            assert isinstance(result, dict)
            assert "risk_score" in result
            assert "reason_codes" in result
            assert "version" in result
            assert "model_type" in result
            assert result["model_type"] == "stub"
            assert 0 <= result["risk_score"] <= 1

    def test_ml_model_integration_xgb_fallback(self):
        """Test ML model integration with XGBoost fallback to stub."""
        with patch.dict(os.environ, {"ORCA_USE_XGB": "true"}):
            features = {"amount": 100.0, "velocity_24h": 1.0, "cross_border": 0}

            # XGBoost should fallback to stub when no model is available
            result = predict_risk(features)

            assert isinstance(result, dict)
            assert "risk_score" in result
            assert "reason_codes" in result
            assert "version" in result
            assert "model_type" in result
            assert 0 <= result["risk_score"] <= 1

    def test_llm_explanation_integration_configured(self):
        """Test LLM explanation integration when configured."""
        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
                "AZURE_OPENAI_API_KEY": "test-key",
                "AZURE_OPENAI_DEPLOYMENT": "gpt-4o-mini",
            },
        ):
            # Clear the singleton to force recreation with new env vars
            import orca_core.llm.explain as explain_module

            explain_module._explainer = None

            explainer = get_llm_explainer()

            # Should be configured with mock credentials
            assert explainer.is_configured()

            # Test explanation generation
            response = explainer.explain_decision(
                decision="APPROVE",
                risk_score=0.3,
                reason_codes=["LOW_RISK"],
                transaction_data={"amount": 100.0, "currency": "USD"},
                model_type="stub",
                model_version="0.1.0",
            )

            assert response is not None
            assert hasattr(response, "explanation")
            assert hasattr(response, "confidence")
            assert hasattr(response, "model_provenance")

    def test_llm_explanation_integration_not_configured(self):
        """Test LLM explanation integration when not configured."""
        # Clear environment variables
        env_vars = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT"]
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]

        # Clear the singleton to force recreation with cleared env vars
        import orca_core.llm.explain as explain_module

        explain_module._explainer = None

        explainer = get_llm_explainer()

        # Should not be configured
        assert not explainer.is_configured()

        # Test explanation generation (should return 503 response)
        response = explainer.explain_decision(
            decision="APPROVE",
            risk_score=0.3,
            reason_codes=["LOW_RISK"],
            transaction_data={"amount": 100.0, "currency": "USD"},
            model_type="stub",
            model_version="0.1.0",
        )

        assert response is not None
        assert response.model_provenance.get("status") == "503_service_unavailable"

    def test_feature_extraction_integration(self):
        """Test feature extraction integration."""
        extractor = FeatureExtractor()

        transaction_data = {"amount": 100.0, "velocity_24h": 2.0, "cross_border": 1}

        features = extractor.extract_features(transaction_data)

        assert isinstance(features, dict)
        assert "amount" in features
        assert "velocity_24h" in features
        assert "cross_border" in features

        # Test with ML model
        result = predict_risk(features)

        assert isinstance(result, dict)
        assert "risk_score" in result

    def test_xgb_training_integration(self):
        """Test XGBoost training integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = XGBoostTrainer(model_dir=temp_dir)

            # Generate synthetic data
            X, y = trainer.generate_synthetic_data(n_samples=100)

            # Train model
            metrics = trainer.train_model(X, y)

            # Save artifacts
            trainer.save_model(metrics)

            # Verify artifacts exist
            assert (Path(temp_dir) / "xgb_model.joblib").exists()
            assert (Path(temp_dir) / "calibrator.joblib").exists()
            assert (Path(temp_dir) / "scaler.joblib").exists()
            assert (Path(temp_dir) / "metadata.json").exists()

            # Test prediction using the same feature structure as training
            # Create test data with proper feature structure
            test_data = []
            for i in range(2):
                sample = {
                    "cart_total": 100.0 + i * 400.0,
                    "features": {
                        "amount": 100.0 + i * 400.0,
                        "velocity_24h": 1.0 + i * 2.0,
                        "cross_border": i,
                    },
                    "context": {
                        "customer": {"age_days": 365, "loyalty_tier": "SILVER"},
                        "payment_method": {"type": "visa"},
                    },
                }
                test_data.append(sample)

            # Extract features using the same extractor
            feature_extractor = FeatureExtractor()
            test_features_list = [feature_extractor.extract_features(data) for data in test_data]
            test_features_df = pd.DataFrame(test_features_list)

            # Use calibrator directly for prediction
            X_scaled = trainer.scaler.transform(test_features_df)
            probabilities = trainer.calibrator.predict_proba(X_scaled)
            assert probabilities.shape == (2, 2)
            assert np.all(probabilities >= 0) and np.all(probabilities <= 1)

    def test_configuration_management(self):
        """Test configuration management integration."""
        # Test default configuration
        settings = get_settings()
        assert settings is not None

        # Test decision mode
        mode = decision_mode()
        assert mode in [ORCA_DECISION_MODE.RULES_ONLY, ORCA_DECISION_MODE.RULES_PLUS_AI]

        # Test AI enabled check
        ai_enabled = is_ai_enabled()
        assert isinstance(ai_enabled, bool)

    def test_decision_engine_with_different_scenarios(self):
        """Test decision engine with different transaction scenarios."""
        scenarios = [
            {
                "name": "low_risk_approve",
                "request": DecisionRequest(
                    cart_total=100.0,
                    currency="USD",
                    rail="Card",
                    channel="online",
                    features={"amount": 100.0, "velocity_24h": 1.0, "cross_border": 0},
                ),
                "expected_decision": "APPROVE",
            },
            {
                "name": "high_ticket_review",
                "request": DecisionRequest(
                    cart_total=750.0,
                    currency="USD",
                    rail="Card",
                    channel="online",
                    features={"amount": 750.0, "velocity_24h": 1.0, "cross_border": 0},
                ),
                "expected_decision": "REVIEW",
            },
            {
                "name": "high_velocity_review",
                "request": DecisionRequest(
                    cart_total=100.0,
                    currency="USD",
                    rail="Card",
                    channel="online",
                    features={"amount": 100.0, "velocity_24h": 4.0, "cross_border": 0},
                ),
                "expected_decision": "REVIEW",
            },
        ]

        for scenario in scenarios:
            response = evaluate_rules(scenario["request"])

            assert isinstance(response, DecisionResponse)
            assert response.decision in ["APPROVE", "DECLINE", "REVIEW"]

            # Check that reasons are provided
            assert len(response.reasons) > 0
            assert len(response.actions) > 0

    def test_ml_model_consistency(self):
        """Test ML model consistency across multiple calls."""
        features = {"amount": 100.0, "velocity_24h": 1.0, "cross_border": 0}

        # Make multiple predictions
        results = []
        for _ in range(5):
            result = predict_risk(features)
            results.append(result)

        # All results should be identical (deterministic)
        for i in range(1, len(results)):
            assert results[i]["risk_score"] == results[0]["risk_score"]
            assert results[i]["reason_codes"] == results[0]["reason_codes"]
            assert results[i]["model_type"] == results[0]["model_type"]

    def test_error_handling_integration(self):
        """Test error handling across the system."""
        # Test with invalid request data
        with pytest.raises(Exception):
            invalid_request = DecisionRequest(
                cart_total="invalid",
                currency="USD",
                rail="Card",
                channel="online",  # Invalid type
            )
            evaluate_rules(invalid_request)

        # Test with missing features
        request = DecisionRequest(
            cart_total=100.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={},  # Empty features
        )

        # Should handle gracefully
        response = evaluate_rules(request)
        assert isinstance(response, DecisionResponse)

    def test_performance_integration(self):
        """Test performance across the system."""
        import time

        request = DecisionRequest(
            cart_total=100.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={"amount": 100.0, "velocity_24h": 1.0, "cross_border": 0},
        )

        # Measure decision time
        start_time = time.time()
        response = evaluate_rules(request)
        decision_time = time.time() - start_time

        # Decision should be fast (< 1 second)
        assert decision_time < 1.0
        assert isinstance(response, DecisionResponse)

    def test_memory_usage_integration(self):
        """Test memory usage across the system."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Process multiple requests
        for _ in range(100):
            request = DecisionRequest(
                cart_total=100.0,
                currency="USD",
                rail="Card",
                channel="online",
                features={"amount": 100.0, "velocity_24h": 1.0, "cross_border": 0},
            )
            response = evaluate_rules(request)
            assert isinstance(response, DecisionResponse)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (< 100MB)
        assert memory_increase < 100 * 1024 * 1024

    def test_concurrent_processing_integration(self):
        """Test concurrent processing capabilities."""
        import threading

        results = []
        errors = []

        def process_request():
            try:
                request = DecisionRequest(
                    cart_total=100.0,
                    currency="USD",
                    rail="Card",
                    channel="online",
                    features={"amount": 100.0, "velocity_24h": 1.0, "cross_border": 0},
                )
                response = evaluate_rules(request)
                results.append(response)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=process_request)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        assert len(results) == 10
        assert len(errors) == 0

        for result in results:
            assert isinstance(result, DecisionResponse)

    def test_data_validation_integration(self):
        """Test data validation across the system."""
        # Test valid data
        valid_request = DecisionRequest(
            cart_total=100.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={"amount": 100.0, "velocity_24h": 1.0, "cross_border": 0},
        )

        response = evaluate_rules(valid_request)
        assert isinstance(response, DecisionResponse)

        # Test edge cases
        edge_cases = [
            {
                "cart_total": 0.01,
                "currency": "USD",
                "rail": "Card",
                "channel": "online",
            },  # Minimum valid amount
            {"cart_total": 1000000.0, "currency": "USD", "rail": "Card", "channel": "online"},
            {"cart_total": 100.0, "currency": "EUR", "rail": "Card", "channel": "online"},
            {"cart_total": 100.0, "currency": "USD", "rail": "ACH", "channel": "online"},
        ]

        for case in edge_cases:
            request = DecisionRequest(**case)
            response = evaluate_rules(request)
            assert isinstance(response, DecisionResponse)

    def test_logging_integration(self):
        """Test logging integration across the system."""
        import logging

        # Set up logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("orca_core")

        # Process request (should generate logs)
        request = DecisionRequest(
            cart_total=100.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={"amount": 100.0, "velocity_24h": 1.0, "cross_border": 0},
        )

        response = evaluate_rules(request)
        assert isinstance(response, DecisionResponse)

        # Logs should be generated (we can't easily test this without capturing logs)

    def test_metadata_integration(self):
        """Test metadata integration across the system."""
        request = DecisionRequest(
            cart_total=100.0,
            currency="USD",
            rail="Card",
            channel="online",
            features={"amount": 100.0, "velocity_24h": 1.0, "cross_border": 0},
        )

        response = evaluate_rules(request)

        # Check metadata structure
        assert "meta" in response.model_dump()
        meta = response.meta

        # Should have risk score
        assert "risk_score" in meta

        # Should have rules evaluated
        assert "rules_evaluated" in meta

        # In AI mode, should have AI metadata
        if is_ai_enabled():
            assert "ai" in meta
            ai_meta = meta["ai"]
            assert "risk_score" in ai_meta
            assert "reason_codes" in ai_meta
            assert "version" in ai_meta
            assert "model_type" in ai_meta
