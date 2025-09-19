"""Smoke tests for AP2 Streamlit UI functionality."""

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import streamlit as st

from src.orca.ui.app import AP2OrcaUI


class TestAP2StreamlitUISmoke:
    """Smoke tests for AP2 Streamlit UI."""

    def setup_method(self):
        """Set up test environment."""
        self.ui = AP2OrcaUI()
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

    def test_ui_initialization(self):
        """Test UI initialization."""
        assert self.ui is not None
        assert hasattr(self.ui, "setup_page_config")
        assert hasattr(self.ui, "initialize_session_state")
        assert hasattr(self.ui, "render_header")
        assert hasattr(self.ui, "render_sidebar")
        assert hasattr(self.ui, "render_ap2_input_section")
        assert hasattr(self.ui, "render_ap2_panes")
        assert hasattr(self.ui, "render_decision_result")
        assert hasattr(self.ui, "render_signature_receipt_section")
        assert hasattr(self.ui, "render_output_section")

    def test_session_state_initialization(self):
        """Test session state initialization."""
        # Mock streamlit session state to avoid runtime errors
        with patch.object(st, "session_state", MagicMock()):
            # Should not raise any exceptions
            try:
                self.ui.initialize_session_state()
            except Exception as e:
                pytest.fail(f"Session state initialization failed: {e}")

    def test_load_sample_contract(self):
        """Test loading sample contract."""
        with patch.object(st, "session_state", MagicMock()):
            with patch.object(st, "success") as mock_success:
                self.ui.load_sample_contract()

                # Verify success message was shown
                mock_success.assert_called_once()
                assert "Sample AP2 contract loaded" in mock_success.call_args[0][0]

    def test_load_golden_file_exists(self):
        """Test loading golden file when it exists."""
        if not self.golden_file.exists():
            pytest.skip("Golden file not found")

        with patch.object(st, "session_state", MagicMock()):
            with patch.object(st, "success") as mock_success:
                self.ui.load_golden_file()

                # Verify success message was shown
                mock_success.assert_called_once()
                assert "Golden AP2 file loaded" in mock_success.call_args[0][0]

    def test_load_golden_file_not_exists(self):
        """Test loading golden file when it doesn't exist."""
        with patch.object(st, "session_state", MagicMock()):
            with patch.object(st, "error") as mock_error:
                # Temporarily rename golden file
                if self.golden_file.exists():
                    temp_name = self.golden_file.with_suffix(".json.temp")
                    self.golden_file.rename(temp_name)

                try:
                    self.ui.load_golden_file()

                    # Verify error message was shown
                    mock_error.assert_called_once()
                    assert "Golden file not found" in mock_error.call_args[0][0]

                finally:
                    # Restore golden file
                    if temp_name.exists():
                        temp_name.rename(self.golden_file)

    def test_process_decision_with_contract(self):
        """Test processing decision when contract is loaded."""
        # Mock session state with contract
        mock_contract = MagicMock()
        mock_contract.decision = MagicMock()
        mock_contract.decision.result = "APPROVE"
        mock_contract.decision.risk_score = 0.1
        mock_contract.decision.reasons = []
        mock_contract.decision.actions = []
        mock_contract.decision.meta = MagicMock()
        mock_contract.decision.meta.model = "rules_only"

        with patch.object(st, "session_state", MagicMock()) as mock_session:
            mock_session.ap2_contract = mock_contract
            mock_session.decision_result = None
            mock_session.explanation = None

            with patch.object(st, "spinner"):
                with patch.object(st, "success") as mock_success:
                    with patch("src.orca.ui.app.evaluate_ap2_rules") as mock_evaluate:
                        with patch("src.orca.ui.app.sign_and_hash_decision") as mock_sign:
                            with patch("src.orca.ui.app.explain_ap2_decision") as mock_explain:
                                mock_evaluate.return_value = mock_contract.decision
                                mock_sign.return_value = mock_contract
                                mock_explain.return_value = "Test explanation"

                                self.ui.process_decision()

                                # Verify success message was shown
                                mock_success.assert_called_once()
                                assert (
                                    "Decision processed successfully"
                                    in mock_success.call_args[0][0]
                                )

    def test_process_decision_without_contract(self):
        """Test processing decision when no contract is loaded."""
        with patch.object(st, "session_state", MagicMock()) as mock_session:
            mock_session.ap2_contract = None

            with patch.object(st, "warning") as mock_warning:
                self.ui.process_decision()

                # Verify warning message was shown
                mock_warning.assert_called_once()
                assert (
                    "Please load or validate an AP2 contract first" in mock_warning.call_args[0][0]
                )

    def test_render_ap2_panes_without_contract(self):
        """Test rendering AP2 panes without contract."""
        with patch.object(st, "session_state", MagicMock()) as mock_session:
            mock_session.ap2_contract = None

            with patch.object(st, "info") as mock_info:
                self.ui.render_ap2_panes()

                # Verify info message was shown
                mock_info.assert_called_once()
                assert "Please load or validate an AP2 contract first" in mock_info.call_args[0][0]

    def test_render_decision_result_without_result(self):
        """Test rendering decision result without result."""
        with patch.object(st, "session_state", MagicMock()) as mock_session:
            mock_session.decision_result = None

            # Should return early without error
            self.ui.render_decision_result()

    def test_render_signature_receipt_section_without_signing(self):
        """Test rendering signature/receipt section without signing info."""
        with patch.object(st, "session_state", MagicMock()) as mock_session:
            mock_session.ap2_contract = None

            # Should return early without error
            self.ui.render_signature_receipt_section()

    def test_render_output_section_without_contract(self):
        """Test rendering output section without contract."""
        with patch.object(st, "session_state", MagicMock()) as mock_session:
            mock_session.ap2_contract = None

            # Should return early without error
            self.ui.render_output_section()

    def test_environment_variable_updates(self):
        """Test that environment variables are updated correctly."""
        with patch.object(st, "session_state", MagicMock()) as mock_session:
            mock_session.signing_enabled = True
            mock_session.receipt_hash_only = False

            with patch.object(st, "sidebar"):
                with patch.object(st, "checkbox") as mock_checkbox:
                    mock_checkbox.return_value = True

                    self.ui.render_sidebar()

                    # Verify environment variables were set
                    assert os.environ.get("ORCA_SIGN_DECISIONS") == "true"
                    # The checkbox mock returns True, so receipt_hash_only will be "true"
                    assert os.environ.get("ORCA_RECEIPT_HASH_ONLY") == "true"

    def test_ui_component_rendering(self):
        """Test that UI components can be rendered without errors."""
        # Create a mock session state with proper data
        mock_session_state = MagicMock()
        mock_session_state.ap2_contract = None
        mock_session_state.decision_result = None
        mock_session_state.explanation = None
        mock_session_state.signing_enabled = False
        mock_session_state.receipt_hash_only = False
        mock_session_state.legacy_json = False

        # Mock all Streamlit components to avoid rendering issues
        with patch.object(st, "session_state", mock_session_state):
            # Mock all Streamlit components
            st_patches = [
                patch.object(st, "title"),
                patch.object(st, "markdown"),
                patch.object(st, "header"),
                patch.object(st, "subheader"),
                patch.object(st, "sidebar"),
                patch.object(st, "radio"),
                patch.object(st, "checkbox"),
                patch.object(st, "button"),
                patch.object(st, "text_area"),
                patch.object(st, "columns", side_effect=lambda n: [MagicMock() for _ in range(n)]),
                patch.object(st, "expander"),
                patch.object(st, "table"),
                patch.object(st, "metric"),
                patch.object(st, "code"),
                patch.object(st, "download_button"),
                patch.object(st, "success"),
                patch.object(st, "error"),
                patch.object(st, "warning"),
                patch.object(st, "info"),
            ]

            # Apply all patches
            for patch_obj in st_patches:
                patch_obj.start()

            try:
                # Test that all render methods can be called without errors
                self.ui.render_header()
                self.ui.render_sidebar()
                self.ui.render_ap2_input_section()
                self.ui.render_ap2_panes()
                self.ui.render_decision_result()
                self.ui.render_signature_receipt_section()
                self.ui.render_output_section()
                self.ui.render_status_section()
            except Exception as e:
                pytest.fail(f"UI rendering failed: {e}")
            finally:
                # Clean up patches
                for patch_obj in st_patches:
                    patch_obj.stop()

    def test_ui_run_method(self):
        """Test that the main run method can be called."""
        with patch.object(st, "session_state", MagicMock()):
            with patch.object(self.ui, "render_header"):
                with patch.object(self.ui, "render_sidebar"):
                    with patch.object(self.ui, "render_status_section"):
                        with patch.object(self.ui, "render_ap2_input_section"):
                            with patch.object(self.ui, "render_ap2_panes"):
                                with patch.object(self.ui, "render_decision_result"):
                                    with patch.object(self.ui, "render_signature_receipt_section"):
                                        with patch.object(self.ui, "render_output_section"):
                                            # Should not raise any exceptions
                                            self.ui.run()

    def test_sample_contract_creation(self):
        """Test sample contract creation logic."""
        with patch.object(st, "session_state", MagicMock()):
            with patch.object(st, "success") as mock_success:
                with patch("src.orca.ui.app.IntentMandate"):
                    with patch("src.orca.ui.app.CartMandate"):
                        with patch("src.orca.ui.app.PaymentMandate"):
                            with patch(
                                "src.orca.core.decision_contract.create_ap2_decision_contract"
                            ) as mock_create:
                                mock_contract = MagicMock()
                                mock_create.return_value = mock_contract

                                self.ui.load_sample_contract()

                                # Verify success message was shown
                                mock_success.assert_called_once()
                                assert "Sample AP2 contract loaded" in mock_success.call_args[0][0]

    def test_golden_file_loading_logic(self):
        """Test golden file loading logic."""
        if not self.golden_file.exists():
            pytest.skip("Golden file not found")

        with patch.object(st, "session_state", MagicMock()):
            with patch.object(st, "success") as mock_success:
                with patch("src.orca.ui.app.validate_ap2_contract") as mock_validate:
                    mock_contract = MagicMock()
                    mock_validate.return_value = mock_contract

                    self.ui.load_golden_file()

                    # Verify success message was shown
                    mock_success.assert_called_once()
                    assert "Golden AP2 file loaded" in mock_success.call_args[0][0]

    def test_error_handling_in_sample_loading(self):
        """Test error handling in sample contract loading."""
        with patch.object(st, "session_state", MagicMock()):
            with patch.object(st, "error") as mock_error:
                with patch("src.orca.ui.app.IntentMandate", side_effect=Exception("Test error")):
                    self.ui.load_sample_contract()

                    # Verify error message was shown
                    mock_error.assert_called_once()
                    assert "Error loading sample contract" in mock_error.call_args[0][0]

    def test_error_handling_in_golden_loading(self):
        """Test error handling in golden file loading."""
        with patch.object(st, "session_state", MagicMock()):
            with patch.object(st, "error") as mock_error:
                with patch(
                    "src.orca.ui.app.validate_ap2_contract", side_effect=Exception("Test error")
                ):
                    self.ui.load_golden_file()

                    # Verify error message was shown
                    mock_error.assert_called_once()
                    assert "Error loading golden file" in mock_error.call_args[0][0]

    def test_error_handling_in_decision_processing(self):
        """Test error handling in decision processing."""
        with patch.object(st, "session_state", MagicMock()) as mock_session:
            mock_contract = MagicMock()
            mock_session.ap2_contract = mock_contract

            with patch.object(st, "error") as mock_error:
                with patch(
                    "src.orca.ui.app.evaluate_ap2_rules", side_effect=Exception("Test error")
                ):
                    self.ui.process_decision()

                    # Verify error message was shown
                    mock_error.assert_called_once()
                    assert "Error processing decision" in mock_error.call_args[0][0]
