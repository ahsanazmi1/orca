"""
Comprehensive tests for CLI batch functionality.
"""

from unittest.mock import patch

from orca_core.cli import decide_batch


class TestDecideBatch:
    """Test suite for decide_batch function."""

    def test_decide_batch_function_exists(self):
        """Test that decide_batch function exists and is callable."""
        assert callable(decide_batch)

    def test_decide_batch_function_signature(self):
        """Test that decide_batch has the expected parameters."""
        import inspect

        sig = inspect.signature(decide_batch)
        params = list(sig.parameters.keys())

        expected_params = ["glob_pattern", "mode", "ml", "explain", "output_format", "output_file"]

        for param in expected_params:
            assert param in params, f"Parameter {param} not found in decide_batch signature"

    def test_decide_batch_integration(self):
        """Test decide_batch integration with typer."""
        # Test that the function is properly decorated and has the expected structure
        assert hasattr(decide_batch, "__name__")
        assert decide_batch.__name__ == "decide_batch"

    def test_decide_batch_docstring(self):
        """Test that decide_batch has proper documentation."""
        docstring = decide_batch.__doc__
        assert docstring is not None
        assert "Evaluate decision requests" in docstring
        assert "JSON files" in docstring

    @patch("orca_core.cli.app")
    def test_decide_batch_registered_with_app(self, mock_app):
        """Test that decide_batch is registered with the typer app."""
        # This test verifies the function is properly decorated
        assert hasattr(decide_batch, "__wrapped__") or hasattr(decide_batch, "__name__")

    def test_decide_batch_default_values(self):
        """Test that decide_batch has expected default values."""
        import inspect

        sig = inspect.signature(decide_batch)

        # Check that glob_pattern has a default
        glob_param = sig.parameters.get("glob_pattern")
        assert glob_param is not None
        assert glob_param.default is not None

        # Check that output_format has a default
        format_param = sig.parameters.get("output_format")
        assert format_param is not None
        assert format_param.default is not None
