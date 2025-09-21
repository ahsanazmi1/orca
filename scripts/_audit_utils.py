"""
Audit utility functions for OCN Orca phase status checking.

This module provides lightweight helper functions for the audit script
without adding heavy dependencies.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def find_files_by_pattern(directory: str, pattern: str) -> list[Path]:
    """Find files matching a glob pattern in directory."""
    path = Path(directory)
    if not path.exists():
        return []
    return list(path.glob(pattern))


def find_files_by_name(directory: str, filename: str) -> list[Path]:
    """Find files with exact name in directory (recursive)."""
    path = Path(directory)
    if not path.exists():
        return []
    return list(path.rglob(filename))


def load_json_file(file_path: Path) -> dict[str, Any] | None:
    """Load JSON file safely."""
    try:
        with open(file_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, PermissionError):
        return None


def search_in_files(
    pattern: str, file_paths: list[Path], case_sensitive: bool = True
) -> list[tuple[Path, int, str]]:
    """Search for pattern in files and return matches with line numbers."""
    matches = []
    flags = [] if case_sensitive else ["-i"]

    for file_path in file_paths:
        try:
            result = subprocess.run(
                ["grep", "-n"] + flags + [pattern, str(file_path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        parts = line.split(":", 2)
                        if len(parts) >= 2:
                            try:
                                line_num = int(parts[1])
                                content = parts[2] if len(parts) > 2 else parts[1]
                                matches.append((file_path, line_num, content))
                            except ValueError:
                                # Skip lines that don't have proper line numbers
                                continue
            # Debug: check if grep found nothing (return code 1)
            elif result.returncode == 1:
                # No matches found - this is normal
                continue
            else:
                # Other error
                continue
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            # Debug: print the exception
            print(f"Subprocess error for {file_path}: {e}")
            continue

    return matches


def run_pytest_coverage() -> tuple[bool, dict[str, Any]]:
    """Run pytest with coverage and return results."""
    try:
        # Run pytest with coverage
        result = subprocess.run(
            ["python", "-m", "pytest", "--cov=src", "--cov-report=json", "--cov-report=term", "-q"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout
        )

        # Try to load coverage report
        coverage_data = None
        coverage_file = Path(".coverage.json")
        if coverage_file.exists():
            coverage_data = load_json_file(coverage_file)

        return result.returncode == 0, {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "coverage_data": coverage_data,
        }
    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        return False, {"error": str(e)}


def check_python_version() -> tuple[bool, str]:
    """Check if Python version meets requirements."""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 12:
        return True, f"{version.major}.{version.minor}.{version.micro}"
    return False, f"{version.major}.{version.minor}.{version.micro}"


def check_import_module(module_name: str) -> tuple[bool, str]:
    """Try to import a module and return success status."""
    try:
        __import__(module_name)
        return True, f"Module '{module_name}' imported successfully"
    except ImportError as e:
        return False, f"Module '{module_name}' not available: {e}"


def validate_json_schema(data: dict[str, Any], schema: dict[str, Any]) -> tuple[bool, list[str]]:
    """Simple JSON schema validation without external dependencies."""
    errors = []

    def validate_object(obj: Any, schema_obj: dict[str, Any], path: str = "") -> None:
        if "type" in schema_obj:
            expected_type = schema_obj["type"]
            if expected_type == "object" and not isinstance(obj, dict):
                errors.append(f"{path}: expected object, got {type(obj).__name__}")
            elif expected_type == "string" and not isinstance(obj, str):
                errors.append(f"{path}: expected string, got {type(obj).__name__}")
            elif expected_type == "number" and not isinstance(obj, (int, float)):
                errors.append(f"{path}: expected number, got {type(obj).__name__}")
            elif expected_type == "array" and not isinstance(obj, list):
                errors.append(f"{path}: expected array, got {type(obj).__name__}")
            elif expected_type == "boolean" and not isinstance(obj, bool):
                errors.append(f"{path}: expected boolean, got {type(obj).__name__}")

        if "required" in schema_obj and isinstance(obj, dict):
            for field in schema_obj["required"]:
                if field not in obj:
                    errors.append(f"{path}.{field}: required field missing")

        if "properties" in schema_obj and isinstance(obj, dict):
            for prop, prop_schema in schema_obj["properties"].items():
                if prop in obj:
                    validate_object(obj[prop], prop_schema, f"{path}.{prop}" if path else prop)

    validate_object(data, schema)
    return len(errors) == 0, errors


def validate_cloudevents_basic(event_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Basic CloudEvents validation without external dependencies."""
    errors = []
    required_fields = ["specversion", "id", "source", "type", "data"]

    for field in required_fields:
        if field not in event_data:
            errors.append(f"Missing required CloudEvents field: {field}")

    # Check specversion
    if "specversion" in event_data and event_data["specversion"] != "1.0":
        errors.append(f"Invalid specversion: {event_data['specversion']}, expected '1.0'")

    # Check type format
    if "type" in event_data:
        event_type = event_data["type"]
        if not isinstance(event_type, str) or "." not in event_type:
            errors.append(f"Invalid event type format: {event_type}")
        elif not event_type.startswith("ocn.orca."):
            errors.append(f"Event type should start with 'ocn.orca.': {event_type}")

    return len(errors) == 0, errors


