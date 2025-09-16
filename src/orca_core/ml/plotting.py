"""
ML Model Plotting and Visualization

This module provides comprehensive plotting capabilities for ML model evaluation,
including ROC/PR curves, calibration plots, and feature importance visualizations.
"""

import json
import os
from typing import Any

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    auc,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)


class MLPlotter:
    """Comprehensive plotting class for ML model evaluation."""

    def __init__(self, model_dir: str = "models") -> None:
        """
        Initialize the ML plotter.

        Args:
            model_dir: Directory containing model artifacts
        """
        self.model_dir = model_dir
        self.setup_style()

    def setup_style(self) -> None:
        """Set up matplotlib and seaborn styles."""
        plt.style.use("seaborn-v0_8")
        sns.set_palette("husl")
        plt.rcParams["figure.figsize"] = (12, 8)
        plt.rcParams["font.size"] = 12

    def plot_roc_curve(
        self,
        y_true: np.ndarray,
        y_scores: np.ndarray,
        model_name: str = "Model",
        save_path: str | None = None,
    ) -> plt.Figure:
        """
        Plot ROC curve with AUC score.

        Args:
            y_true: True binary labels
            y_scores: Predicted probabilities or scores
            model_name: Name of the model for the plot
            save_path: Optional path to save the plot

        Returns:
            matplotlib Figure object
        """
        # Calculate ROC curve
        fpr, tpr, thresholds = roc_curve(y_true, y_scores)
        auc_score = roc_auc_score(y_true, y_scores)

        # Create plot
        fig, ax = plt.subplots(figsize=(10, 8))

        # Plot ROC curve
        ax.plot(fpr, tpr, color="blue", lw=2, label=f"{model_name} (AUC = {auc_score:.3f})")

        # Plot diagonal line (random classifier)
        ax.plot(
            [0, 1],
            [0, 1],
            color="red",
            lw=2,
            linestyle="--",
            label="Random Classifier (AUC = 0.500)",
        )

        # Customize plot
        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(0.0, 1.05)
        ax.set_xlabel("False Positive Rate", fontsize=14)
        ax.set_ylabel("True Positive Rate", fontsize=14)
        ax.set_title(f"ROC Curve - {model_name}", fontsize=16, fontweight="bold")
        ax.legend(loc="lower right", fontsize=12)
        ax.grid(True, alpha=0.3)

        # Add AUC score as text
        ax.text(
            0.6,
            0.2,
            f"AUC = {auc_score:.3f}",
            bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.8},
            fontsize=14,
            fontweight="bold",
        )

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            print(f"📊 ROC curve saved to: {save_path}")

        return fig

    def plot_precision_recall_curve(
        self,
        y_true: np.ndarray,
        y_scores: np.ndarray,
        model_name: str = "Model",
        save_path: str | None = None,
    ) -> plt.Figure:
        """
        Plot Precision-Recall curve with AUC score.

        Args:
            y_true: True binary labels
            y_scores: Predicted probabilities or scores
            model_name: Name of the model for the plot
            save_path: Optional path to save the plot

        Returns:
            matplotlib Figure object
        """
        # Calculate PR curve
        precision, recall, thresholds = precision_recall_curve(y_true, y_scores)
        pr_auc = auc(recall, precision)

        # Calculate baseline (random classifier)
        baseline = np.sum(y_true) / len(y_true)

        # Create plot
        fig, ax = plt.subplots(figsize=(10, 8))

        # Plot PR curve
        ax.plot(
            recall, precision, color="blue", lw=2, label=f"{model_name} (PR-AUC = {pr_auc:.3f})"
        )

        # Plot baseline
        ax.axhline(
            y=baseline,
            color="red",
            lw=2,
            linestyle="--",
            label=f"Random Classifier (PR-AUC = {baseline:.3f})",
        )

        # Customize plot
        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(0.0, 1.05)
        ax.set_xlabel("Recall", fontsize=14)
        ax.set_ylabel("Precision", fontsize=14)
        ax.set_title(f"Precision-Recall Curve - {model_name}", fontsize=16, fontweight="bold")
        ax.legend(loc="lower left", fontsize=12)
        ax.grid(True, alpha=0.3)

        # Add PR-AUC score as text
        ax.text(
            0.6,
            0.2,
            f"PR-AUC = {pr_auc:.3f}",
            bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.8},
            fontsize=14,
            fontweight="bold",
        )

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            print(f"📊 PR curve saved to: {save_path}")

        return fig

    def plot_calibration_curve(
        self,
        y_true: np.ndarray,
        y_prob: np.ndarray,
        model_name: str = "Model",
        n_bins: int = 10,
        save_path: str | None = None,
    ) -> plt.Figure:
        """
        Plot calibration curve to assess probability calibration.

        Args:
            y_true: True binary labels
            y_prob: Predicted probabilities
            model_name: Name of the model for the plot
            n_bins: Number of bins for calibration curve
            save_path: Optional path to save the plot

        Returns:
            matplotlib Figure object
        """
        # Calculate calibration curve
        fraction_of_positives, mean_predicted_value = calibration_curve(
            y_true, y_prob, n_bins=n_bins
        )

        # Calculate calibration error
        calibration_error = np.mean(np.abs(fraction_of_positives - mean_predicted_value))

        # Create plot
        fig, ax = plt.subplots(figsize=(10, 8))

        # Plot calibration curve
        ax.plot(
            mean_predicted_value,
            fraction_of_positives,
            "s-",
            label=f"{model_name} (ECE = {calibration_error:.3f})",
            color="blue",
            markersize=8,
        )

        # Plot perfect calibration line
        ax.plot([0, 1], [0, 1], "k:", label="Perfectly calibrated", color="red", lw=2)

        # Customize plot
        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(0.0, 1.0)
        ax.set_xlabel("Mean Predicted Probability", fontsize=14)
        ax.set_ylabel("Fraction of Positives", fontsize=14)
        ax.set_title(f"Calibration Curve - {model_name}", fontsize=16, fontweight="bold")
        ax.legend(loc="upper left", fontsize=12)
        ax.grid(True, alpha=0.3)

        # Add calibration error as text
        ax.text(
            0.6,
            0.2,
            f"ECE = {calibration_error:.3f}",
            bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.8},
            fontsize=14,
            fontweight="bold",
        )

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            print(f"📊 Calibration curve saved to: {save_path}")

        return fig

    def plot_feature_importance(
        self,
        feature_names: list[str],
        importance_scores: np.ndarray,
        model_name: str = "Model",
        top_n: int = 15,
        save_path: str | None = None,
    ) -> plt.Figure:
        """
        Plot feature importance scores.

        Args:
            feature_names: List of feature names
            importance_scores: Feature importance scores
            model_name: Name of the model for the plot
            top_n: Number of top features to display
            save_path: Optional path to save the plot

        Returns:
            matplotlib Figure object
        """
        # Create DataFrame for easier handling
        df_importance = pd.DataFrame(
            {"feature": feature_names, "importance": importance_scores}
        ).sort_values("importance", ascending=True)
        # Sort in ascending order for horizontal bar plot

        # Take top N features
        df_importance = df_importance.tail(top_n)

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 8))

        # Create horizontal bar plot
        bars = ax.barh(
            df_importance["feature"], df_importance["importance"], color="skyblue", alpha=0.8
        )

        # Customize plot
        ax.set_xlabel("Feature Importance", fontsize=14)
        ax.set_ylabel("Features", fontsize=14)
        ax.set_title(f"Feature Importance - {model_name}", fontsize=16, fontweight="bold")
        ax.grid(True, alpha=0.3, axis="x")

        # Add value labels on bars
        for _i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(
                width + 0.001,
                bar.get_y() + bar.get_height() / 2,
                f"{width:.3f}",
                ha="left",
                va="center",
                fontsize=10,
            )

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            print(f"📊 Feature importance plot saved to: {save_path}")

        return fig

    def plot_confusion_matrix(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        class_names: list[str] | None = None,
        model_name: str = "Model",
        save_path: str | None = None,
    ) -> plt.Figure:
        """
        Plot confusion matrix with annotations.

        Args:
            y_true: True labels
            y_pred: Predicted labels
            class_names: Names of classes
            model_name: Name of the model for the plot
            save_path: Optional path to save the plot

        Returns:
            matplotlib Figure object
        """
        # Calculate confusion matrix
        cm = confusion_matrix(y_true, y_pred)

        # Create plot
        fig, ax = plt.subplots(figsize=(8, 6))

        # Create heatmap
        sns.heatmap(
            cm,
            annot=True,
            fmt="d",
            cmap="Blues",
            xticklabels=class_names,
            yticklabels=class_names,
            ax=ax,
        )

        # Customize plot
        ax.set_xlabel("Predicted Label", fontsize=14)
        ax.set_ylabel("True Label", fontsize=14)
        ax.set_title(f"Confusion Matrix - {model_name}", fontsize=16, fontweight="bold")

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            print(f"📊 Confusion matrix saved to: {save_path}")

        return fig

    def plot_model_comparison(
        self, results: dict[str, dict[str, Any]], metric: str = "auc", save_path: str | None = None
    ) -> plt.Figure:
        """
        Plot comparison of multiple models.

        Args:
            results: Dictionary with model results
            metric: Metric to compare (auc, pr_auc, accuracy, etc.)
            save_path: Optional path to save the plot

        Returns:
            matplotlib Figure object
        """
        # Extract model names and scores
        model_names = list(results.keys())
        scores = [results[model][metric] for model in model_names]

        # Create plot
        fig, ax = plt.subplots(figsize=(10, 6))

        # Create bar plot
        bars = ax.bar(model_names, scores, color="lightcoral", alpha=0.8)

        # Customize plot
        ax.set_ylabel(f"{metric.upper()} Score", fontsize=14)
        ax.set_title(f"Model Comparison - {metric.upper()}", fontsize=16, fontweight="bold")
        ax.grid(True, alpha=0.3, axis="y")

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 0.01,
                f"{height:.3f}",
                ha="center",
                va="bottom",
                fontsize=12,
            )

        # Rotate x-axis labels if needed
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            print(f"📊 Model comparison plot saved to: {save_path}")

        return fig

    def generate_model_report(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_prob: np.ndarray,
        feature_names: list[str],
        importance_scores: np.ndarray,
        model_name: str = "Model",
        output_dir: str = "plots",
    ) -> dict[str, str]:
        """
        Generate comprehensive model evaluation report with all plots.

        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_prob: Predicted probabilities
            feature_names: List of feature names
            importance_scores: Feature importance scores
            model_name: Name of the model
            output_dir: Directory to save plots

        Returns:
            Dictionary with paths to saved plots
        """
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        plot_paths = {}

        # Generate ROC curve
        roc_path = os.path.join(output_dir, f"{model_name}_roc_curve.png")
        self.plot_roc_curve(y_true, y_prob, model_name, roc_path)
        plot_paths["roc_curve"] = roc_path

        # Generate PR curve
        pr_path = os.path.join(output_dir, f"{model_name}_pr_curve.png")
        self.plot_precision_recall_curve(y_true, y_prob, model_name, pr_path)
        plot_paths["pr_curve"] = pr_path

        # Generate calibration curve
        cal_path = os.path.join(output_dir, f"{model_name}_calibration_curve.png")
        self.plot_calibration_curve(y_true, y_prob, model_name, save_path=cal_path)
        plot_paths["calibration_curve"] = cal_path

        # Generate feature importance plot
        feat_path = os.path.join(output_dir, f"{model_name}_feature_importance.png")
        self.plot_feature_importance(
            feature_names, importance_scores, model_name, save_path=feat_path
        )
        plot_paths["feature_importance"] = feat_path

        # Generate confusion matrix
        cm_path = os.path.join(output_dir, f"{model_name}_confusion_matrix.png")
        self.plot_confusion_matrix(y_true, y_pred, model_name=model_name, save_path=cm_path)
        plot_paths["confusion_matrix"] = cm_path

        print(f"📊 Model evaluation report generated for {model_name}")
        print(f"   Plots saved to: {output_dir}")

        return plot_paths


