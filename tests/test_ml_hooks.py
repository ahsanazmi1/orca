"""Tests for ML hooks functionality."""

import tempfile
from pathlib import Path

import pandas as pd
from orca_core.core.ml_hooks import RiskPredictionModel, get_model, predict_risk, train_model


class TestMLHooks:
    """Test cases for ML hooks."""

    def test_predict_risk_override(self) -> None:
        """Test predict_risk with override value."""
        features = {"risk_score": 0.8}
        risk_score = predict_risk(features)
        assert risk_score == 0.8

    def test_predict_risk_empty_features(self) -> None:
        """Test predict_risk with empty features."""
        features: dict[str, float] = {}
        risk_score = predict_risk(features)

        # Should return a value between 0 and 1 (XGBoost probability)
        assert 0.0 <= risk_score <= 1.0

    def test_predict_risk_with_features(self) -> None:
        """Test predict_risk with various feature combinations."""
        # Test with some features - should return a valid probability
        features = {"velocity_24h": 1.0, "cart_total": 100.0, "loyalty_score": 0.8}
        risk_score = predict_risk(features)

        # Should return a value between 0 and 1
        assert 0.0 <= risk_score <= 1.0

    def test_risk_prediction_model_creation(self) -> None:
        """Test RiskPredictionModel creation."""
        model = RiskPredictionModel()

        assert model.model is not None
        assert len(model.feature_columns) > 0
        assert "velocity_24h" in model.feature_columns

    def test_model_save_load(self) -> None:
        """Test model saving and loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "test_model.pkl"

            # Create and save model
            model = RiskPredictionModel(str(model_path))
            model.save_model()

            assert model_path.exists()

            # Load model
            loaded_model = RiskPredictionModel(str(model_path))
            assert loaded_model.model is not None

    def test_model_training(self) -> None:
        """Test model training functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "trained_model.pkl"

            # Generate sample data
            X = pd.DataFrame(
                {
                    "velocity_24h": [1.0, 5.0, 2.0, 8.0, 1.5],
                    "velocity_7d": [3.0, 15.0, 6.0, 25.0, 4.0],
                    "cart_total": [100.0, 2000.0, 250.0, 5000.0, 150.0],
                    "customer_age_days": [365.0, 730.0, 180.0, 1095.0, 500.0],
                    "loyalty_score": [0.5, 0.8, 0.3, 0.9, 0.6],
                    "chargebacks_12m": [0.0, 2.0, 0.0, 1.0, 0.0],
                    "location_mismatch": [0.0, 1.0, 0.0, 1.0, 0.0],
                    "high_ip_distance": [0.0, 1.0, 0.0, 1.0, 0.0],
                    "time_since_last_purchase": [7.0, 1.0, 14.0, 2.0, 10.0],
                    "payment_method_risk": [0.3, 0.8, 0.2, 0.9, 0.4],
                }
            )

            y = pd.Series([0, 1, 0, 1, 0])  # Binary labels

            # Train model
            train_model(X, y, str(model_path))

            # Verify model was saved
            assert model_path.exists()

            # Test prediction
            model = get_model()
            features = {"velocity_24h": 6.0, "cart_total": 1500.0, "chargebacks_12m": 1.0}

            risk_score = model.predict_risk_score(features)
            assert 0.0 <= risk_score <= 1.0

    def test_feature_importance(self) -> None:
        """Test feature importance functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "test_model.pkl"

            # Create a new model (not loading existing one)
            model = RiskPredictionModel(str(model_path))

            # Feature importance should be empty for untrained model
            importance = model.get_feature_importance()
            assert importance == {}

            # Test with trained model
            X = pd.DataFrame(
                {
                    "velocity_24h": [1.0, 5.0, 2.0],
                    "velocity_7d": [3.0, 15.0, 6.0],
                    "cart_total": [100.0, 2000.0, 250.0],
                    "customer_age_days": [365.0, 730.0, 180.0],
                    "loyalty_score": [0.5, 0.8, 0.3],
                    "chargebacks_12m": [0.0, 2.0, 0.0],
                    "location_mismatch": [0.0, 1.0, 0.0],
                    "high_ip_distance": [0.0, 1.0, 0.0],
                    "time_since_last_purchase": [7.0, 1.0, 14.0],
                    "payment_method_risk": [0.3, 0.8, 0.2],
                }
            )
            y = pd.Series([0, 1, 0])

            model.train(X, y)
            importance = model.get_feature_importance()

            # Should have feature importance after training
            assert len(importance) > 0
            assert all(isinstance(v, int | float) for v in importance.values())

    def test_model_fallback_on_prediction_error(self) -> None:
        """Test that model falls back gracefully on prediction errors."""
        # Create a model with no trained model
        model = RiskPredictionModel()
        model.model = None  # Simulate untrained model

        # Should return default risk score on prediction error
        features = {"velocity_24h": 1.0}
        risk_score = model.predict_risk_score(features)
        assert risk_score == 0.15  # Default fallback value

    def test_model_load_error_handling(self) -> None:
        """Test error handling when loading a corrupted model file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "corrupted_model.pkl"

            # Create a corrupted model file
            model_path.write_text("corrupted data")

            # Should create a new model when loading fails
            model = RiskPredictionModel(str(model_path))
            assert model.model is not None

    def test_model_training_with_none_model(self) -> None:
        """Test training when model is None."""
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "test_model.pkl"
            model = RiskPredictionModel(str(model_path))
            model.model = None  # Simulate failed model creation

            X = pd.DataFrame(
                {
                    "velocity_24h": [1.0, 2.0],
                    "velocity_7d": [3.0, 6.0],
                    "cart_total": [100.0, 250.0],
                    "customer_age_days": [365.0, 180.0],
                    "loyalty_score": [0.5, 0.3],
                    "chargebacks_12m": [0.0, 0.0],
                    "location_mismatch": [0.0, 0.0],
                    "high_ip_distance": [0.0, 0.0],
                    "time_since_last_purchase": [7.0, 14.0],
                    "payment_method_risk": [0.3, 0.2],
                }
            )
            y = pd.Series([0, 1])

            # Should handle None model gracefully
            model.train(X, y)
            # Should not crash, but model might still be None

    def test_save_model_with_none_model(self) -> None:
        """Test saving when model is None."""
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "test_model.pkl"
            model = RiskPredictionModel(str(model_path))
            model.model = None

            # Should handle None model gracefully
            model.save_model()
            # Should not crash

    def test_predict_risk_score_exception_handling(self) -> None:
        """Test exception handling in predict_risk_score."""
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "test_model.pkl"
            model = RiskPredictionModel(str(model_path))

            # Create a mock model that will raise an exception
            class MockModel:
                def predict_proba(self, X):
                    raise Exception("Mock prediction error")

            model.model = MockModel()

            # Should return default risk score on exception
            features = {"velocity_24h": 1.0}
            risk_score = model.predict_risk_score(features)
            assert risk_score == 0.15

    def test_get_feature_importance_exception_handling(self) -> None:
        """Test exception handling in get_feature_importance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "test_model.pkl"
            model = RiskPredictionModel(str(model_path))

            # Create a mock model that will raise an exception
            class MockModel:
                @property
                def feature_importances_(self):
                    raise Exception("Mock feature importance error")

            model.model = MockModel()

            # Should return empty dict on exception
            importance = model.get_feature_importance()
            assert importance == {}

    def test_global_model_singleton(self) -> None:
        """Test that get_model returns the same instance."""
        model1 = get_model()
        model2 = get_model()
        assert model1 is model2

    def test_train_model_function(self) -> None:
        """Test the train_model function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "trained_model.pkl"

            X = pd.DataFrame(
                {
                    "velocity_24h": [1.0, 5.0, 2.0],
                    "velocity_7d": [3.0, 15.0, 6.0],
                    "cart_total": [100.0, 2000.0, 250.0],
                    "customer_age_days": [365.0, 730.0, 180.0],
                    "loyalty_score": [0.5, 0.8, 0.3],
                    "chargebacks_12m": [0.0, 2.0, 0.0],
                    "location_mismatch": [0.0, 1.0, 0.0],
                    "high_ip_distance": [0.0, 1.0, 0.0],
                    "time_since_last_purchase": [7.0, 1.0, 14.0],
                    "payment_method_risk": [0.3, 0.8, 0.2],
                }
            )
            y = pd.Series([0, 1, 0])

            # Train model using the function
            train_model(X, y, str(model_path))

            # Verify model was saved
            assert model_path.exists()

            # Test that global model was updated
            model = get_model()
            assert model.model is not None
