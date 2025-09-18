"""Tests for the Orca Core CLI module."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from orca_core.cli import app


class TestCLI:
    """Test the CLI functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_decide_command_with_json_string(self):
        """Test the decide command with a JSON string."""
        json_input = '{"cart_total": 100.0, "currency": "USD"}'
        result = self.runner.invoke(app, ["decide", json_input])

        assert result.exit_code == 0
        assert "decision" in result.stdout.lower()
        assert "APPROVE" in result.stdout

    def test_decide_command_with_rail_override(self):
        """Test the decide command with rail override."""
        json_input = '{"cart_total": 100.0, "currency": "USD"}'
        result = self.runner.invoke(app, ["decide", json_input, "--rail", "ACH"])

        assert result.exit_code == 0
        assert "decision" in result.stdout.lower()

    def test_decide_command_with_channel_override(self):
        """Test the decide command with channel override."""
        json_input = '{"cart_total": 100.0, "currency": "USD"}'
        result = self.runner.invoke(app, ["decide", json_input, "--channel", "pos"])

        assert result.exit_code == 0
        assert "decision" in result.stdout.lower()

    def test_decide_command_with_invalid_json(self):
        """Test the decide command with invalid JSON."""
        result = self.runner.invoke(app, ["decide", "invalid json"])

        assert result.exit_code == 1
        assert "Invalid JSON" in result.stdout

    def test_decide_command_with_mode_override(self):
        """Test the decide command with mode override."""
        json_input = '{"cart_total": 100.0, "currency": "USD"}'
        result = self.runner.invoke(app, ["decide", json_input, "--mode", "rules"])

        assert result.exit_code == 0
        assert "decision" in result.stdout.lower()

    def test_decide_command_with_ai_mode_override(self):
        """Test the decide command with AI mode override."""
        json_input = '{"cart_total": 100.0, "currency": "USD"}'
        result = self.runner.invoke(app, ["decide", json_input, "--mode", "ai"])

        assert result.exit_code == 0
        assert "decision" in result.stdout.lower()

    def test_decide_command_with_invalid_mode(self):
        """Test the decide command with invalid mode."""
        json_input = '{"cart_total": 100.0, "currency": "USD"}'
        result = self.runner.invoke(app, ["decide", json_input, "--mode", "invalid"])

        assert result.exit_code == 1
        assert "Invalid mode: invalid. Use 'rules' or 'ai'" in result.stdout

    def test_decide_command_with_ml_override(self):
        """Test the decide command with ML engine override."""
        json_input = '{"cart_total": 100.0, "currency": "USD"}'
        result = self.runner.invoke(app, ["decide", json_input, "--ml", "stub"])

        assert result.exit_code == 0
        assert "decision" in result.stdout.lower()

    def test_decide_command_with_xgb_ml_override(self):
        """Test the decide command with XGBoost ML engine override."""
        json_input = '{"cart_total": 100.0, "currency": "USD"}'
        result = self.runner.invoke(app, ["decide", json_input, "--ml", "xgb"])

        assert result.exit_code == 0
        assert "decision" in result.stdout.lower()

    def test_decide_command_with_invalid_ml(self):
        """Test the decide command with invalid ML engine."""
        json_input = '{"cart_total": 100.0, "currency": "USD"}'
        result = self.runner.invoke(app, ["decide", json_input, "--ml", "invalid"])

        assert result.exit_code == 1
        assert "Invalid ML engine: invalid. Use 'stub' or 'xgb'" in result.stdout

    def test_decide_command_with_explain_override(self):
        """Test the decide command with explain override."""
        json_input = '{"cart_total": 100.0, "currency": "USD"}'
        result = self.runner.invoke(app, ["decide", json_input, "--explain", "yes"])

        assert result.exit_code == 0
        assert "decision" in result.stdout.lower()

    def test_decide_command_with_explain_false(self):
        """Test the decide command with explain disabled."""
        json_input = '{"cart_total": 100.0, "currency": "USD"}'
        result = self.runner.invoke(app, ["decide", json_input, "--explain", "no"])

        assert result.exit_code == 0
        assert "decision" in result.stdout.lower()

    def test_decide_command_with_invalid_explain(self):
        """Test the decide command with invalid explain value."""
        json_input = '{"cart_total": 100.0, "currency": "USD"}'
        result = self.runner.invoke(app, ["decide", json_input, "--explain", "maybe"])

        assert result.exit_code == 1
        assert "Invalid explain value: maybe. Use 'yes' or 'no'" in result.stdout

    def test_decide_command_with_table_format(self):
        """Test the decide command with table output format."""
        json_input = '{"cart_total": 100.0, "currency": "USD"}'
        result = self.runner.invoke(app, ["decide", json_input, "--format", "table"])

        assert result.exit_code == 0
        assert "Decision Result" in result.stdout

    def test_decide_command_with_empty_input(self):
        """Test the decide command with empty input."""
        result = self.runner.invoke(app, ["decide", ""])

        assert result.exit_code == 1
        assert "No JSON input provided" in result.stdout

    def test_decide_file_command(self):
        """Test the decide-file command."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"cart_total": 100.0, "currency": "USD"}, f)
            temp_file = f.name

        try:
            result = self.runner.invoke(app, ["decide-file", temp_file])
            assert result.exit_code == 0
            assert "decision" in result.stdout.lower()
        finally:
            os.unlink(temp_file)

    def test_decide_file_command_with_overrides(self):
        """Test the decide-file command with overrides."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"cart_total": 100.0, "currency": "USD"}, f)
            temp_file = f.name

        try:
            result = self.runner.invoke(
                app,
                [
                    "decide-file",
                    temp_file,
                    "--mode",
                    "rules",
                    "--ml",
                    "stub",
                    "--explain",
                    "yes",
                    "--rail",
                    "ACH",
                    "--channel",
                    "pos",
                    "--format",
                    "table",
                ],
            )
            assert result.exit_code == 0
            assert "Decision Result" in result.stdout
        finally:
            os.unlink(temp_file)

    def test_decide_file_command_file_not_found(self):
        """Test the decide-file command with non-existent file."""
        result = self.runner.invoke(app, ["decide-file", "nonexistent.json"])

        assert result.exit_code == 1
        assert "File not found" in result.stdout

    def test_decide_file_command_invalid_json(self):
        """Test the decide-file command with invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name

        try:
            result = self.runner.invoke(app, ["decide-file", temp_file])
            assert result.exit_code == 1
            assert "Invalid JSON in file" in result.stdout
        finally:
            os.unlink(temp_file)

    def test_config_command(self):
        """Test the config command."""
        result = self.runner.invoke(app, ["config"])

        assert result.exit_code == 0
        assert "Orca Core Configuration" in result.stdout
        assert "Decision Mode" in result.stdout
        assert "AI Enabled" in result.stdout

    @patch("orca_core.cli.XGBoostTrainer")
    def test_train_xgb_command(self, mock_trainer):
        """Test the train-xgb command."""
        mock_instance = MagicMock()
        mock_instance.train_and_save.return_value = {
            "auc_score": 0.85,
            "log_loss": 0.45,
            "feature_importance": {"feature1": 0.3, "feature2": 0.2, "feature3": 0.1},
        }
        mock_trainer.return_value = mock_instance

        result = self.runner.invoke(
            app, ["train-xgb", "--samples", "1000", "--model-dir", "test_models"]
        )

        assert result.exit_code == 0
        assert "Training XGBoost model" in result.stdout
        assert "AUC Score: 0.8500" in result.stdout
        assert "Log Loss: 0.4500" in result.stdout
        assert "Top 5 Most Important Features" in result.stdout

    @patch("orca_core.cli.XGBoostTrainer")
    def test_train_xgb_command_failure(self, mock_trainer):
        """Test the train-xgb command with training failure."""
        mock_instance = MagicMock()
        mock_instance.train_and_save.side_effect = Exception("Training failed")
        mock_trainer.return_value = mock_instance

        result = self.runner.invoke(app, ["train-xgb"])

        assert result.exit_code == 1
        assert "Training failed" in result.stdout

    @patch("orca_core.cli.get_model_info")
    def test_model_info_command(self, mock_get_model_info):
        """Test the model-info command."""
        mock_get_model_info.return_value = {
            "model_type": "xgboost",
            "version": "1.0.0",
            "status": "trained",
            "features": 10,
            "training_date": "2024-01-01",
            "auc_score": 0.85,
        }

        result = self.runner.invoke(app, ["model-info"])

        assert result.exit_code == 0
        assert "ML Model Information" in result.stdout
        assert "Model Type: xgboost" in result.stdout
        assert "Version: 1.0.0" in result.stdout

    @patch("orca_core.cli.get_model_info")
    def test_model_info_command_stub_model(self, mock_get_model_info):
        """Test the model-info command with stub model."""
        mock_get_model_info.return_value = {
            "model_type": "stub",
            "version": "1.0.0",
            "status": "active",
            "description": "Stub model for testing",
            "features": ["feature1", "feature2"],
        }

        result = self.runner.invoke(app, ["model-info"])

        assert result.exit_code == 0
        assert "ML Model Information" in result.stdout
        assert "Model Type: stub" in result.stdout
        assert "Description: Stub model for testing" in result.stdout

    @patch("orca_core.cli.get_model_info")
    def test_model_info_command_failure(self, mock_get_model_info):
        """Test the model-info command with failure."""
        mock_get_model_info.side_effect = Exception("Model info failed")

        result = self.runner.invoke(app, ["model-info"])

        assert result.exit_code == 1
        assert "Failed to get model info" in result.stdout

    @patch("subprocess.run")
    def test_debug_ui_command(self, mock_subprocess):
        """Test the debug-ui command."""
        result = self.runner.invoke(app, ["debug-ui", "--port", "8502", "--host", "0.0.0.0"])

        assert result.exit_code == 0
        assert "Launching Orca Core Debug UI" in result.stdout
        mock_subprocess.assert_called_once()

    @patch("subprocess.run")
    def test_debug_ui_command_keyboard_interrupt(self, mock_subprocess):
        """Test the debug-ui command with keyboard interrupt."""
        mock_subprocess.side_effect = KeyboardInterrupt()

        result = self.runner.invoke(app, ["debug-ui"])

        assert result.exit_code == 0
        assert "Debug UI stopped" in result.stdout

    @patch("subprocess.run")
    def test_debug_ui_command_failure(self, mock_subprocess):
        """Test the debug-ui command with failure."""
        mock_subprocess.side_effect = Exception("Streamlit not found")

        result = self.runner.invoke(app, ["debug-ui"])

        assert result.exit_code == 1
        assert "Failed to launch debug UI" in result.stdout

    def test_explain_command(self):
        """Test the explain command."""
        json_input = '{"cart_total": 100.0, "currency": "USD"}'
        result = self.runner.invoke(app, ["explain", json_input])

        assert result.exit_code == 0
        # The exact output depends on the explanation logic

    def test_explain_command_invalid_json(self):
        """Test the explain command with invalid JSON."""
        result = self.runner.invoke(app, ["explain", "invalid json"])

        assert result.exit_code == 1
        assert "Invalid JSON" in result.stdout

    def test_decide_batch_command_no_files(self):
        """Test the decide-batch command with no matching files."""
        result = self.runner.invoke(app, ["decide-batch", "--glob", "nonexistent/*.json"])

        assert result.exit_code == 0
        assert "No files found matching pattern" in result.stdout

    def test_decide_batch_command_with_files(self):
        """Test the decide-batch command with matching files."""
        # Create temporary test files
        test_files = []
        try:
            for i in range(2):
                with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                    json.dump({"cart_total": 100.0 + i, "currency": "USD"}, f)
                    test_files.append(f.name)

            # Create a glob pattern that matches our test files
            glob_pattern = f"{Path(test_files[0]).parent}/*.json"

            result = self.runner.invoke(
                app,
                [
                    "decide-batch",
                    "--glob",
                    glob_pattern,
                    "--format",
                    "csv",
                    "--output",
                    "test_output.csv",
                ],
            )

            assert result.exit_code == 0
            assert "Processing" in result.stdout
            assert "CSV output written to" in result.stdout

        finally:
            # Clean up test files
            for file_path in test_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            if os.path.exists("test_output.csv"):
                os.unlink("test_output.csv")

    def test_decide_batch_command_json_format(self):
        """Test the decide-batch command with JSON output format."""
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"cart_total": 100.0, "currency": "USD"}, f)
            temp_file = f.name

        try:
            result = self.runner.invoke(
                app, ["decide-batch", "--glob", temp_file, "--format", "json"]
            )

            assert result.exit_code == 0
            assert "JSON output written to" in result.stdout

        finally:
            os.unlink(temp_file)

    def test_decide_batch_command_with_overrides(self):
        """Test the decide-batch command with mode and ML overrides."""
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"cart_total": 100.0, "currency": "USD"}, f)
            temp_file = f.name

        try:
            result = self.runner.invoke(
                app,
                [
                    "decide-batch",
                    "--glob",
                    temp_file,
                    "--mode",
                    "rules",
                    "--ml",
                    "stub",
                    "--explain",
                    "yes",
                ],
            )

            assert result.exit_code == 0
            assert "Processing" in result.stdout

        finally:
            os.unlink(temp_file)

    def test_decide_batch_command_invalid_mode(self):
        """Test the decide-batch command with invalid mode."""
        result = self.runner.invoke(app, ["decide-batch", "--mode", "invalid"])

        assert result.exit_code == 1
        assert "Invalid mode" in result.stdout

    def test_decide_batch_command_invalid_ml(self):
        """Test the decide-batch command with invalid ML engine."""
        result = self.runner.invoke(app, ["decide-batch", "--ml", "invalid"])

        assert result.exit_code == 1
        assert "Invalid ML engine" in result.stdout

    def test_decide_batch_command_invalid_explain(self):
        """Test the decide-batch command with invalid explain value."""
        result = self.runner.invoke(app, ["decide-batch", "--explain", "maybe"])

        assert result.exit_code == 1
        assert "Invalid explain value" in result.stdout

    @patch("orca_core.core.ml_hooks.train_model")
    @patch("orca_core.core.ml_hooks.get_model")
    def test_train_command(self, mock_get_model, mock_train_model):
        """Test the train command."""
        mock_model = MagicMock()
        mock_model.get_feature_importance.return_value = {
            "feature1": 0.3,
            "feature2": 0.2,
            "feature3": 0.1,
        }
        mock_get_model.return_value = mock_model

        result = self.runner.invoke(app, ["train", "--samples", "1000"])

        assert result.exit_code == 0
        assert "Generating 1000 synthetic training samples" in result.stdout
        assert "Training Random Forest model" in result.stdout
        assert "Feature Importance" in result.stdout

    def test_train_command_with_data_file(self):
        """Test the train command with data file (should fail gracefully)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("feature1,feature2,target\n1,2,0\n3,4,1")
            temp_file = f.name

        try:
            result = self.runner.invoke(app, ["train", "--data", temp_file])

            assert result.exit_code == 1
            assert "CSV data loading not yet implemented" in result.stdout

        finally:
            os.unlink(temp_file)

    @patch("orca_core.cli.plot_xgb_model_evaluation")
    def test_generate_plots_command(self, mock_plot):
        """Test the generate-plots command."""
        mock_plot.return_value = {
            "roc_curve": "plots/roc_curve.png",
            "feature_importance": "plots/feature_importance.png",
        }

        result = self.runner.invoke(
            app, ["generate-plots", "--model-dir", "test_models", "--output-dir", "test_plots"]
        )

        assert result.exit_code == 0
        assert "Generating ML model evaluation plots" in result.stdout
        assert "Model evaluation plots generated successfully" in result.stdout

    @patch("orca_core.cli.plot_xgb_model_evaluation")
    def test_generate_plots_command_failure(self, mock_plot):
        """Test the generate-plots command with failure."""
        mock_plot.return_value = None

        result = self.runner.invoke(app, ["generate-plots"])

        assert result.exit_code == 1
        assert "Failed to generate evaluation plots" in result.stdout

    @patch("orca_core.cli.plot_xgb_model_evaluation")
    def test_generate_plots_command_exception(self, mock_plot):
        """Test the generate-plots command with exception."""
        mock_plot.side_effect = Exception("Plot generation failed")

        result = self.runner.invoke(app, ["generate-plots"])

        assert result.exit_code == 1
        assert "Error generating plots" in result.stdout

    def test_decide_command_with_stdin(self):
        """Test the decide command reading from stdin."""
        json_input = '{"cart_total": 100.0, "currency": "USD"}'
        result = self.runner.invoke(app, ["decide", "-"], input=json_input)

        assert result.exit_code == 0
        assert "decision" in result.stdout.lower()

    def test_decide_file_command_with_valid_file(self):
        """Test the decide-file command with a valid JSON file."""
        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"cart_total": 100.0, "currency": "USD"}, f)
            temp_file = f.name

        try:
            result = self.runner.invoke(app, ["decide-file", temp_file])

            assert result.exit_code == 0
            assert "decision" in result.stdout.lower()
        finally:
            Path(temp_file).unlink()

    def test_decide_file_command_with_rail_override(self):
        """Test the decide-file command with rail override."""
        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"cart_total": 100.0, "currency": "USD"}, f)
            temp_file = f.name

        try:
            result = self.runner.invoke(app, ["decide-file", temp_file, "--rail", "ACH"])

            assert result.exit_code == 0
            assert "decision" in result.stdout.lower()
        finally:
            Path(temp_file).unlink()

    def test_decide_file_command_with_channel_override(self):
        """Test the decide-file command with channel override."""
        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"cart_total": 100.0, "currency": "USD"}, f)
            temp_file = f.name

        try:
            result = self.runner.invoke(app, ["decide-file", temp_file, "--channel", "pos"])

            assert result.exit_code == 0
            assert "decision" in result.stdout.lower()
        finally:
            Path(temp_file).unlink()

    def test_decide_file_command_with_nonexistent_file(self):
        """Test the decide-file command with a nonexistent file."""
        result = self.runner.invoke(app, ["decide-file", "nonexistent.json"])

        assert result.exit_code == 1
        assert "File not found" in result.stdout

    def test_decide_file_command_with_invalid_json(self):
        """Test the decide-file command with invalid JSON in file."""
        # Create a temporary file with invalid JSON
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name

        try:
            result = self.runner.invoke(app, ["decide-file", temp_file])

            assert result.exit_code == 1
            assert "Invalid JSON in file" in result.stdout
        finally:
            Path(temp_file).unlink()

    def test_decide_batch_command_with_existing_files(self):
        """Test the decide-batch command with existing fixture files."""
        # Use the existing fixture files
        result = self.runner.invoke(app, ["decide-batch", "--glob", "fixtures/requests/*.json"])

        assert result.exit_code == 0
        assert "Processing" in result.stdout

    def test_decide_batch_command_with_no_files(self):
        """Test the decide-batch command with no matching files."""
        result = self.runner.invoke(app, ["decide-batch", "--glob", "nonexistent/*.json"])

        assert result.exit_code == 0
        assert "No files found" in result.stdout

    def test_decide_batch_command_with_custom_glob(self):
        """Test the decide-batch command with custom glob pattern."""
        # Create a temporary directory with JSON files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test JSON files
            for i in range(3):
                test_file = temp_path / f"test_{i}.json"
                with open(test_file, "w") as f:
                    json.dump({"cart_total": 100.0 + i * 50, "currency": "USD"}, f)

            result = self.runner.invoke(app, ["decide-batch", "--glob", str(temp_path / "*.json")])

            assert result.exit_code == 0
            assert "Processing 3 files" in result.stdout

    def test_explain_command_with_valid_json(self):
        """Test the explain command with valid JSON."""
        json_input = '{"cart_total": 100.0, "currency": "USD"}'
        result = self.runner.invoke(app, ["explain", json_input])

        assert result.exit_code == 0
        assert "decision" in result.stdout.lower()

    def test_explain_command_with_high_ticket(self):
        """Test the explain command with high ticket amount."""
        json_input = '{"cart_total": 750.0, "currency": "USD"}'
        result = self.runner.invoke(app, ["explain", json_input])

        assert result.exit_code == 0
        assert "decision" in result.stdout.lower()

    def test_explain_command_with_velocity(self):
        """Test the explain command with velocity features."""
        json_input = '{"cart_total": 100.0, "features": {"velocity_24h": 5.0}}'
        result = self.runner.invoke(app, ["explain", json_input])

        assert result.exit_code == 0
        assert "decision" in result.stdout.lower()

    def test_explain_command_with_invalid_json(self):
        """Test the explain command with invalid JSON."""
        result = self.runner.invoke(app, ["explain", "invalid json"])

        assert result.exit_code == 1
        assert "Invalid JSON" in result.stdout

    def test_help_command(self):
        """Test that help command works."""
        result = self.runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Orca Core Decision Engine CLI" in result.stdout

    def test_decide_help_command(self):
        """Test that decide command help works."""
        result = self.runner.invoke(app, ["decide", "--help"])

        assert result.exit_code == 0
        assert "Evaluate a decision request" in result.stdout

    def test_decide_file_help_command(self):
        """Test that decide-file command help works."""
        result = self.runner.invoke(app, ["decide-file", "--help"])

        assert result.exit_code == 0
        assert "Evaluate a decision request from a JSON file" in result.stdout

    def test_decide_batch_help_command(self):
        """Test that decide-batch command help works."""
        result = self.runner.invoke(app, ["decide-batch", "--help"])

        assert result.exit_code == 0
        assert "Evaluate decision requests from multiple JSON files" in result.stdout

    def test_explain_help_command(self):
        """Test that explain command help works."""
        result = self.runner.invoke(app, ["explain", "--help"])

        assert result.exit_code == 0
        assert "Explain a decision request in plain English" in result.stdout

    def test_cli_with_fixtures(self):
        """Test CLI with existing fixtures."""
        # Test with an existing fixture file
        result = self.runner.invoke(app, ["decide-file", "fixtures/requests/low_ticket_ok.json"])

        assert result.exit_code == 0
        assert "decision" in result.stdout.lower()

    def test_cli_error_handling(self):
        """Test CLI error handling with various edge cases."""
        # Test with missing required fields
        result = self.runner.invoke(app, ["decide", '{"currency": "USD"}'])

        assert result.exit_code == 1
        assert "Error" in result.stdout

    def test_cli_with_complex_request(self):
        """Test CLI with a complex request including features and context."""
        complex_request = {
            "cart_total": 500.0,
            "currency": "USD",
            "rail": "Card",
            "channel": "online",
            "features": {"velocity_24h": 2.0, "velocity_7d": 8.0},
            "context": {"user_id": "test_user", "ip_address": "192.168.1.1"},
        }

        result = self.runner.invoke(app, ["decide", json.dumps(complex_request)])

        assert result.exit_code == 0
        assert "decision" in result.stdout.lower()

    def test_cli_output_format(self):
        """Test that CLI output is properly formatted JSON."""
        json_input = '{"cart_total": 100.0, "currency": "USD"}'
        result = self.runner.invoke(app, ["decide", json_input])

        assert result.exit_code == 0

        # Clean the output by removing newlines and extra whitespace
        cleaned_output = result.stdout.strip().replace("\n", "")

        # Try to parse the output as JSON
        try:
            output_json = json.loads(cleaned_output)
            assert "decision" in output_json
            assert "reasons" in output_json
            assert "actions" in output_json
            assert "meta" in output_json
        except json.JSONDecodeError:
            pytest.fail("CLI output is not valid JSON")

    def test_cli_with_ach_rail(self):
        """Test CLI with ACH rail."""
        json_input = '{"cart_total": 100.0, "currency": "USD", "rail": "ACH"}'
        result = self.runner.invoke(app, ["decide", json_input])

        assert result.exit_code == 0
        assert "decision" in result.stdout.lower()

    def test_cli_with_pos_channel(self):
        """Test CLI with POS channel."""
        json_input = '{"cart_total": 100.0, "currency": "USD", "channel": "pos"}'
        result = self.runner.invoke(app, ["decide", json_input])

        assert result.exit_code == 0
        assert "decision" in result.stdout.lower()