def check_git_tags() -> list[str]:
    """Get available git tags."""
    try:
        result = subprocess.run(
            ["git", "tag", "--list"], capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return [tag.strip() for tag in result.stdout.strip().split("\n") if tag.strip()]
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass
    return []


def check_pre_commit_hooks() -> tuple[bool, list[str]]:
    """Check if pre-commit hooks are configured."""
    hooks_file = Path(".pre-commit-config.yaml")
    if not hooks_file.exists():
        return False, [".pre-commit-config.yaml not found"]

    try:
        result = subprocess.run(
            ["pre-commit", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return False, ["pre-commit not installed"]

        # Check if hooks are installed
        result = subprocess.run(
            ["pre-commit", "install", "--install-hooks"], capture_output=True, text=True, timeout=30
        )

        return True, ["pre-commit hooks configured"]
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False, ["pre-commit not available"]


def get_file_size(file_path: Path) -> int:
    """Get file size in bytes."""
    try:
        return file_path.stat().st_size
    except (FileNotFoundError, PermissionError):
        return 0


def check_editorconfig() -> bool:
    """Check if .editorconfig exists."""
    return Path(".editorconfig").exists()


def check_codeowners() -> bool:
    """Check if CODEOWNERS file exists."""
    return Path(".github/CODEOWNERS").exists()


def find_ocn_common() -> tuple[bool, str]:
    """Try to find ocn-common dependency."""
    # Check if it's installed as a package
    try:
        import ocn_common

        return (
            True,
            f"ocn_common installed as package (version: {getattr(ocn_common, '__version__', 'unknown')})",
        )
    except ImportError:
        pass

    # Check if it's a git submodule
    if Path("ocn-common").exists() and Path("ocn-common/.git").exists():
        return True, "ocn-common found as git submodule"

    # Check if it's in PYTHONPATH
    for path in sys.path:
        ocn_path = Path(path) / "ocn_common"
        if ocn_path.exists():
            return True, f"ocn-common found in PYTHONPATH: {path}"

    return False, "ocn-common not found (not installed, not a submodule, not in PYTHONPATH)"


def check_streamlit_app() -> tuple[bool, list[str]]:
    """Check if Streamlit app exists and can be imported."""
    streamlit_files = find_files_by_pattern(".", "**/*streamlit*.py")
    demo_files = find_files_by_pattern(".", "**/demo*.py")

    all_files = streamlit_files + demo_files
    if not all_files:
        return False, ["No Streamlit or demo files found"]

    evidence = []
    for file_path in all_files:
        evidence.append(f"Found: {file_path}")

        # Try to check if it's a valid Streamlit app
        try:
            with open(file_path) as f:
                content = f.read()
                if "streamlit" in content.lower() or "st." in content:
                    evidence.append(f"  Contains Streamlit code: {file_path}")
        except (FileNotFoundError, PermissionError):
            continue

    return len(evidence) > 0, evidence


def check_log_redaction() -> tuple[bool, list[str]]:
    """Check for basic log redaction patterns."""
    evidence = []

    # Look for common PCI patterns that should be redacted
    pci_patterns = [
        r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # Credit card numbers
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
    ]

    # Search in source files
    source_files = find_files_by_pattern("src", "**/*.py")
    for pattern in pci_patterns:
        matches = search_in_files(pattern, source_files)
        if matches:
            evidence.append(f"Found potential PII patterns in code: {pattern}")

    # Look for redaction utilities
    redaction_files = find_files_by_name("src", "*redact*")
    if redaction_files:
        evidence.append(f"Found redaction utilities: {[str(f) for f in redaction_files]}")

    return len(evidence) == 0, evidence  # No PII patterns found is good


def get_coverage_percentage(coverage_data: dict[str, Any] | None) -> float:
    """Extract coverage percentage from coverage data."""
    if not coverage_data:
        return 0.0

    # Try different coverage report formats
    if "totals" in coverage_data:
        return coverage_data["totals"].get("percent_covered", 0.0)
    elif "coverage" in coverage_data:
        return coverage_data["coverage"].get("percent_covered", 0.0)

    return 0.0
