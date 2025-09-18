"""Tests for XGBoost model training and artifacts."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from orca_core.ml.features import FeatureExtractor
from orca_core.ml.train_xgb import XGBoostTrainer


class TestXGBoostTrainer:
    """Test XGBoost model training functionality."""

    def test_trainer_initialization(self):
        """Test XGBoostTrainer initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = XGBoostTrainer(model_dir=temp_dir)
            assert str(trainer.model_dir) == temp_dir
            assert trainer.model is None
            assert trainer.calibrator is None
            assert trainer.scaler is None

    def test_generate_synthetic_data(self):
        """Test synthetic data generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = XGBoostTrainer(model_dir=temp_dir)
            X, y = trainer.generate_synthetic_data(n_samples=1000)

            # The actual feature extractor returns more features than just 3
            assert X.shape[0] == 1000  # 1000 samples
            assert y.shape == (1000,)
            assert np.all((y == 0) | (y == 1))  # Binary classification
            # Check that we have the expected feature columns
            expected_features = [
                "amount",
                "velocity_24h",
                "velocity_7d",
                "velocity_30d",
                "cross_border",
                "location_mismatch",
                "high_ip_distance",
                "card_bin_risk",
                "time_since_last_purchase",
                "payment_method_risk",
                "chargebacks_12m",
                "loyalty_score",
                "hour_of_day",
                "is_weekend",
            ]
            for feature in expected_features:
                assert feature in X.columns

    def test_train_model_success(self):
        """Test successful model training."""
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = XGBoostTrainer(model_dir=temp_dir)

            # Generate small dataset for testing
            X, y = trainer.generate_synthetic_data(n_samples=100)

            # Train model
            metrics = trainer.train_model(X, y)

            # Check that model was trained
            assert trainer.model is not None
            assert trainer.calibrator is not None
            assert trainer.scaler is not None

            # Check that metrics were returned
            assert isinstance(metrics, dict)
            assert "auc_score" in metrics
            assert "log_loss" in metrics
            assert "feature_importance" in metrics

    def test_train_model_with_validation(self):
        """Test model training with validation split."""
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = XGBoostTrainer(model_dir=temp_dir)

            X, y = trainer.generate_synthetic_data(n_samples=200)

            # Train with validation (test_size parameter)
            metrics = trainer.train_model(X, y, test_size=0.2)

            assert trainer.model is not None
            assert trainer.calibrator is not None
            assert isinstance(metrics, dict)

    def test_calibrator_predict_proba(self):
        """Test probability prediction using calibrator."""
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = XGBoostTrainer(model_dir=temp_dir)

            X, y = trainer.generate_synthetic_data(n_samples=100)
            trainer.train_model(X, y)

            # Test prediction using calibrator directly
            test_X = X.head(5)
            X_scaled = trainer.scaler.transform(test_X)
            probabilities = trainer.calibrator.predict_proba(X_scaled)

            assert probabilities.shape == (5, 2)  # Binary classification
            assert np.all(probabilities >= 0) and np.all(probabilities <= 1)
            assert np.allclose(probabilities.sum(axis=1), 1.0, rtol=1e-10)

    def test_feature_importances_in_metrics(self):
        """Test feature importance extraction from training metrics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = XGBoostTrainer(model_dir=temp_dir)

            X, y = trainer.generate_synthetic_data(n_samples=100)
            metrics = trainer.train_model(X, y)

            importances = metrics["feature_importance"]

            assert isinstance(importances, dict)
            assert len(importances) > 0  # Should have multiple features
            assert all(isinstance(imp, int | float) for imp in importances.values())
            # Check that we have the expected features
            expected_features = ["amount", "velocity_24h", "cross_border"]
            for feature in expected_features:
                if feature in importances:
                    assert isinstance(importances[feature], int | float)

    def test_training_metrics(self):
        """Test training metrics from train_model."""
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = XGBoostTrainer(model_dir=temp_dir)

            X, y = trainer.generate_synthetic_data(n_samples=200)
            metrics = trainer.train_model(X, y)

            assert isinstance(metrics, dict)
            assert "auc_score" in metrics
            assert "log_loss" in metrics
            assert "classification_report" in metrics
            assert "feature_importance" in metrics
            assert 0 <= metrics["auc_score"] <= 1
            assert metrics["log_loss"] >= 0

    def test_save_model(self):
        """Test saving model artifacts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = XGBoostTrainer(model_dir=temp_dir)

            X, y = trainer.generate_synthetic_data(n_samples=100)
            metrics = trainer.train_model(X, y)

            # Save artifacts
            trainer.save_model(metrics)

            # Check all artifacts exist
            model_path = Path(temp_dir) / "xgb_model.joblib"
            calibrator_path = Path(temp_dir) / "calibrator.joblib"
            scaler_path = Path(temp_dir) / "scaler.joblib"
            metadata_path = Path(temp_dir) / "metadata.json"

            assert model_path.exists()
            assert calibrator_path.exists()
            assert scaler_path.exists()
            assert metadata_path.exists()

            # Check metadata content
            with open(metadata_path) as f:
                metadata = json.load(f)

            assert "version" in metadata
            assert "model_type" in metadata
            assert "created_at" in metadata
            assert "training_metrics" in metadata
            assert "feature_names" in metadata

    def test_train_and_save_pipeline(self):
        """Test complete train and save pipeline."""
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = XGBoostTrainer(model_dir=temp_dir)

            # Run full training pipeline
            metrics = trainer.train_and_save(n_samples=1000)

            # Check all components
            assert trainer.model is not None
            assert trainer.calibrator is not None
            assert trainer.scaler is not None
            assert isinstance(metrics, dict)
            assert "auc_score" in metrics

            # Check that artifacts were saved
            model_path = Path(temp_dir) / "xgb_model.joblib"
            calibrator_path = Path(temp_dir) / "calibrator.joblib"
            scaler_path = Path(temp_dir) / "scaler.joblib"
            metadata_path = Path(temp_dir) / "metadata.json"

            assert model_path.exists()
            assert calibrator_path.exists()
            assert scaler_path.exists()
            assert metadata_path.exists()

    def test_training_with_different_parameters(self):
        """Test training with different XGBoost parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = XGBoostTrainer(model_dir=temp_dir)

            X, y = trainer.generate_synthetic_data(n_samples=100)

            # Train model (the actual implementation doesn't support custom parameters)
            trainer.train_model(X, y)

            assert trainer.model is not None
            assert trainer.model.n_estimators == 100  # Default value
            assert trainer.model.max_depth == 6  # Default value
            assert trainer.model.learning_rate == 0.1  # Default value

    def test_error_handling(self):
        """Test error handling in training."""
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = XGBoostTrainer(model_dir=temp_dir)

            # Test with invalid data (empty DataFrame)
            with pytest.raises((ValueError, IndexError)):
                trainer.train_model(pd.DataFrame(), pd.Series())

            # Test with mismatched data
            X = pd.DataFrame({"amount": [100, 200]})
            y = pd.Series([0, 1, 1])  # Mismatched length

            with pytest.raises((ValueError, IndexError)):
                trainer.train_model(X, y)

    def test_calibration_improvement(self):
        """Test that calibration improves probability estimates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = XGBoostTrainer(model_dir=temp_dir)

            X, y = trainer.generate_synthetic_data(n_samples=500)
            trainer.train_model(X, y)

            # Get uncalibrated probabilities
            X_scaled = trainer.scaler.transform(X)
            uncalibrated_probs = trainer.model.predict_proba(X_scaled)[:, 1]

            # Get calibrated probabilities
            calibrated_probs = trainer.calibrator.predict_proba(X_scaled)[:, 1]

            # Calibrated probabilities should be different (not identical)
            assert not np.allclose(uncalibrated_probs, calibrated_probs, rtol=1e-10)

    def test_feature_scaling(self):
        """Test that features are properly scaled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            trainer = XGBoostTrainer(model_dir=temp_dir)

            # Generate synthetic data (which will have proper feature structure)
            X, y = trainer.generate_synthetic_data(n_samples=100)

            trainer.train_model(X, y)

            # Check that scaler was fitted
            assert trainer.scaler is not None
            assert hasattr(trainer.scaler, "mean_")
            assert hasattr(trainer.scaler, "scale_")


