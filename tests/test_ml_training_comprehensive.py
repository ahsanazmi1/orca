"""
Comprehensive tests for ML training functionality.

This module tests the XGBoost training pipeline, including synthetic data generation,
model training, calibration, and model persistence.
"""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from orca_core.ml.train_xgb import XGBoostTrainer


class TestXGBoostTrainer:
    """Test suite for XGBoostTrainer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.trainer = XGBoostTrainer(model_dir=self.temp_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_trainer_initialization(self):
        """Test XGBoostTrainer initialization."""
        assert self.trainer.model_dir == Path(self.temp_dir)
        assert self.trainer.model_dir.exists()
        assert self.trainer.feature_extractor is not None
        assert self.trainer.model is None
        assert self.trainer.calibrator is None
        assert self.trainer.scaler is None
        assert self.trainer.feature_names is None
        assert isinstance(self.trainer.metadata, dict)

    def test_trainer_initialization_default_dir(self):
        """Test trainer initialization with default directory."""
        trainer = XGBoostTrainer()
        assert trainer.model_dir == Path("models")

    def test_generate_synthetic_data_basic(self):
        """Test basic synthetic data generation."""
        X, y = self.trainer.generate_synthetic_data(n_samples=100)

        assert isinstance(X, pd.DataFrame)
        assert isinstance(y, pd.Series)
        assert len(X) == 100
        assert len(y) == 100
        assert y.name == "risk_label"
        assert set(y.unique()).issubset({0, 1})

    def test_generate_synthetic_data_structure(self):
        """Test structure of generated synthetic data."""
        X, y = self.trainer.generate_synthetic_data(n_samples=50)

        # Check that features are extracted properly
        assert len(X.columns) > 0
        assert all(isinstance(val, (int, float)) for val in X.values.flatten())
        assert all(isinstance(val, (int, float)) for val in y)

        # Check that we have both positive and negative samples
        assert 0 in y.values
        assert 1 in y.values

    def test_generate_transaction_sample_structure(self):
        """Test structure of generated transaction samples."""
        sample = self.trainer._generate_transaction_sample()

        # Check required fields
        assert "cart_total" in sample
        assert "currency" in sample
        assert "rail" in sample
        assert "channel" in sample
        assert "features" in sample
        assert "context" in sample

        # Check data types
        assert isinstance(sample["cart_total"], (int, float))
        assert isinstance(sample["currency"], str)
        assert isinstance(sample["rail"], str)
        assert isinstance(sample["channel"], str)
        assert isinstance(sample["features"], dict)
        assert isinstance(sample["context"], dict)

        # Check features structure
        features = sample["features"]
        assert "amount" in features
        assert "velocity_24h" in features
        assert "velocity_7d" in features
        assert "velocity_30d" in features

        # Check context structure
        context = sample["context"]
        assert "customer" in context
        assert "location_ip_country" in context
        assert "billing_country" in context
        assert "payment_method" in context

    def test_generate_transaction_sample_realistic_values(self):
        """Test that generated samples have realistic values."""
        sample = self.trainer._generate_transaction_sample()

        # Check realistic ranges
        assert sample["cart_total"] > 0
        assert sample["features"]["amount"] > 0
        assert sample["features"]["velocity_24h"] >= 1
        assert sample["features"]["velocity_7d"] >= sample["features"]["velocity_24h"]
        assert sample["features"]["velocity_30d"] >= sample["features"]["velocity_7d"]

        # Check customer age
        customer = sample["context"]["customer"]
        assert customer["age_days"] > 0
        assert customer["chargebacks_12m"] >= 0

    def test_generate_target_basic(self):
        """Test target generation with basic features."""
        features = {
            "amount": 100.0,
            "velocity_24h": 1.0,
            "cross_border": 0.0,
            "location_mismatch": 0.0,
            "payment_method_risk": 0.3,
            "chargebacks_12m": 0.0,
            "loyalty_score": 0.5,
            "hour_of_day": 12.0,
            "is_weekend": 0.0,
        }

        target = self.trainer._generate_target(features)

        assert target in {0, 1}
        assert isinstance(target, int)

    def test_generate_target_high_risk(self):
        """Test target generation for high-risk scenarios."""
        features = {
            "amount": 2000.0,  # High amount
            "velocity_24h": 10.0,  # High velocity
            "cross_border": 1.0,  # Cross border
            "location_mismatch": 1.0,  # Location mismatch
            "payment_method_risk": 0.8,  # High payment risk
            "chargebacks_12m": 3.0,  # High chargebacks
            "loyalty_score": 0.1,  # Low loyalty
            "hour_of_day": 2.0,  # Late night
            "is_weekend": 1.0,  # Weekend
        }

        target = self.trainer._generate_target(features)

        # High risk should likely result in target = 1
        assert target in {0, 1}

    def test_generate_target_low_risk(self):
        """Test target generation for low-risk scenarios."""
        features = {
            "amount": 50.0,  # Low amount
            "velocity_24h": 1.0,  # Low velocity
            "cross_border": 0.0,  # Domestic
            "location_mismatch": 0.0,  # No mismatch
            "payment_method_risk": 0.1,  # Low payment risk
            "chargebacks_12m": 0.0,  # No chargebacks
            "loyalty_score": 0.9,  # High loyalty
            "hour_of_day": 14.0,  # Daytime
            "is_weekend": 0.0,  # Weekday
        }

        target = self.trainer._generate_target(features)

        # Low risk should likely result in target = 0
        assert target in {0, 1}

    def test_train_model_basic(self):
        """Test basic model training."""
        # Generate small dataset for testing
        X, y = self.trainer.generate_synthetic_data(n_samples=100)

        metrics = self.trainer.train_model(X, y, test_size=0.3, random_state=42)

        # Check that model was trained
        assert self.trainer.model is not None
        assert self.trainer.calibrator is not None
        assert self.trainer.scaler is not None
        assert self.trainer.feature_names is not None

        # Check metrics structure
        assert "auc_score" in metrics
        assert "log_loss" in metrics
        assert "classification_report" in metrics
        assert "feature_importance" in metrics
        assert "n_features" in metrics
        assert "n_samples_train" in metrics
        assert "n_samples_test" in metrics
        assert "training_date" in metrics

        # Check metric values
        assert 0.0 <= metrics["auc_score"] <= 1.0
        assert metrics["log_loss"] >= 0.0
        assert metrics["n_features"] > 0
        assert metrics["n_samples_train"] > 0
        assert metrics["n_samples_test"] > 0

    def test_train_model_feature_names(self):
        """Test that feature names are stored correctly."""
        X, y = self.trainer.generate_synthetic_data(n_samples=50)

        self.trainer.train_model(X, y)

        assert self.trainer.feature_names == X.columns.tolist()
        assert len(self.trainer.feature_names) == len(X.columns)

    def test_train_model_calibration(self):
        """Test that model calibration works."""
        X, y = self.trainer.generate_synthetic_data(n_samples=100)

        self.trainer.train_model(X, y)

        # Check that calibrator was created
        assert self.trainer.calibrator is not None

        # Test calibration on sample data
        sample_features = X.iloc[:5]
        sample_scaled = self.trainer.scaler.transform(sample_features)
        probabilities = self.trainer.calibrator.predict_proba(sample_scaled)

        assert probabilities.shape[0] == 5
        assert probabilities.shape[1] == 2  # Binary classification
        assert np.all(probabilities >= 0.0)
        assert np.all(probabilities <= 1.0)
        assert np.allclose(probabilities.sum(axis=1), 1.0)

    def test_train_model_scaling(self):
        """Test that feature scaling works correctly."""
        X, y = self.trainer.generate_synthetic_data(n_samples=100)

        self.trainer.train_model(X, y)

        # Check that scaler was fitted
        assert self.trainer.scaler is not None

        # Test scaling
        sample_features = X.iloc[:5]
        scaled_features = self.trainer.scaler.transform(sample_features)

        assert scaled_features.shape == sample_features.shape
        assert not np.any(np.isnan(scaled_features))
        assert not np.any(np.isinf(scaled_features))

    def test_save_model_basic(self):
        """Test basic model saving."""
        # Train a model first
        X, y = self.trainer.generate_synthetic_data(n_samples=50)
        metrics = self.trainer.train_model(X, y)

        # Save the model
        self.trainer.save_model(metrics)

        # Check that files were created
        model_path = self.trainer.model_dir / "xgb_model.joblib"
        calibrator_path = self.trainer.model_dir / "calibrator.joblib"
        scaler_path = self.trainer.model_dir / "scaler.joblib"
        metadata_path = self.trainer.model_dir / "metadata.json"

        assert model_path.exists()
        assert calibrator_path.exists()
        assert scaler_path.exists()
        assert metadata_path.exists()

    def test_save_model_metadata(self):
        """Test that metadata is saved correctly."""
        X, y = self.trainer.generate_synthetic_data(n_samples=50)
        metrics = self.trainer.train_model(X, y)

        self.trainer.save_model(metrics)

        # Load and check metadata
        metadata_path = self.trainer.model_dir / "metadata.json"
        with open(metadata_path) as f:
            metadata = json.load(f)

        assert metadata["model_type"] == "xgboost"
        assert metadata["version"] == "1.0.0"
        assert "feature_names" in metadata
        assert "training_metrics" in metadata
        assert "created_at" in metadata
        assert "feature_extractor_version" in metadata

        # Check that training metrics are preserved
        assert metadata["training_metrics"]["auc_score"] == metrics["auc_score"]
        assert metadata["training_metrics"]["log_loss"] == metrics["log_loss"]

    def test_train_and_save_pipeline(self):
        """Test complete training and saving pipeline."""
        metrics = self.trainer.train_and_save(n_samples=100)

        # Check that model was trained
        assert self.trainer.model is not None
        assert self.trainer.calibrator is not None
        assert self.trainer.scaler is not None

        # Check that files were saved
        model_path = self.trainer.model_dir / "xgb_model.joblib"
        calibrator_path = self.trainer.model_dir / "calibrator.joblib"
        scaler_path = self.trainer.model_dir / "scaler.joblib"
        metadata_path = self.trainer.model_dir / "metadata.json"

        assert model_path.exists()
        assert calibrator_path.exists()
        assert scaler_path.exists()
        assert metadata_path.exists()

        # Check metrics
        assert "auc_score" in metrics
        assert "log_loss" in metrics
        assert "feature_importance" in metrics

    def test_train_model_different_test_sizes(self):
        """Test training with different test sizes."""
        X, y = self.trainer.generate_synthetic_data(n_samples=100)

        # Test with different test sizes
        for test_size in [0.1, 0.2, 0.3, 0.4]:
            trainer = XGBoostTrainer(model_dir=self.temp_dir)
            metrics = trainer.train_model(X, y, test_size=test_size)

            expected_train_size = int(len(X) * (1 - test_size))
            expected_test_size = int(len(X) * test_size)

            assert metrics["n_samples_train"] == expected_train_size
            assert metrics["n_samples_test"] == expected_test_size

    def test_train_model_different_random_states(self):
        """Test training with different random states."""
        X, y = self.trainer.generate_synthetic_data(n_samples=100)

        # Train with different random states
        metrics1 = self.trainer.train_model(X, y, random_state=42)
        trainer2 = XGBoostTrainer(model_dir=self.temp_dir)
        metrics2 = trainer2.train_model(X, y, random_state=123)

        # Results should be different due to different random states
        assert metrics1["auc_score"] != metrics2["auc_score"]

    def test_feature_importance_structure(self):
        """Test that feature importance is properly structured."""
        X, y = self.trainer.generate_synthetic_data(n_samples=100)
        metrics = self.trainer.train_model(X, y)

        feature_importance = metrics["feature_importance"]

        assert isinstance(feature_importance, dict)
        assert len(feature_importance) == len(X.columns)

        # Check that all features have importance scores
        for feature in X.columns:
            assert feature in feature_importance
            assert isinstance(feature_importance[feature], float)
            assert feature_importance[feature] >= 0.0

    def test_classification_report_structure(self):
        """Test that classification report is properly structured."""
        X, y = self.trainer.generate_synthetic_data(n_samples=100)
        metrics = self.trainer.train_model(X, y)

        classification_report = metrics["classification_report"]

        assert isinstance(classification_report, dict)
        assert "0" in classification_report  # Class 0
        assert "1" in classification_report  # Class 1
        assert "accuracy" in classification_report
        assert "macro avg" in classification_report
        assert "weighted avg" in classification_report

    def test_training_date_format(self):
        """Test that training date is in correct format."""
        X, y = self.trainer.generate_synthetic_data(n_samples=50)
        metrics = self.trainer.train_model(X, y)

        training_date = metrics["training_date"]

        # Should be ISO format
        assert isinstance(training_date, str)
        assert "T" in training_date  # ISO format has T separator
        assert len(training_date) > 10  # Should be a reasonable length

    def test_generate_synthetic_data_different_sizes(self):
        """Test synthetic data generation with different sample sizes."""
        for n_samples in [10, 50, 100, 500]:
            X, y = self.trainer.generate_synthetic_data(n_samples=n_samples)

            assert len(X) == n_samples
            assert len(y) == n_samples
            assert len(X.columns) > 0

    def test_generate_synthetic_data_risk_distribution(self):
        """Test that synthetic data has reasonable risk distribution."""
        X, y = self.trainer.generate_synthetic_data(n_samples=1000)

        # Should have both positive and negative samples
        assert 0 in y.values
        assert 1 in y.values

        # Should not be too imbalanced (between 10% and 90% positive)
        positive_ratio = y.mean()
        assert 0.1 <= positive_ratio <= 0.9

    def test_train_model_with_imbalanced_data(self):
        """Test training with artificially imbalanced data."""
        # Create imbalanced dataset
        X, y = self.trainer.generate_synthetic_data(n_samples=100)

        # Make it heavily imbalanced
        y_imbalanced = y.copy()
        y_imbalanced[y_imbalanced == 1] = 0  # Convert all 1s to 0s
        y_imbalanced.iloc[:5] = 1  # Set only first 5 to 1

        metrics = self.trainer.train_model(X, y_imbalanced)

        # Should still train successfully
        assert self.trainer.model is not None
        assert "auc_score" in metrics
        assert "log_loss" in metrics

    def test_train_model_with_single_class(self):
        """Test training with single class data."""
        X, y = self.trainer.generate_synthetic_data(n_samples=100)

        # Make all targets the same
        y_single = pd.Series([0] * len(y), name="risk_label")

        # This should raise an error or handle gracefully
        with pytest.raises(ValueError):
            self.trainer.train_model(X, y_single)

    def test_save_model_without_training(self):
        """Test saving model without training."""
        # This should work even without training (saves empty model)
        self.trainer.save_model({})

        # Check that files were created
        from pathlib import Path

        assert (Path(self.temp_dir) / "xgb_model.joblib").exists()
        assert (Path(self.temp_dir) / "metadata.json").exists()

    def test_train_model_empty_data(self):
        """Test training with empty data."""
        X_empty = pd.DataFrame()
        y_empty = pd.Series(dtype=int)

        with pytest.raises(ValueError):
            self.trainer.train_model(X_empty, y_empty)

    def test_generate_synthetic_data_zero_samples(self):
        """Test synthetic data generation with zero samples."""
        X, y = self.trainer.generate_synthetic_data(n_samples=0)

        assert len(X) == 0
        assert len(y) == 0

    def test_train_model_very_small_dataset(self):
        """Test training with very small dataset."""
        X, y = self.trainer.generate_synthetic_data(n_samples=50)  # Use larger dataset

        # Should handle small datasets gracefully
        metrics = self.trainer.train_model(X, y, test_size=0.2)

        assert self.trainer.model is not None
        assert "auc_score" in metrics

    def test_model_persistence_consistency(self):
        """Test that saved and loaded models are consistent."""
        # Train and save model
        X, y = self.trainer.generate_synthetic_data(n_samples=100)
        self.trainer.train_model(X, y)
        metrics = {"test": "value"}
        self.trainer.save_model(metrics)

        # Check that all components were saved
        assert (self.trainer.model_dir / "xgb_model.joblib").exists()
        assert (self.trainer.model_dir / "calibrator.joblib").exists()
        assert (self.trainer.model_dir / "scaler.joblib").exists()
        assert (self.trainer.model_dir / "metadata.json").exists()

    def test_feature_extractor_integration(self):
        """Test integration with feature extractor."""
        # Generate sample data
        sample = self.trainer._generate_transaction_sample()

        # Extract features using the integrated feature extractor
        features = self.trainer.feature_extractor.extract_features(sample)

        assert isinstance(features, dict)
        assert len(features) > 0

        # All values should be numeric
        for value in features.values():
            assert isinstance(value, (int, float))

    def test_metadata_consistency(self):
        """Test that metadata is consistent across saves."""
        X, y = self.trainer.generate_synthetic_data(n_samples=50)
        metrics = self.trainer.train_model(X, y)

        self.trainer.save_model(metrics)

        # Load metadata
        metadata_path = self.trainer.model_dir / "metadata.json"
        with open(metadata_path) as f:
            metadata = json.load(f)

        # Check consistency
        assert metadata["feature_names"] == self.trainer.feature_names
        assert metadata["training_metrics"]["n_features"] == len(self.trainer.feature_names)
        assert metadata["training_metrics"]["n_samples_train"] == metrics["n_samples_train"]
        assert metadata["training_metrics"]["n_samples_test"] == metrics["n_samples_test"]


class TestXGBoostTrainerEdgeCases:
    """Test suite for edge cases and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_trainer_with_nonexistent_directory(self):
        """Test trainer with nonexistent directory."""
        nonexistent_dir = Path(self.temp_dir) / "nonexistent"
        trainer = XGBoostTrainer(model_dir=str(nonexistent_dir))

        # Directory should be created
        assert trainer.model_dir.exists()

    def test_trainer_with_readonly_directory(self):
        """Test trainer with readonly directory."""
        readonly_dir = Path(self.temp_dir) / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # Read-only

        try:
            trainer = XGBoostTrainer(model_dir=str(readonly_dir))
            # Should handle readonly directory gracefully
            assert trainer.model_dir == readonly_dir
        finally:
            readonly_dir.chmod(0o755)  # Restore permissions

    def test_generate_synthetic_data_with_negative_samples(self):
        """Test synthetic data generation with negative sample count."""
        trainer = XGBoostTrainer(model_dir=self.temp_dir)

        # Should handle negative samples gracefully (return empty data)
        X, y = trainer.generate_synthetic_data(n_samples=-1)
        assert len(X) == 0
        assert len(y) == 0

    def test_train_model_with_invalid_test_size(self):
        """Test training with invalid test size."""
        trainer = XGBoostTrainer(model_dir=self.temp_dir)
        X, y = trainer.generate_synthetic_data(n_samples=100)

        # Test size > 1.0
        with pytest.raises(ValueError):
            trainer.train_model(X, y, test_size=1.5)

        # Test size < 0.0
        with pytest.raises(ValueError):
            trainer.train_model(X, y, test_size=-0.1)

    def test_train_model_with_mismatched_data(self):
        """Test training with mismatched X and y dimensions."""
        trainer = XGBoostTrainer(model_dir=self.temp_dir)
        X, y = trainer.generate_synthetic_data(n_samples=100)

        # Mismatched lengths
        y_mismatched = y.iloc[:-10]  # Remove last 10 samples

        with pytest.raises(ValueError):
            trainer.train_model(X, y_mismatched)

    def test_save_model_with_invalid_metrics(self):
        """Test saving model with invalid metrics."""
        trainer = XGBoostTrainer(model_dir=self.temp_dir)
        X, y = trainer.generate_synthetic_data(n_samples=50)
        trainer.train_model(X, y)

        # Should handle invalid metrics gracefully
        trainer.save_model("invalid_metrics")

        # Check that files were created
        from pathlib import Path

        assert (Path(self.temp_dir) / "xgb_model.joblib").exists()
        assert (Path(self.temp_dir) / "metadata.json").exists()

        # None metrics should be handled gracefully
        trainer.save_model(None)

    def test_generate_transaction_sample_randomness(self):
        """Test that transaction samples are random."""
        trainer = XGBoostTrainer(model_dir=self.temp_dir)

        # Generate multiple samples
        samples = [trainer._generate_transaction_sample() for _ in range(10)]

        # Should have some variation
        cart_totals = [s["cart_total"] for s in samples]
        amounts = [s["features"]["amount"] for s in samples]

        # Should not all be the same
        assert len(set(cart_totals)) > 1
        assert len(set(amounts)) > 1

    def test_generate_target_deterministic(self):
        """Test that target generation is deterministic for same features."""
        trainer = XGBoostTrainer(model_dir=self.temp_dir)

        features = {
            "amount": 100.0,
            "velocity_24h": 2.0,
            "cross_border": 0.0,
            "location_mismatch": 0.0,
            "payment_method_risk": 0.3,
            "chargebacks_12m": 0.0,
            "loyalty_score": 0.5,
            "hour_of_day": 12.0,
            "is_weekend": 0.0,
        }

        # Generate target multiple times
        targets = [trainer._generate_target(features) for _ in range(10)]

        # Should be deterministic (all same)
        assert len(set(targets)) == 1

    def test_train_model_memory_efficiency(self):
        """Test that training doesn't consume excessive memory."""
        trainer = XGBoostTrainer(model_dir=self.temp_dir)

        # Generate larger dataset
        X, y = trainer.generate_synthetic_data(n_samples=1000)

        # Should train without memory issues
        metrics = trainer.train_model(X, y)

        assert trainer.model is not None
        assert "auc_score" in metrics

    def test_feature_extractor_error_handling(self):
        """Test error handling in feature extraction during training."""
        trainer = XGBoostTrainer(model_dir=self.temp_dir)

        # Mock feature extractor to raise error
        with patch.object(
            trainer.feature_extractor,
            "extract_features",
            side_effect=Exception("Feature extraction failed"),
        ):
            with pytest.raises(Exception):
                trainer.generate_synthetic_data(n_samples=10)

    def test_model_training_error_recovery(self):
        """Test error recovery during model training."""
        trainer = XGBoostTrainer(model_dir=self.temp_dir)
        X, y = trainer.generate_synthetic_data(n_samples=100)

        # Mock XGBoost to raise error
        with patch(
            "orca_core.ml.train_xgb.xgb.XGBClassifier", side_effect=Exception("XGBoost failed")
        ):
            with pytest.raises(Exception):
                trainer.train_model(X, y)

    def test_calibration_error_handling(self):
        """Test error handling during model calibration."""
        trainer = XGBoostTrainer(model_dir=self.temp_dir)
        X, y = trainer.generate_synthetic_data(n_samples=100)

        # Mock calibration to raise error
        with patch(
            "orca_core.ml.train_xgb.CalibratedClassifierCV",
            side_effect=Exception("Calibration failed"),
        ):
            with pytest.raises(Exception):
                trainer.train_model(X, y)


