"""
XGBoost Training Module for Orca Core

This module generates synthetic training data and trains an XGBoost model
for risk prediction with proper calibration.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

# XGBoost imports
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, log_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from .features import FeatureExtractor


class XGBoostTrainer:
    """XGBoost model trainer for Orca risk prediction."""

    def __init__(self, model_dir: str = "models") -> None:
        """Initialize trainer with model directory."""
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)

        self.feature_extractor = FeatureExtractor()
        self.model: xgb.XGBClassifier | None = None
        self.calibrator: CalibratedClassifierCV | None = None
        self.scaler: StandardScaler | None = None
        self.feature_names: list[str] | None = None
        self.metadata: dict[str, Any] = {}

    def generate_synthetic_data(self, n_samples: int = 10000) -> tuple[pd.DataFrame, pd.Series]:
        """
        Generate synthetic training data for risk prediction.

        Args:
            n_samples: Number of samples to generate

        Returns:
            Tuple of (features_df, target_series)
        """
        print(f"🎲 Generating {n_samples} synthetic training samples...")

        data = []
        targets = []

        for _i in range(n_samples):
            # Generate realistic transaction data
            sample = self._generate_transaction_sample()

            # Extract features
            features = self.feature_extractor.extract_features(sample)

            # Generate target (0 = low risk, 1 = high risk)
            target = self._generate_target(features)

            data.append(features)
            targets.append(target)

        # Convert to DataFrame
        features_df = pd.DataFrame(data)
        targets_series = pd.Series(targets, name="risk_label")

        print(f"✅ Generated {len(features_df)} samples")
        print(f"📊 Risk distribution: {targets_series.value_counts().to_dict()}")

        return features_df, targets_series

    def _generate_transaction_sample(self) -> dict[str, Any]:
        """Generate a single synthetic transaction sample."""
        # Base transaction data
        amount = np.random.lognormal(mean=4.5, sigma=1.0)  # Log-normal distribution
        cart_total = amount * np.random.uniform(0.8, 1.2)

        # Customer context
        customer_age_days = np.random.exponential(365)  # Exponential distribution
        loyalty_tier = np.random.choice(
            ["BRONZE", "SILVER", "GOLD", "PLATINUM"], p=[0.4, 0.3, 0.2, 0.1]
        )

        # Velocity features (correlated with risk)
        base_velocity = np.random.poisson(2)
        velocity_24h = max(1, base_velocity + np.random.poisson(1))
        velocity_7d = velocity_24h * np.random.uniform(2, 5)
        velocity_30d = velocity_7d * np.random.uniform(3, 6)

        # Location features
        cross_border = np.random.choice([0, 1], p=[0.8, 0.2])
        np.random.choice([0, 1], p=[0.9, 0.1])

        # Payment method
        payment_methods = ["card", "visa", "mastercard", "amex", "ach", "paypal"]
        payment_method = np.random.choice(payment_methods, p=[0.1, 0.3, 0.3, 0.1, 0.1, 0.1])

        # Temporal features
        np.random.randint(0, 24)
        np.random.randint(0, 7)

        sample = {
            "cart_total": cart_total,
            "currency": "USD",
            "rail": np.random.choice(["Card", "ACH"]),
            "channel": np.random.choice(["online", "pos"]),
            "features": {
                "amount": amount,
                "velocity_24h": velocity_24h,
                "velocity_7d": velocity_7d,
                "velocity_30d": velocity_30d,
                "cross_border": cross_border,
                "high_ip_distance": np.random.choice([0, 1], p=[0.9, 0.1]),
                "card_bin_risk": np.random.beta(2, 8),  # Beta distribution for risk scores
                "time_since_last_purchase_hours": np.random.exponential(24),
            },
            "context": {
                "customer": {
                    "age_days": customer_age_days,
                    "loyalty_tier": loyalty_tier,
                    "chargebacks_12m": np.random.poisson(0.5),
                    "time_since_last_purchase_hours": np.random.exponential(24),
                },
                "location_ip_country": (
                    "US" if not cross_border else np.random.choice(["CA", "MX", "GB", "DE"])
                ),
                "billing_country": "US",
                "payment_method": {"type": payment_method},
            },
        }

        return sample

    def _generate_target(self, features: dict[str, float]) -> int:
        """Generate target label based on features (simplified risk model)."""
        risk_score = 0.0

        # Amount risk
        if features["amount"] > 1000:
            risk_score += 0.3
        elif features["amount"] > 500:
            risk_score += 0.2

        # Velocity risk
        if features["velocity_24h"] > 5:
            risk_score += 0.3
        elif features["velocity_24h"] > 3:
            risk_score += 0.2

        # Location risk
        if features["cross_border"] > 0:
            risk_score += 0.2
        if features["location_mismatch"] > 0:
            risk_score += 0.2

        # Payment method risk
        risk_score += features["payment_method_risk"] * 0.2

        # Customer risk
        if features["chargebacks_12m"] > 0:
            risk_score += 0.3
        if features["loyalty_score"] < 0.3:
            risk_score += 0.1

        # Temporal risk
        if features["hour_of_day"] < 6 or features["hour_of_day"] > 22:
            risk_score += 0.1
        if features["is_weekend"] > 0:
            risk_score += 0.1

        # Add some noise
        risk_score += np.random.normal(0, 0.1)
        risk_score = max(0, min(1, risk_score))  # Clamp to [0, 1]

        # Convert to binary label (threshold at 0.5)
        return 1 if risk_score > 0.5 else 0

    def train_model(
        self, X: pd.DataFrame, y: pd.Series, test_size: float = 0.2, random_state: int = 42
    ) -> dict[str, Any]:
        """
        Train XGBoost model with calibration.

        Args:
            X: Feature matrix
            y: Target labels
            test_size: Test set size
            random_state: Random seed

        Returns:
            Training metrics dictionary
        """
        print("🚀 Training XGBoost model...")

        # Store feature names
        self.feature_names = X.columns.tolist()

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )

        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train XGBoost model
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=random_state,
            eval_metric="logloss",
        )

        if self.model is None:
            raise ValueError("Model not initialized")
        self.model.fit(X_train_scaled, y_train, eval_set=[(X_test_scaled, y_test)], verbose=False)

        # Calibrate the model
        print("📊 Calibrating model...")
        self.calibrator = CalibratedClassifierCV(self.model, method="isotonic", cv=3)
        if self.calibrator is None:
            raise ValueError("Calibrator not initialized")
        self.calibrator.fit(X_train_scaled, y_train)

        # Evaluate model
        y_pred_proba = self.calibrator.predict_proba(X_test_scaled)[:, 1]
        y_pred = (y_pred_proba > 0.5).astype(int)

        # Calculate metrics
        metrics = {
            "auc_score": float(roc_auc_score(y_test, y_pred_proba)),
            "log_loss": float(log_loss(y_test, y_pred_proba)),
            "classification_report": classification_report(y_test, y_pred, output_dict=True),
            "feature_importance": {
                name: float(imp)
                for name, imp in zip(
                    self.feature_names or [],
                    self.model.feature_importances_ if self.model else [],
                    strict=False,
                )
            },
            "n_features": len(self.feature_names) if self.feature_names else 0,
            "n_samples_train": len(X_train),
            "n_samples_test": len(X_test),
            "training_date": datetime.now().isoformat(),
        }

        print("✅ Model training completed!")
        print(f"📊 AUC Score: {metrics['auc_score']:.4f}")
        print(f"📊 Log Loss: {metrics['log_loss']:.4f}")

        return metrics

    def save_model(self, metrics: dict[str, Any]) -> None:
        """Save trained model and artifacts."""
        print("💾 Saving model artifacts...")

        # Save XGBoost model
        model_path = self.model_dir / "xgb_model.joblib"
        joblib.dump(self.model, model_path)

        # Save calibrator
        calibrator_path = self.model_dir / "calibrator.joblib"
        joblib.dump(self.calibrator, calibrator_path)

        # Save scaler
        scaler_path = self.model_dir / "scaler.joblib"
        joblib.dump(self.scaler, scaler_path)

        # Save metadata
        metadata = {
            "model_type": "xgboost",
            "version": "1.0.0",
            "feature_names": self.feature_names,
            "training_metrics": metrics,
            "created_at": datetime.now().isoformat(),
            "feature_extractor_version": "1.0.0",
        }

        metadata_path = self.model_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"✅ Model artifacts saved to {self.model_dir}")
        print("   📁 xgb_model.joblib")
        print("   📁 calibrator.joblib")
        print("   📁 scaler.joblib")
        print("   📁 metadata.json")

    def train_and_save(self, n_samples: int = 10000) -> dict[str, Any]:
        """Complete training pipeline: generate data, train, and save."""
        # Generate synthetic data
        X, y = self.generate_synthetic_data(n_samples)

        # Train model
        metrics = self.train_model(X, y)

        # Save artifacts
        self.save_model(metrics)

        return metrics


def main() -> None:
    """Main training function."""
    print("🤖 XGBoost Training for Orca Core Risk Prediction")
    print("=" * 60)

    # Create trainer
    trainer = XGBoostTrainer()

    # Train and save model
    metrics = trainer.train_and_save(n_samples=10000)

    print("\n🎉 Training completed successfully!")
    print(f"📊 Final AUC Score: {metrics['auc_score']:.4f}")
    print(f"📊 Final Log Loss: {metrics['log_loss']:.4f}")

    # Show top features
    feature_importance = metrics["feature_importance"]
    top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]

    print("\n🔝 Top 10 Most Important Features:")
    for feature, importance in top_features:
        print(f"   {feature}: {importance:.4f}")


if __name__ == "__main__":
    main()
