"""
Tests for src.orca_core.ml.plotting module.
"""

import os
import tempfile
from unittest.mock import Mock, patch

import numpy as np

from src.orca_core.ml.plotting import MLPlotter, plot_xgb_model_evaluation


class TestMLPlotter:
    """Test cases for MLPlotter class."""

    def test_init(self):
        """Test MLPlotter initialization."""
        plotter = MLPlotter()
        assert plotter.model_dir == "models"

        plotter = MLPlotter(model_dir="custom_models")
        assert plotter.model_dir == "custom_models"

    @patch("src.orca_core.ml.plotting.plt")
    @patch("src.orca_core.ml.plotting.sns")
    def test_setup_style(self, mock_sns, mock_plt):
        """Test setup_style method."""
        plotter = MLPlotter()
        plotter.setup_style()

        mock_plt.style.use.assert_called_with("seaborn-v0_8")
        mock_sns.set_palette.assert_called_with("husl")

    @patch("src.orca_core.ml.plotting.plt")
    def test_plot_roc_curve(self, mock_plt):
        """Test plot_roc_curve method."""
        # Setup mock
        mock_fig = Mock()
        mock_ax = Mock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        plotter = MLPlotter()

        # Generate test data
        y_true = np.array([0, 0, 1, 1])
        y_scores = np.array([0.1, 0.4, 0.35, 0.8])

        result = plotter.plot_roc_curve(y_true, y_scores, "Test Model")

        assert result == mock_fig
        mock_plt.subplots.assert_called_once()
        mock_ax.plot.assert_called()
        mock_ax.set_title.assert_called()

    @patch("src.orca_core.ml.plotting.plt")
    def test_plot_precision_recall_curve(self, mock_plt):
        """Test plot_precision_recall_curve method."""
        # Setup mock
        mock_fig = Mock()
        mock_ax = Mock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        plotter = MLPlotter()

        # Generate test data
        y_true = np.array([0, 0, 1, 1])
        y_scores = np.array([0.1, 0.4, 0.35, 0.8])

        result = plotter.plot_precision_recall_curve(y_true, y_scores, "Test Model")

        assert result == mock_fig
        mock_plt.subplots.assert_called_once()
        mock_ax.plot.assert_called()
        mock_ax.set_title.assert_called()

    @patch("src.orca_core.ml.plotting.plt")
    @patch("src.orca_core.ml.plotting.sns")
    def test_plot_confusion_matrix(self, mock_sns, mock_plt):
        """Test plot_confusion_matrix method."""
        # Setup mock
        mock_fig = Mock()
        mock_ax = Mock()
        mock_ax.spines = {"top": Mock(), "right": Mock(), "left": Mock(), "bottom": Mock()}
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        plotter = MLPlotter()

        # Generate test data
        y_true = np.array([0, 0, 1, 1])
        y_pred = np.array([0, 1, 0, 1])

        result = plotter.plot_confusion_matrix(y_true, y_pred, "Test Model")

        assert result == mock_fig
        mock_plt.subplots.assert_called_once()
        mock_sns.heatmap.assert_called_once()

    @patch("src.orca_core.ml.plotting.plt")
    def test_plot_calibration_curve(self, mock_plt):
        """Test plot_calibration_curve method."""
        # Setup mock
        mock_fig = Mock()
        mock_ax = Mock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        plotter = MLPlotter()

        # Generate test data
        y_true = np.array([0, 0, 1, 1])
        y_prob = np.array([0.1, 0.4, 0.35, 0.8])

        result = plotter.plot_calibration_curve(y_true, y_prob, "Test Model")

        assert result == mock_fig
        mock_plt.subplots.assert_called_once()

    @patch("src.orca_core.ml.plotting.plt")
    def test_plot_feature_importance(self, mock_plt):
        """Test plot_feature_importance method."""
        # Setup mock
        mock_fig = Mock()
        mock_ax = Mock()
        mock_bar1 = Mock()
        mock_bar1.get_width.return_value = 0.5
        mock_bar1.get_y.return_value = 0
        mock_bar1.get_height.return_value = 0.2
        mock_bar2 = Mock()
        mock_bar2.get_width.return_value = 0.3
        mock_bar2.get_y.return_value = 0.2
        mock_bar2.get_height.return_value = 0.2
        mock_ax.barh.return_value = [mock_bar1, mock_bar2]
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        plotter = MLPlotter()

        # Generate test data
        feature_names = ["feature1", "feature2", "feature3"]
        importance_scores = np.array([0.5, 0.3, 0.2])

        result = plotter.plot_feature_importance(feature_names, importance_scores, "Test Model")

        assert result == mock_fig
        mock_plt.subplots.assert_called_once()
        mock_ax.barh.assert_called_once()

    @patch("src.orca_core.ml.plotting.plt")
    @patch("src.orca_core.ml.plotting.sns")
    def test_generate_model_report(self, mock_sns, mock_plt):
        """Test generate_model_report method."""
        # Setup mock
        mock_fig = Mock()
        mock_ax = Mock()
        mock_ax.spines = {"top": Mock(), "right": Mock(), "left": Mock(), "bottom": Mock()}
        mock_bar1 = Mock()
        mock_bar1.get_width.return_value = 0.6
        mock_bar1.get_y.return_value = 0
        mock_bar1.get_height.return_value = 0.2
        mock_ax.barh.return_value = [mock_bar1]
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        plotter = MLPlotter()

        # Generate test data
        y_true = np.array([0, 0, 1, 1])
        y_pred = np.array([0, 1, 0, 1])
        y_prob = np.array([0.1, 0.4, 0.35, 0.8])
        feature_names = ["feature1", "feature2"]
        importance_scores = np.array([0.6, 0.4])

        with tempfile.TemporaryDirectory() as temp_dir:
            result = plotter.generate_model_report(
                y_true=y_true,
                y_pred=y_pred,
                y_prob=y_prob,
                feature_names=feature_names,
                importance_scores=importance_scores,
                model_name="Test Model",
                output_dir=temp_dir,
            )

            assert isinstance(result, dict)
            assert "roc_curve" in result
            assert "pr_curve" in result
            assert "confusion_matrix" in result
            assert "calibration_curve" in result
            assert "feature_importance" in result


