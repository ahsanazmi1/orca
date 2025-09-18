"""Script to create XGBoost model artifacts for testing."""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


def create_sample_data(n_samples: int = 1000) -> tuple[pd.DataFrame, pd.Series]:
    """Create sample training data."""
    np.random.seed(42)

    # Generate features
    data = {
        "amount": np.random.exponential(100, n_samples),
        "velocity_24h": np.random.poisson(2, n_samples),
        "velocity_7d": np.random.poisson(10, n_samples),
        "cross_border": np.random.binomial(1, 0.1, n_samples),
        "location_mismatch": np.random.binomial(1, 0.05, n_samples),
        "payment_method_risk": np.random.beta(2, 5, n_samples),
        "chargebacks_12m": np.random.poisson(0.5, n_samples),
        "customer_age_days": np.random.exponential(365, n_samples),
        "loyalty_score": np.random.beta(3, 2, n_samples),
        "time_since_last_purchase": np.random.exponential(7, n_samples),
    }

    df = pd.DataFrame(data)

    # Create target based on business rules
    target = (
        (df["amount"] > 500).astype(int) * 0.3
        + (df["velocity_24h"] > 3).astype(int) * 0.2
        + (df["cross_border"] > 0).astype(int) * 0.2
        + (df["location_mismatch"] > 0).astype(int) * 0.3
        + (df["payment_method_risk"] > 0.7).astype(int) * 0.2
        + (df["chargebacks_12m"] > 1).astype(int) * 0.4
        + np.random.normal(0, 0.1, n_samples)
    )

    # Convert to binary classification
    target = (target > 0.5).astype(int)

    return df, target


def train_model():
    """Train XGBoost model and create artifacts."""
    print("🚀 Creating XGBoost model artifacts...")

    # Create sample data
    X, y = create_sample_data(2000)

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Create scaler
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train XGBoost model
    model = xgb.XGBClassifier(
        n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, eval_metric="logloss"
    )

    model.fit(X_train_scaled, y_train)

    # Calibrate the model
    calibrator = CalibratedClassifierCV(model, method="isotonic", cv=3)
    calibrator.fit(X_train_scaled, y_train)

    # Get feature importance (convert numpy types to Python types)
    feature_importance = {
        name: float(importance)
        for name, importance in zip(X.columns, model.feature_importances_, strict=True)
    }

    # Create metadata
    metadata = {
        "version": "1.0.0",
        "trained_on": "2024-01-01",
        "feature_names": list(X.columns),
        "feature_importance": feature_importance,
        "thresholds": {
            "amount": 500.0,
            "velocity_24h": 3.0,
            "cross_border": 0.5,
            "location_mismatch": 0.5,
            "payment_method_risk": 0.7,
            "chargebacks_12m": 1.0,
        },
        "training_metrics": {
            "train_accuracy": float(model.score(X_train_scaled, y_train)),
            "test_accuracy": float(model.score(X_test_scaled, y_test)),
            "feature_count": len(X.columns),
        },
    }

    # Create feature specification
    feature_spec = {
        "feature_names": list(X.columns),
        "defaults": {
            "amount": 100.0,
            "velocity_24h": 1.0,
            "velocity_7d": 5.0,
            "cross_border": 0.0,
            "location_mismatch": 0.0,
            "payment_method_risk": 0.3,
            "chargebacks_12m": 0.0,
            "customer_age_days": 365.0,
            "loyalty_score": 0.5,
            "time_since_last_purchase": 7.0,
        },
        "ap2_mappings": {
            "amount": "cart.amount",
            "velocity_24h": "velocity.24h",
            "velocity_7d": "velocity.7d",
            "cross_border": "cart.geo.cross_border",
            "location_mismatch": "cart.geo.location_mismatch",
            "payment_method_risk": "payment.method_risk",
            "chargebacks_12m": "customer.chargebacks_12m",
            "customer_age_days": "customer.age_days",
            "loyalty_score": "customer.loyalty_score",
            "time_since_last_purchase": "customer.time_since_last_purchase",
        },
    }

    # Create model directory
    model_dir = Path("models/xgb/1.0.0")
    model_dir.mkdir(parents=True, exist_ok=True)

    # Save model
    model.save_model(str(model_dir / "model.json"))

    # Save calibrator
    joblib.dump(calibrator, model_dir / "calibrator.pkl")

    # Save scaler
    joblib.dump(scaler, model_dir / "scaler.pkl")

    # Save metadata
    with open(model_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # Save feature specification
    with open(model_dir / "feature_spec.json", "w") as f:
        json.dump(feature_spec, f, indent=2)

    print(f"✅ Model artifacts created in {model_dir}")
    print(f"📊 Features: {len(X.columns)}")
    print(f"📊 Train accuracy: {metadata['training_metrics']['train_accuracy']:.3f}")
    print(f"📊 Test accuracy: {metadata['training_metrics']['test_accuracy']:.3f}")

    return model_dir


if __name__ == "__main__":
    train_model()
