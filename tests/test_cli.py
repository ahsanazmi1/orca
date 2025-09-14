"""Tests for the Orca Core CLI module."""

import json
import tempfile
from pathlib import Path

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

    def test_decide_command_with_empty_input(self):
        """Test the decide command with empty input."""
        result = self.runner.invoke(app, ["decide", ""])

        assert result.exit_code == 1
        assert "No JSON input provided" in result.stdout

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