def plot_xgb_model_evaluation(
    model_dir: str = "models", output_dir: str = "validation/phase2/plots"
) -> dict[str, str]:
    """
    Generate comprehensive evaluation plots for XGBoost model.

    Args:
        model_dir: Directory containing XGBoost model artifacts
        output_dir: Directory to save evaluation plots

    Returns:
        Dictionary with paths to saved plots
    """
    # Load model artifacts
    model_path = os.path.join(model_dir, "xgb_model.joblib")
    scaler_path = os.path.join(model_dir, "scaler.joblib")
    metadata_path = os.path.join(model_dir, "metadata.json")

    if not all(os.path.exists(p) for p in [model_path, scaler_path, metadata_path]):
        print("❌ XGBoost model artifacts not found. Please train the model first.")
        return {}

    # Load artifacts
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    with open(metadata_path) as f:
        metadata = json.load(f)

    # Generate synthetic test data (in practice, use real test data)
    np.random.seed(42)
    n_test = 1000

    # Generate test features
    test_features = np.random.randn(n_test, len(metadata["feature_names"]))
    test_features[:, 0] = np.random.exponential(500, n_test)  # amount
    test_features[:, 1] = np.random.poisson(3, n_test)  # velocity_24h
    test_features[:, 2] = np.random.binomial(1, 0.3, n_test)  # cross_border

    # Generate test labels
    test_labels = (
        (test_features[:, 0] > 1000) * 0.3
        + (test_features[:, 1] > 5) * 0.2
        + (test_features[:, 2] == 1) * 0.1
        + np.random.normal(0, 0.1, n_test)
    ) > 0.5

    # Scale features
    test_features_scaled = scaler.transform(test_features)

    # Make predictions
    test_proba = model.predict_proba(test_features_scaled)[:, 1]
    test_pred = (test_proba > 0.5).astype(int)

    # Get feature importance
    feature_importance = model.feature_importances_

    # Generate plots
    plotter = MLPlotter()
    plot_paths = plotter.generate_model_report(
        y_true=test_labels,
        y_pred=test_pred,
        y_prob=test_proba,
        feature_names=metadata["feature_names"],
        importance_scores=feature_importance,
        model_name="XGBoost",
        output_dir=output_dir,
    )

    return plot_paths


if __name__ == "__main__":
    # Example usage
    plotter = MLPlotter()

    # Generate XGBoost evaluation plots
    plot_paths = plot_xgb_model_evaluation()

    if plot_paths:
        print("✅ XGBoost model evaluation plots generated successfully!")
        for plot_type, path in plot_paths.items():
            print(f"   {plot_type}: {path}")
    else:
        print("❌ Failed to generate evaluation plots. Please train the XGBoost model first.")
