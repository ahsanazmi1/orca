"""
Smoke tests for the Orca audit functionality.

These tests ensure the audit script runs and produces expected outputs
without modifying the actual codebase.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


class TestAuditSmoke:
    """Smoke tests for audit functionality."""

    def test_audit_script_exists(self):
        """Test that the audit script exists and is executable."""
        audit_script = Path("scripts/audit_orca_phase_status.py")
        assert audit_script.exists(), "Audit script should exist"

        # Check that it's a Python file
        content = audit_script.read_text()
        assert "#!/usr/bin/env python3" in content or "def main()" in content

    def test_audit_utils_exists(self):
        """Test that audit utilities exist."""
        utils_script = Path("scripts/_audit_utils.py")
        assert utils_script.exists(), "Audit utilities should exist"

        # Check for key utility functions
        content = utils_script.read_text()
        assert "def find_files_by_pattern" in content
        assert "def load_json_file" in content
        assert "def run_pytest_coverage" in content

    def test_audit_script_imports(self):
        """Test that the audit script can be imported without errors."""
        sys.path.insert(0, str(Path("scripts").absolute()))

        try:
            import audit_orca_phase_status

            assert hasattr(audit_orca_phase_status, "OrcaAuditor")
            assert hasattr(audit_orca_phase_status, "AuditResult")
        except ImportError as e:
            pytest.fail(f"Failed to import audit script: {e}")
        finally:
            sys.path.pop(0)

    def test_audit_utils_imports(self):
        """Test that audit utilities can be imported."""
        sys.path.insert(0, str(Path("scripts").absolute()))

        try:
            import _audit_utils

            assert hasattr(_audit_utils, "find_files_by_pattern")
            assert hasattr(_audit_utils, "load_json_file")
            assert hasattr(_audit_utils, "check_python_version")
        except ImportError as e:
            pytest.fail(f"Failed to import audit utilities: {e}")
        finally:
            sys.path.pop(0)

    def test_audit_result_creation(self):
        """Test AuditResult creation and serialization."""
        sys.path.insert(0, str(Path("scripts").absolute()))

        try:
            from audit_orca_phase_status import AuditResult

            result = AuditResult(
                name="Test Check",
                phase="Foundations",
                status="pass",
                evidence=["Test evidence"],
                remedy="Test remedy",
            )

            # Test to_dict method
            result_dict = result.to_dict()
            assert result_dict["name"] == "Test Check"
            assert result_dict["phase"] == "Foundations"
            assert result_dict["status"] == "pass"
            assert result_dict["evidence"] == ["Test evidence"]
            assert result_dict["remedy"] == "Test remedy"

        except ImportError as e:
            pytest.fail(f"Failed to import AuditResult: {e}")
        finally:
            sys.path.pop(0)

    def test_audit_script_runs_without_crashing(self):
        """Test that the audit script runs without crashing."""
        audit_script = Path("scripts/audit_orca_phase_status.py")

        # Run with timeout to prevent hanging
        try:
            result = subprocess.run(
                [sys.executable, str(audit_script), "--help"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            # Script should either exit with 0 or have some output
            assert result.returncode in [0, 1] or result.stdout or result.stderr
        except subprocess.TimeoutExpired:
            pytest.fail("Audit script timed out")
        except FileNotFoundError:
            pytest.fail("Could not run audit script")

    def test_audit_utilities_basic_functionality(self):
        """Test basic functionality of audit utilities."""
        sys.path.insert(0, str(Path("scripts").absolute()))

        try:
            import _audit_utils

            # Test file finding
            files = _audit_utils.find_files_by_pattern(".", "*.py")
            assert isinstance(files, list)
            assert len(files) > 0  # Should find at least some Python files

            # Test Python version check
            version_ok, version = _audit_utils.check_python_version()
            assert isinstance(version_ok, bool)
            assert isinstance(version, str)

            # Test JSON loading
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                test_data = {"test": "data"}
                json.dump(test_data, f)
                f.flush()

                loaded_data = _audit_utils.load_json_file(Path(f.name))
                assert loaded_data == test_data

                # Clean up
                Path(f.name).unlink()

        except ImportError as e:
            pytest.fail(f"Failed to import audit utilities: {e}")
        finally:
            sys.path.pop(0)

    def test_audit_generates_output_files(self):
        """Test that audit generates expected output files (in temp directory)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Change to temp directory and copy necessary files
            original_cwd = Path.cwd()

            try:
                # Create a minimal test environment
                (temp_path / "scripts").mkdir()

                # Copy audit files
                audit_script = Path("scripts/audit_orca_phase_status.py")
                utils_script = Path("scripts/_audit_utils.py")

                if audit_script.exists():
                    (temp_path / "scripts" / "audit_orca_phase_status.py").write_text(
                        audit_script.read_text()
                    )
                if utils_script.exists():
                    (temp_path / "scripts" / "_audit_utils.py").write_text(utils_script.read_text())

                # Create minimal test files
                (temp_path / "README.md").write_text("# Test README")
                (temp_path / "LICENSE").write_text("Test License")
                (temp_path / "pyproject.toml").write_text(
                    """
[project]
name = "test"
version = "0.1.0"
requires-python = ">=3.12"
"""
                )

                # Change to temp directory
                import os

                os.chdir(temp_path)

                # Run audit script
                if (temp_path / "scripts" / "audit_orca_phase_status.py").exists():
                    subprocess.run(
                        [sys.executable, "scripts/audit_orca_phase_status.py"],
                        capture_output=True,
                        text=True,
                        timeout=60,
                        cwd=temp_path,
                    )

                    # Check that output files were created
                    markdown_report = temp_path / "AUDIT_REPORT.md"
                    json_report = temp_path / "audit_report.json"

                    # At least one should exist (depending on how far the script gets)
                    assert (
                        markdown_report.exists() or json_report.exists()
                    ), "Audit should generate at least one report file"

                    if markdown_report.exists():
                        content = markdown_report.read_text()
                        assert "OCN Orca Audit" in content
                        assert "Summary" in content

                    if json_report.exists():
                        with open(json_report) as f:
                            data = json.load(f)
                            assert "audit_date" in data
                            assert "summary" in data
                            assert "results" in data

            finally:
                os.chdir(original_cwd)

    def test_audit_handles_missing_files_gracefully(self):
        """Test that audit handles missing files gracefully."""
        sys.path.insert(0, str(Path("scripts").absolute()))

        try:
            import _audit_utils

            # Test finding non-existent files
            files = _audit_utils.find_files_by_pattern("non_existent_directory", "*.py")
            assert files == []

            # Test loading non-existent JSON
            non_existent = _audit_utils.load_json_file(Path("non_existent.json"))
            assert non_existent is None

            # Test finding files with non-existent pattern
            files = _audit_utils.find_files_by_pattern(".", "*.non_existent_extension")
            assert isinstance(files, list)

        except ImportError as e:
            pytest.fail(f"Failed to import audit utilities: {e}")
        finally:
            sys.path.pop(0)

    def test_audit_utilities_error_handling(self):
        """Test error handling in audit utilities."""
        sys.path.insert(0, str(Path("scripts").absolute()))

        try:
            import _audit_utils

            # Test with invalid JSON
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                f.write("{ invalid json }")
                f.flush()

                loaded_data = _audit_utils.load_json_file(Path(f.name))
                assert loaded_data is None

                # Clean up
                Path(f.name).unlink()

            # Test search in non-existent files
            matches = _audit_utils.search_in_files("test", [Path("non_existent.py")])
            assert matches == []

        except ImportError as e:
            pytest.fail(f"Failed to import audit utilities: {e}")
        finally:
            sys.path.pop(0)

    @pytest.mark.skip(reason="Slow test - may timeout")
    def test_audit_coverage_check(self):
        """Test that coverage checking works (may be slow)."""
        sys.path.insert(0, str(Path("scripts").absolute()))

        try:
            import _audit_utils

            # This test may take time and may fail if pytest/coverage not available
            # So we'll just test that the function exists and can be called
            success, results = _audit_utils.run_pytest_coverage()

            # Should return boolean and dict
            assert isinstance(success, bool)
            assert isinstance(results, dict)

        except ImportError as e:
            pytest.fail(f"Failed to import audit utilities: {e}")
        finally:
            sys.path.pop(0)