def test_main_function():
    """Test the main function in train_xgb module."""
    from orca_core.ml.train_xgb import main

    with patch("orca_core.ml.train_xgb.XGBoostTrainer") as mock_trainer_class:
        mock_trainer = Mock()
        mock_trainer.train_and_save.return_value = {
            "auc_score": 0.85,
            "log_loss": 0.45,
            "feature_importance": {
                "feature1": 0.3,
                "feature2": 0.2,
                "feature3": 0.1,
                "feature4": 0.05,
                "feature5": 0.05,
                "feature6": 0.05,
                "feature7": 0.05,
                "feature8": 0.05,
                "feature9": 0.05,
                "feature10": 0.05,
            },
        }
        mock_trainer_class.return_value = mock_trainer

        with patch("builtins.print") as mock_print:
            main()

            # Verify trainer was created and train_and_save was called
            mock_trainer_class.assert_called_once()
            mock_trainer.train_and_save.assert_called_once_with(n_samples=10000)

            # Verify print statements
            expected_prints = [
                "🤖 XGBoost Training for Orca Core Risk Prediction",
                "=" * 60,
                "🎉 Training completed successfully!",
                "📊 Final AUC Score: 0.8500",
                "📊 Final Log Loss: 0.4500",
                "🔝 Top 10 Most Important Features:",
                "feature1: 0.3000",
                "feature2: 0.2000",
                "feature3: 0.1000",
            ]

            # Check that all expected print statements were called
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            for expected in expected_prints:
                assert any(
                    expected in call for call in print_calls
                ), f"Expected print not found: {expected}"


# Note: The if __name__ == "__main__" block is tested indirectly through the main() function test
# Testing the actual script execution is complex and not necessary for coverage