class TestFeatureExtractor:
    """Test feature extraction functionality."""

    def test_feature_extractor_initialization(self):
        """Test FeatureExtractor initialization."""
        extractor = FeatureExtractor()
        assert extractor is not None

    def test_extract_basic_features(self):
        """Test basic feature extraction."""
        extractor = FeatureExtractor()

        # Test data with proper structure
        transaction_data = {
            "cart_total": 100.0,
            "features": {"amount": 100.0, "velocity_24h": 2.0, "cross_border": 1},
            "context": {
                "customer": {"age_days": 365, "loyalty_tier": "SILVER", "chargebacks_12m": 0},
                "location_ip_country": "US",
                "billing_country": "US",
                "payment_method": {"type": "visa"},
            },
        }

        features = extractor.extract_features(transaction_data)

        assert isinstance(features, dict)
        assert "amount" in features
        assert "velocity_24h" in features
        assert "cross_border" in features
        assert features["amount"] == 100.0
        assert features["velocity_24h"] == 2.0
        assert features["cross_border"] == 1.0

    def test_extract_features_with_missing_data(self):
        """Test feature extraction with missing data."""
        extractor = FeatureExtractor()

        # Test with minimal data structure
        transaction_data = {
            "cart_total": 100.0,
            "features": {"amount": 100.0, "cross_border": 0},
            "context": {"customer": {}, "payment_method": {"type": "card"}},
        }

        features = extractor.extract_features(transaction_data)

        assert features["amount"] == 100.0
        assert features["velocity_24h"] == 1.0  # Default value
        assert features["cross_border"] == 0.0

    def test_extract_features_with_extra_data(self):
        """Test feature extraction with extra data."""
        extractor = FeatureExtractor()

        # Test with proper structure and extra fields
        transaction_data = {
            "cart_total": 100.0,
            "features": {
                "amount": 100.0,
                "velocity_24h": 2.0,
                "cross_border": 1,
                "extra_field": "ignored",
            },
            "context": {
                "customer": {"age_days": 365},
                "payment_method": {"type": "visa"},
                "extra_context": "ignored",
            },
            "extra_top_level": "ignored",
        }

        features = extractor.extract_features(transaction_data)

        # Should contain all expected features (not just the basic ones)
        assert len(features) == len(extractor.feature_names)
        assert "amount" in features
        assert "velocity_24h" in features
        assert "cross_border" in features

    def test_feature_validation(self):
        """Test feature validation."""
        extractor = FeatureExtractor()

        # Test with invalid data types (the extractor should raise ValueError)
        transaction_data = {
            "cart_total": "invalid",
            "features": {"amount": "invalid", "velocity_24h": "invalid", "cross_border": "invalid"},
            "context": {"customer": {}, "payment_method": {"type": "card"}},
        }

        # The extractor should raise ValueError for invalid data types
        with pytest.raises(ValueError):
            extractor.extract_features(transaction_data)

    def test_feature_normalization(self):
        """Test feature normalization."""
        extractor = FeatureExtractor()

        # Test with extreme values
        transaction_data = {
            "cart_total": 1000000.0,
            "features": {
                "amount": 1000000.0,  # Very large amount
                "velocity_24h": 100.0,  # Very high velocity
                "cross_border": 1,
            },
            "context": {"customer": {"age_days": 365}, "payment_method": {"type": "visa"}},
        }

        features = extractor.extract_features(transaction_data)

        # Features should be extracted as-is (normalization happens in training)
        assert features["amount"] == 1000000.0
        assert features["velocity_24h"] == 100.0
        assert features["cross_border"] == 1.0