@patch("src.orca_core.ml.plotting.os.path.exists")
@patch("src.orca_core.ml.plotting.joblib.load")
@patch("builtins.open")
@patch("json.load")
@patch("src.orca_core.ml.plotting.plt")
def test_plot_xgb_model_evaluation_no_model(
    mock_plt, mock_json_load, mock_open, mock_joblib_load, mock_exists
):
    """Test plot_xgb_model_evaluation when model doesn't exist."""
    mock_exists.return_value = False

    result = plot_xgb_model_evaluation()

    assert result == {}


def test_plot_model_comparison():
    """Test plot_model_comparison method."""
    with patch("src.orca_core.ml.plotting.plt") as mock_plt:
        # Mock matplotlib components
        mock_fig = Mock()
        mock_ax = Mock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        # Mock bar plot
        mock_bars = [Mock(), Mock()]
        mock_ax.bar.return_value = mock_bars
        mock_bars[0].get_height.return_value = 0.85
        mock_bars[0].get_x.return_value = 0.1
        mock_bars[0].get_width.return_value = 0.8
        mock_bars[1].get_height.return_value = 0.92
        mock_bars[1].get_x.return_value = 0.1
        mock_bars[1].get_width.return_value = 0.8

        plotter = MLPlotter()

        # Test data
        results = {"Model A": {"auc": 0.85}, "Model B": {"auc": 0.92}}

        result = plotter.plot_model_comparison(results, "auc")

        # Verify calls
        mock_plt.subplots.assert_called_once_with(figsize=(10, 6))
        mock_ax.bar.assert_called_once()
        mock_ax.set_ylabel.assert_called_once_with("AUC Score", fontsize=14)
        mock_ax.set_title.assert_called_once_with(
            "Model Comparison - AUC", fontsize=16, fontweight="bold"
        )
        mock_ax.grid.assert_called_once_with(True, alpha=0.3, axis="y")
        mock_plt.xticks.assert_called_once_with(rotation=45, ha="right")
        mock_plt.tight_layout.assert_called_once()

        assert result == mock_fig


def test_plot_model_comparison_with_save():
    """Test plot_model_comparison method with save_path."""
    with patch("src.orca_core.ml.plotting.plt") as mock_plt:
        # Mock matplotlib components
        mock_fig = Mock()
        mock_ax = Mock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        # Mock bar plot
        mock_bars = [Mock()]
        mock_ax.bar.return_value = mock_bars
        mock_bars[0].get_height.return_value = 0.85
        mock_bars[0].get_x.return_value = 0.1
        mock_bars[0].get_width.return_value = 0.8

        plotter = MLPlotter()

        # Test data
        results = {"Model A": {"precision": 0.85}}

        with patch("builtins.print") as mock_print:
            result = plotter.plot_model_comparison(results, "precision", save_path="test.png")

            # Verify save was called
            mock_plt.savefig.assert_called_once_with("test.png", dpi=300, bbox_inches="tight")
            mock_print.assert_called_once_with("📊 Model comparison plot saved to: test.png")

            assert result == mock_fig


