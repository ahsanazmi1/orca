#!/usr/bin/env python3
"""Training script for Orca Core ML risk prediction model."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from orca_core.core.ml_hooks import train_model  # noqa: E402
from sklearn.metrics import classification_report, roc_auc_score  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402


def generate_sample_data(n_samples: int = 1000) -> tuple[pd.DataFrame, pd.Series]:
    """
    Generate synthetic training data for risk prediction.

    Args:
        n_samples: Number of samples to generate

    Returns:
        Tuple of (features_df, target_series)
    """
    np.random.seed(42)

    # Generate features
    data = {
        "velocity_24h": np.random.exponential(2.0, n_samples),
        "velocity_7d": np.random.exponential(5.0, n_samples),
        "cart_total": np.random.lognormal(4.0, 1.5, n_samples),
        "customer_age_days": np.random.lognormal(6.0, 1.0, n_samples),
        "loyalty_score": np.random.beta(2, 2, n_samples),
        "chargebacks_12m": np.random.poisson(0.5, n_samples),
        "location_mismatch": np.random.choice([0, 1], n_samples, p=[0.9, 0.1]),
        "high_ip_distance": np.random.choice([0, 1], n_samples, p=[0.85, 0.15]),
        "time_since_last_purchase": np.random.exponential(7.0, n_samples),
        "payment_method_risk": np.random.beta(2, 3, n_samples),
    }

    features_df = pd.DataFrame(data)

    # Generate target labels based on risk patterns
    # High risk if:
    # - High velocity AND high cart total
    # - Recent chargebacks
    # - Location mismatch
    # - High payment method risk

    risk_score = (
        (features_df["velocity_24h"] > 5) * 0.3
        + (features_df["cart_total"] > 1000) * 0.2
        + (features_df["chargebacks_12m"] > 0) * 0.4
        + (features_df["location_mismatch"] == 1) * 0.3
        + (features_df["high_ip_distance"] == 1) * 0.2
        + (features_df["payment_method_risk"] > 0.7) * 0.3
        + np.random.normal(0, 0.1, n_samples)
    )

    # Convert to binary labels (0 = low risk, 1 = high risk)
    target = (risk_score > 0.5).astype(int)

    return features_df, pd.Series(target)


def main() -> None:
    """Main training function."""
    print("🎯 Orca Core XGBoost Model Training")
    print("=" * 50)

    # Generate sample data
    print("📊 Generating synthetic training data...")
    X, y = generate_sample_data(n_samples=2000)

    print(f"✅ Generated {len(X)} samples")
    print(f"📈 Risk distribution: {y.value_counts().to_dict()}")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"📚 Training set: {len(X_train)} samples")
    print(f"🧪 Test set: {len(X_test)} samples")

    # Train model
    print("\n🚀 Training XGBoost model...")
    train_model(X_train, y_train, model_path="models/orca_risk_model.pkl")

    # Evaluate model
    print("\n📊 Evaluating model performance...")
    from orca_core.core.ml_hooks import get_model

    model = get_model()

    # Predict on test set
    y_pred_proba = []
    for _, row in X_test.iterrows():
        features = row.to_dict()
        risk_score = model.predict_risk_score(features)
        y_pred_proba.append(risk_score)

    y_pred = (np.array(y_pred_proba) > 0.5).astype(int)

    # Calculate metrics
    auc_score = roc_auc_score(y_test, y_pred_proba)
    print(f"🎯 ROC AUC Score: {auc_score:.3f}")

    print("\n📋 Classification Report:")
    print(classification_report(y_test, y_pred, target_names=["Low Risk", "High Risk"]))

    # Feature importance
    importance = model.get_feature_importance()
    print("\n🔍 Feature Importance:")
    for feature, imp in sorted(importance.items(), key=lambda x: x[1], reverse=True):
        print(f"  {feature}: {imp:.3f}")

    print("\n✅ Model training completed successfully!")
    print("💾 Model saved to models/orca_risk_model.pkl")


if __name__ == "__main__":
    main()
