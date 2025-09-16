"""ML hooks for Orca Core decision engine."""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# Import scikit-learn models
from sklearn.ensemble import RandomForestClassifier


class RiskPredictionModel:
    """Machine learning-based risk prediction model for fraud detection."""

    def __init__(self, model_path: str | None = None):
        """
        Initialize the risk prediction model.

        Args:
            model_path: Path to saved model file. If None, creates a new model.
        """
        self.model_path = model_path or "models/risk_model.pkl"
        self.model: RandomForestClassifier | None = None
        self.feature_columns: list[str] = [
            "velocity_24h",
            "velocity_7d",
            "cart_total",
            "customer_age_days",
            "loyalty_score",
            "chargebacks_12m",
            "location_mismatch",
            "high_ip_distance",
            "time_since_last_purchase",
            "payment_method_risk",
        ]
        self._load_or_create_model()

    def _load_or_create_model(self) -> None:
        """Load existing model or create a new one."""
        model_file = Path(self.model_path)
        if model_file.exists():
            try:
                self.model = joblib.load(model_file)
                print(f"✅ Loaded existing model from {self.model_path}")
            except Exception as e:
                print(f"⚠️ Failed to load model: {e}. Creating new model.")
                self._create_default_model()
        else:
            print(f"📝 No existing model found at {self.model_path}. Creating new model.")
            self._create_default_model()

    def _create_default_model(self) -> None:
        """Create a default Random Forest model with sensible parameters."""
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,  # Use all available cores
        )

    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        """
        Train the Random Forest model.

        Args:
            X: Feature matrix
            y: Target labels (0 = low risk, 1 = high risk)
        """
        if self.model is None:
            self._create_default_model()

        if self.model is None:
            print("❌ Cannot train model: Model creation failed")
            return

        print("🚀 Training Random Forest model...")
        self.model.fit(X, y)
        print("✅ Model training completed!")

        # Save the trained model
        self.save_model()

    def predict_risk_score(self, features: dict[str, float]) -> float:
        """
        Predict risk score for given features.

        Args:
            features: Dictionary of feature values

        Returns:
            Risk score between 0.0 and 1.0 (0.0 = low risk, 1.0 = high risk)
        """
        # Handle override for testing
        if "risk_score" in features:
            return float(features["risk_score"])

        if self.model is None:
            print("⚠️ No model loaded, returning default risk score")
            return 0.15

        try:
            # Create feature vector with default values for missing features
            feature_vector = []
            for col in self.feature_columns:
                if col in features:
                    feature_vector.append(float(features[col]))
                else:
                    # Use sensible defaults for missing features
                    default_values = {
                        "velocity_24h": 1.0,
                        "velocity_7d": 3.0,
                        "cart_total": 100.0,
                        "customer_age_days": 365.0,
                        "loyalty_score": 0.5,
                        "chargebacks_12m": 0.0,
                        "location_mismatch": 0.0,
                        "high_ip_distance": 0.0,
                        "time_since_last_purchase": 7.0,
                        "payment_method_risk": 0.3,
                    }
                    feature_vector.append(default_values.get(col, 0.0))

            # Convert to numpy array and reshape for prediction
            X = np.array(feature_vector).reshape(1, -1)

            # Get probability of high risk (class 1)
            risk_probability = self.model.predict_proba(X)[0][1]

            return float(risk_probability)

        except Exception as e:
            # Log error but don't print to stdout (breaks CLI JSON output)
            import logging

            logging.warning(f"Error in ML prediction: {e}. Returning default risk score.")
            return 0.15

    def save_model(self, path: str | None = None) -> None:
        """
        Save the trained model to disk.

        Args:
            path: Optional custom path to save the model
        """
        if self.model is None:
            print("⚠️ No model to save")
            return

        save_path = path or self.model_path
        model_file = Path(save_path)

        # Create directory if it doesn't exist
        model_file.parent.mkdir(parents=True, exist_ok=True)

        joblib.dump(self.model, save_path)
        print(f"💾 Model saved to {save_path}")

    def get_feature_importance(self) -> dict[str, float]:
        """
        Get feature importance from the trained model.

        Returns:
            Dictionary mapping feature names to importance scores
        """
        if self.model is None:
            return {}

        try:
            importance_scores = self.model.feature_importances_
            return dict(zip(self.feature_columns, importance_scores, strict=True))
        except Exception:
            return {}


# Global model instance
_model_instance: RiskPredictionModel | None = None


def get_model() -> RiskPredictionModel:
    """Get or create the global model instance."""
    global _model_instance
    if _model_instance is None:
        _model_instance = RiskPredictionModel()
    return _model_instance


def predict_risk(features: dict[str, float]) -> float:
    """
    Predict risk score based on features using Random Forest model.

    Args:
        features: Dictionary of feature values

    Returns:
        Risk score between 0.0 and 1.0 (0.0 = low risk, 1.0 = high risk)
    """
    model = get_model()
    return model.predict_risk_score(features)


def train_model(X: pd.DataFrame, y: pd.Series, model_path: str | None = None) -> None:
    """
    Train the risk prediction model.

    Args:
        X: Feature matrix
        y: Target labels (0 = low risk, 1 = high risk)
        model_path: Optional path to save the trained model
    """
    global _model_instance
    _model_instance = RiskPredictionModel(model_path)
    _model_instance.train(X, y)