@patch("src.orca_core.ml.plotting.os.path.exists")
@patch("src.orca_core.ml.plotting.joblib.load")
@patch("builtins.open")
@patch("json.load")
@patch("src.orca_core.ml.plotting.plt")
@patch("src.orca_core.ml.plotting.sns")
def test_plot_xgb_model_evaluation_with_model(
    mock_sns, mock_plt, mock_json_load, mock_open, mock_joblib_load, mock_exists
):
    """Test plot_xgb_model_evaluation with existing model."""
    # Setup mocks
    mock_exists.return_value = True

    mock_model = Mock()
    # Return probabilities for 1000 samples to match test data size
    np.random.seed(42)
    mock_proba = np.random.rand(1000, 2)
    mock_proba = mock_proba / mock_proba.sum(axis=1, keepdims=True)  # Normalize
    mock_model.predict_proba.return_value = mock_proba
    mock_model.feature_importances_ = np.array([0.5, 0.3, 0.2])

    mock_scaler = Mock()
    mock_scaler.transform.return_value = np.random.randn(1000, 3)

    mock_joblib_load.side_effect = [mock_model, mock_scaler]

    mock_json_load.return_value = {"feature_names": ["amount", "velocity_24h", "cross_border"]}

    mock_fig = Mock()
    mock_ax = Mock()
    mock_ax.spines = {"top": Mock(), "right": Mock(), "left": Mock(), "bottom": Mock()}
    mock_bar1 = Mock()
    mock_bar1.get_width.return_value = 0.5
    mock_bar1.get_y.return_value = 0
    mock_bar1.get_height.return_value = 0.2
    mock_ax.barh.return_value = [mock_bar1]
    mock_plt.subplots.return_value = (mock_fig, mock_ax)

    with tempfile.TemporaryDirectory() as temp_dir:
        result = plot_xgb_model_evaluation(output_dir=temp_dir)

        assert isinstance(result, dict)
        # Should contain plot paths
        expected_keys = [
            "roc_curve",
            "pr_curve",
            "confusion_matrix",
            "calibration_curve",
            "feature_importance",
        ]
        for key in expected_keys:
            assert key in result


def test_plot_roc_curve_with_save():
    """Test plot_roc_curve with save functionality."""
    with patch("src.orca_core.ml.plotting.plt") as mock_plt:
        mock_fig = Mock()
        mock_ax = Mock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        plotter = MLPlotter()

        # Generate test data
        y_true = np.array([0, 0, 1, 1])
        y_scores = np.array([0.1, 0.4, 0.35, 0.8])

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            plotter.plot_roc_curve(y_true, y_scores, "Test Model", save_path=temp_path)
            mock_plt.savefig.assert_called_with(temp_path, dpi=300, bbox_inches="tight")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


def test_plot_precision_recall_curve_with_save():
    """Test plot_precision_recall_curve with save functionality."""
    with patch("src.orca_core.ml.plotting.plt") as mock_plt:
        mock_fig = Mock()
        mock_ax = Mock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        plotter = MLPlotter()

        # Generate test data
        y_true = np.array([0, 0, 1, 1])
        y_scores = np.array([0.1, 0.4, 0.35, 0.8])

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            plotter.plot_precision_recall_curve(y_true, y_scores, "Test Model", save_path=temp_path)
            mock_plt.savefig.assert_called_with(temp_path, dpi=300, bbox_inches="tight")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


def test_mlplotter_main_execution():
    """Test the main execution block."""
    with patch("src.orca_core.ml.plotting.plot_xgb_model_evaluation") as mock_plot_func:
        # Test successful execution
        mock_plot_func.return_value = {
            "roc_curve": "/path/to/roc.png",
            "pr_curve": "/path/to/pr.png",
        }

        # Import the module to trigger main execution
        import src.orca_core.ml.plotting

        # Test failed execution
        mock_plot_func.return_value = {}

        # Re-import to test the failure case
        import importlib

        importlib.reload(src.orca_core.ml.plotting)
