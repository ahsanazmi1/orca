"""Integration tests for AP2 CLI functionality."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest


class TestAP2CLIIntegration:
    """Integration tests for AP2 CLI commands."""

    def setup_method(self):
        """Set up test environment."""
        self.cli_module = "src.orca.cli"
        self.golden_file = Path("tests/golden/decision.ap2.json")

    def create_sample_ap2_contract(self) -> dict[str, Any]:
        """Create a sample AP2 contract for testing."""
        return {
            "ap2_version": "0.1.0",
            "intent": {
                "actor": "human",
                "intent_type": "purchase",
                "channel": "web",
                "agent_presence": "assisted",
                "timestamps": {
                    "created": "2023-01-01T00:00:00Z",
                    "expires": "2023-01-01T23:59:59Z",
                },
            },
            "cart": {
                "items": [
                    {
                        "id": "test_item_1",
                        "name": "Test Product",
                        "quantity": 1,
                        "unit_price": "100.00",
                        "total_price": "100.00",
                    }
                ],
                "amount": "100.00",
                "currency": "USD",
                "mcc": "5733",
                "geo": {
                    "country": "US",
                },
            },
            "payment": {
                "instrument_ref": "test_card_123456789",
                "modality": "immediate",
                "auth_requirements": ["pin"],
            },
            "decision": {
                "result": "APPROVE",
                "risk_score": 0.1,
                "reasons": [],
                "actions": [],
                "meta": {
                    "model": "rules_only",
                    "trace_id": "test-trace-123",
                    "version": "0.1.0",
                },
            },
            "signing": {
                "vc_proof": None,
                "receipt_hash": None,
            },
        }

    def run_cli_command(self, args: list, input_data: str = None) -> subprocess.CompletedProcess:
        """Run a CLI command and return the result."""
        cmd = ["python", "-m", self.cli_module] + args
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd())
        env["NO_COLOR"] = "1"  # Disable colors to avoid ANSI escape codes

        if input_data:
            return subprocess.run(
                cmd,
                input=input_data,
                text=True,
                capture_output=True,
                cwd=Path.cwd(),
                env=env,
            )
        else:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
                env=env,
            )

    def test_validate_command_valid_file(self):
        """Test validate command with valid AP2 file."""
        # Create temporary file with valid AP2 data
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.create_sample_ap2_contract(), f)
            temp_file = f.name

        try:
            result = self.run_cli_command(["validate", temp_file])

            assert result.returncode == 0
            assert "✅ AP2 contract is valid" in result.stdout
            assert result.stderr == ""

        finally:
            os.unlink(temp_file)

    def test_validate_command_invalid_file(self):
        """Test validate command with invalid AP2 file."""
        # Create temporary file with invalid data
        invalid_data = {"invalid": "data"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(invalid_data, f)
            temp_file = f.name

        try:
            result = self.run_cli_command(["validate", temp_file])

            assert result.returncode == 1
            assert "❌ AP2 contract validation failed" in result.stdout

        finally:
            os.unlink(temp_file)

    def test_validate_command_nonexistent_file(self):
        """Test validate command with nonexistent file."""
        result = self.run_cli_command(["validate", "nonexistent.json"])

        assert result.returncode == 1
        assert "does not exist" in result.stdout

    def test_validate_command_verbose(self):
        """Test validate command with verbose output."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.create_sample_ap2_contract(), f)
            temp_file = f.name

        try:
            result = self.run_cli_command(["validate", temp_file, "--verbose"])

            assert result.returncode == 0
            assert "✅ AP2 contract is valid" in result.stdout
            assert "Contract Summary:" in result.stdout
            assert "AP2 Version:" in result.stdout
            assert "Intent Channel:" in result.stdout

        finally:
            os.unlink(temp_file)

    def test_decide_file_command_ap2_output(self):
        """Test decide-file command with AP2 output."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.create_sample_ap2_contract(), f)
            input_file = f.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_file = f.name

        try:
            result = self.run_cli_command(["decide-file", input_file, "--output", output_file])

            assert result.returncode == 0

            # Check output file exists and contains valid JSON
            with open(output_file) as f:
                output_data = json.load(f)

            assert "ap2_version" in output_data
            assert "intent" in output_data
            assert "cart" in output_data
            assert "payment" in output_data
            assert "decision" in output_data
            assert "signing" in output_data

            # Check decision was processed
            assert output_data["decision"]["result"] in ["APPROVE", "REVIEW", "DECLINE"]
            assert "risk_score" in output_data["decision"]

        finally:
            os.unlink(input_file)
            os.unlink(output_file)

    def test_decide_file_command_legacy_output(self):
        """Test decide-file command with legacy output."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.create_sample_ap2_contract(), f)
            input_file = f.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_file = f.name

        try:
            result = self.run_cli_command(
                ["decide-file", input_file, "--output", output_file, "--legacy-json"]
            )

            assert result.returncode == 0

            # Check output file exists and contains legacy format
            with open(output_file) as f:
                output_data = json.load(f)

            # Legacy format should have different structure
            assert "decision" in output_data
            assert "reasons" in output_data
            assert "actions" in output_data
            assert "meta" in output_data

        finally:
            os.unlink(input_file)
            os.unlink(output_file)

    def test_decide_file_command_with_explanation(self):
        """Test decide-file command with explanation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.create_sample_ap2_contract(), f)
            input_file = f.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_file = f.name

        try:
            result = self.run_cli_command(
                ["decide-file", input_file, "--output", output_file, "--explain"]
            )

            assert result.returncode == 0

            # Check output file contains explanation
            with open(output_file) as f:
                output_data = json.load(f)

            assert "explanation" in output_data
            assert isinstance(output_data["explanation"], str)
            assert len(output_data["explanation"]) > 0

        finally:
            os.unlink(input_file)
            os.unlink(output_file)

    def test_decide_file_command_validate_only(self):
        """Test decide-file command with validate-only flag."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.create_sample_ap2_contract(), f)
            input_file = f.name

        try:
            result = self.run_cli_command(["decide-file", input_file, "--validate-only"])

            assert result.returncode == 0
            assert "✅ AP2 contract is valid" in result.stdout

        finally:
            os.unlink(input_file)

    def test_decide_stdin_command(self):
        """Test decide-stdin command."""
        input_data = json.dumps(self.create_sample_ap2_contract())

        result = self.run_cli_command(["decide-stdin"], input_data=input_data)

        assert result.returncode == 0

        # Parse output JSON
        output_data = json.loads(result.stdout)

        assert "ap2_version" in output_data
        assert "decision" in output_data
        assert output_data["decision"]["result"] in ["APPROVE", "REVIEW", "DECLINE"]

    def test_decide_stdin_command_legacy_output(self):
        """Test decide-stdin command with legacy output."""
        input_data = json.dumps(self.create_sample_ap2_contract())

        result = self.run_cli_command(["decide-stdin", "--legacy-json"], input_data=input_data)

        assert result.returncode == 0

        # Parse output JSON
        output_data = json.loads(result.stdout)

        # Should be legacy format
        assert "decision" in output_data
        assert "reasons" in output_data
        assert "actions" in output_data

    def test_create_sample_command(self):
        """Test create-sample command."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_file = f.name

        try:
            result = self.run_cli_command(
                [
                    "create-sample",
                    output_file,
                    "--amount",
                    "250.0",
                    "--currency",
                    "EUR",
                    "--channel",
                    "pos",
                    "--modality",
                    "deferred",
                    "--country",
                    "DE",
                ]
            )

            assert result.returncode == 0
            assert "✅ Sample AP2 contract created" in result.stdout

            # Check output file exists and contains valid AP2 data
            with open(output_file) as f:
                sample_data = json.load(f)

            assert "ap2_version" in sample_data
            assert sample_data["cart"]["amount"] == "250.0"
            assert sample_data["cart"]["currency"] == "EUR"
            assert sample_data["intent"]["channel"] == "pos"
            assert sample_data["payment"]["modality"] == "deferred"

        finally:
            os.unlink(output_file)

    def test_explain_command(self):
        """Test explain command."""
        # First create a decision result file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.create_sample_ap2_contract(), f)
            input_file = f.name

        try:
            result = self.run_cli_command(["explain", input_file])

            assert result.returncode == 0
            assert "Decision Explanation" in result.stdout
            assert "Decision:" in result.stdout

        finally:
            os.unlink(input_file)

    def test_explain_command_verbose(self):
        """Test explain command with verbose output."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.create_sample_ap2_contract(), f)
            input_file = f.name

        try:
            result = self.run_cli_command(["explain", input_file, "--verbose"])

            assert result.returncode == 0
            assert "Decision Explanation" in result.stdout
            assert "Decision Summary:" in result.stdout
            assert "Result:" in result.stdout
            assert "Risk Score:" in result.stdout

        finally:
            os.unlink(input_file)

    def test_golden_file_integration(self):
        """Test CLI with golden AP2 file."""
        if not self.golden_file.exists():
            pytest.skip("Golden file not found")

        # Test validation
        result = self.run_cli_command(["validate", str(self.golden_file)])
        assert result.returncode == 0
        assert "✅ AP2 contract is valid" in result.stdout

        # Test decision processing
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_file = f.name

        try:
            result = self.run_cli_command(
                ["decide-file", str(self.golden_file), "--output", output_file, "--explain"]
            )

            assert result.returncode == 0

            # Check output
            with open(output_file) as f:
                output_data = json.load(f)

            assert "decision" in output_data
            assert "explanation" in output_data
            assert output_data["decision"]["result"] in ["APPROVE", "REVIEW", "DECLINE"]

        finally:
            os.unlink(output_file)

    def test_error_handling_invalid_json(self):
        """Test error handling for invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name

        try:
            result = self.run_cli_command(["validate", temp_file])

            assert result.returncode == 1
            assert "❌" in result.stdout

        finally:
            os.unlink(temp_file)

    def test_error_handling_missing_required_fields(self):
        """Test error handling for missing required fields."""
        incomplete_data = {
            "ap2_version": "0.1.0",
            # Missing required fields
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(incomplete_data, f)
            temp_file = f.name

        try:
            result = self.run_cli_command(["validate", temp_file])

            assert result.returncode == 1
            assert "❌ AP2 contract validation failed" in result.stdout

        finally:
            os.unlink(temp_file)

    def test_help_command(self):
        """Test help command."""
        result = self.run_cli_command(["--help"])

        assert result.returncode == 0
        assert "AP2 Decision Engine CLI" in result.stdout
        assert "decide-file" in result.stdout
        assert "validate" in result.stdout
        assert "create-sample" in result.stdout
        assert "explain" in result.stdout

    def test_subcommand_help(self):
        """Test subcommand help."""
        result = self.run_cli_command(["decide-file", "--help"])

        assert result.returncode == 0
        assert "Process an AP2 decision request from a JSON file" in result.stdout
        assert "--legacy-json" in result.stdout
        assert "--explain" in result.stdout
        assert "--validate-only" in result.stdout