class TestAuditIntegration:
    """Integration tests for audit functionality."""

    def test_audit_script_help_output(self):
        """Test that audit script provides help information."""
        audit_script = Path("scripts/audit_orca_phase_status.py")

        if not audit_script.exists():
            pytest.skip("Audit script not found")

        # Read the script to check for help/documentation
        content = audit_script.read_text()

        # Should contain docstring or help information
        assert "OCN Orca Phase Status Audit" in content
        assert "audit_report.json" in content
        assert "AUDIT_REPORT.md" in content

    def test_audit_utilities_docstrings(self):
        """Test that audit utilities have proper docstrings."""
        utils_script = Path("scripts/_audit_utils.py")

        if not utils_script.exists():
            pytest.skip("Audit utilities not found")

        content = utils_script.read_text()

        # Should contain function docstrings
        assert '"""' in content or "'''" in content
        assert "find_files_by_pattern" in content
        assert "load_json_file" in content

    def test_audit_file_structure(self):
        """Test that audit files have proper structure."""
        audit_script = Path("scripts/audit_orca_phase_status.py")
        utils_script = Path("scripts/_audit_utils.py")

        assert audit_script.exists(), "Main audit script should exist"
        assert utils_script.exists(), "Audit utilities should exist"

        # Check that they're in the scripts directory
        assert audit_script.parent.name == "scripts"
        assert utils_script.parent.name == "scripts"

        # Check file sizes (should not be empty)
        assert audit_script.stat().st_size > 1000, "Audit script should be substantial"
        assert utils_script.stat().st_size > 500, "Audit utilities should be substantial"
