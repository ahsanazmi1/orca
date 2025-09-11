#!/usr/bin/env python3
"""
Dev Doctor - Check development environment setup
Checks for required and optional development tools and their versions.
"""

import os
import platform
import subprocess
import sys


class DevDoctor:
    def __init__(self) -> None:
        self.required_tools = {
            "git": "Git version control",
            "gh": "GitHub CLI",
            "python": "Python (>=3.11)",
            "uv": "uv package manager",
            "make": "GNU Make",
            "pre-commit": "pre-commit hooks",
            "ruff": "Ruff linter/formatter",
            "black": "Black formatter",
            "mypy": "MyPy type checker",
            "pytest": "pytest testing framework",
            "streamlit": "Streamlit web framework",
        }

        self.optional_tools = {
            "node": "Node.js",
            "docker": "Docker",
            "pip": "pip package manager",
            "pipx": "pipx package manager",
        }

        self.results: dict[str, tuple[bool, str]] = {}
        self.failed_required: list[str] = []

    def run_command(self, cmd: list[str]) -> tuple[bool, str]:
        """Run a command and return (success, output)."""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False, "Command not found or timed out"

    def check_git(self) -> tuple[bool, str]:
        """Check Git installation."""
        success, output = self.run_command(["git", "--version"])
        if success:
            return True, output
        return False, "Git not found"

    def check_gh(self) -> tuple[bool, str]:
        """Check GitHub CLI installation."""
        success, output = self.run_command(["gh", "--version"])
        if success:
            # Extract version from output like "gh version 2.78.0 (2025-08-21)"
            lines = output.split("\n")
            version_line = lines[0] if lines else output
            return True, version_line
        return False, "GitHub CLI not found"

    def check_python(self) -> tuple[bool, str]:
        """Check Python installation and version."""
        success, output = self.run_command([sys.executable, "--version"])
        if success:
            # Extract version number
            version_str = output.split()[1] if len(output.split()) > 1 else output
            try:
                version_parts = version_str.split(".")
                major, minor = int(version_parts[0]), int(version_parts[1])
                if major > 3 or (major == 3 and minor >= 11):
                    return True, f"Python {version_str}"
                else:
                    return False, f"Python {version_str} (requires >=3.11)"
            except (ValueError, IndexError):
                return True, f"Python {version_str}"
        return False, "Python not found"

    def check_uv(self) -> tuple[bool, str]:
        """Check uv installation."""
        # Try direct command first
        success, output = self.run_command(["uv", "--version"])
        if success:
            return True, output

        # Try full path on Windows
        if platform.system() == "Windows":
            success, output = self.run_command([r"C:\Users\Mohsin\.local\bin\uv.exe", "--version"])
            if success:
                return True, output

        return False, "uv not found"

    def check_make(self) -> tuple[bool, str]:
        """Check Make installation."""
        success, output = self.run_command(["make", "--version"])
        if success:
            # Extract first line with version
            lines = output.split("\n")
            version_line = lines[0] if lines else output
            return True, version_line
        return False, "Make not found"

    def check_pip(self) -> tuple[bool, str]:
        """Check pip installation."""
        success, output = self.run_command([sys.executable, "-m", "pip", "--version"])
        if success:
            return True, output
        return False, "pip not found"

    def check_pipx(self) -> tuple[bool, str]:
        """Check pipx installation."""
        success, output = self.run_command(["pipx", "--version"])
        if success:
            return True, output
        return False, "pipx not found"

    def check_node(self) -> tuple[bool, str]:
        """Check Node.js installation."""
        success, output = self.run_command(["node", "--version"])
        if success:
            return True, f"Node.js {output}"
        return False, "Node.js not found"

    def check_docker(self) -> tuple[bool, str]:
        """Check Docker installation."""
        success, output = self.run_command(["docker", "--version"])
        if success:
            return True, output
        return False, "Docker not found"

    def check_python_package(self, package: str) -> tuple[bool, str]:
        """Check if a Python package is installed."""
        # Try direct command first
        success, output = self.run_command([package, "--version"])
        if success:
            return True, output

        # Try as Python module
        success, output = self.run_command([sys.executable, "-m", package, "--version"])
        if success:
            return True, output

        # Try full path on Windows for pipx packages
        if platform.system() == "Windows":
            pipx_path = rf"C:\Users\{os.environ.get('USERNAME', 'User')}\.local\bin\{package}.exe"
            success, output = self.run_command([pipx_path, "--version"])
            if success:
                return True, output

        return False, f"{package} not found"

    def run_checks(self) -> None:
        """Run all tool checks."""
        print("🔍 Dev Doctor - Checking development environment...\n")

        # Required tools
        print("📋 REQUIRED TOOLS:")
        print("-" * 50)

        for tool, description in self.required_tools.items():
            if tool == "git":
                success, output = self.check_git()
            elif tool == "gh":
                success, output = self.check_gh()
            elif tool == "python":
                success, output = self.check_python()
            elif tool == "uv":
                success, output = self.check_uv()
            elif tool == "make":
                success, output = self.check_make()
            elif tool == "pip":
                success, output = self.check_pip()
            elif tool == "pipx":
                success, output = self.check_pipx()
            elif tool == "node":
                success, output = self.check_node()
            elif tool == "docker":
                success, output = self.check_docker()
            else:
                # Python packages
                success, output = self.check_python_package(tool)

            self.results[tool] = (success, output)

            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {tool:<12} - {description}")
            if success:
                print(f"    Version: {output}")
            else:
                print(f"    Error: {output}")
                if tool in self.required_tools:
                    self.failed_required.append(tool)
            print()

        # Optional tools
        print("📋 OPTIONAL TOOLS:")
        print("-" * 50)

        for tool, description in self.optional_tools.items():
            if tool in self.results:
                success, output = self.results[tool]
            else:
                if tool == "node":
                    success, output = self.check_node()
                elif tool == "docker":
                    success, output = self.check_docker()
                elif tool == "pip":
                    success, output = self.check_pip()
                elif tool == "pipx":
                    success, output = self.check_pipx()
                else:
                    success, output = False, "Not checked"

            status = "✅ PASS" if success else "⚠️  MISSING"
            print(f"{status} {tool:<12} - {description}")
            if success:
                print(f"    Version: {output}")
            print()

    def print_summary(self) -> int:
        """Print summary and exit with appropriate code."""
        print("📊 SUMMARY:")
        print("-" * 50)

        total_required = len(self.required_tools)
        passed_required = total_required - len(self.failed_required)

        print(f"Required tools: {passed_required}/{total_required} passed")

        if self.failed_required:
            print(f"\n❌ Missing required tools: {', '.join(self.failed_required)}")
            print("\n💡 Next steps:")
            print("   1. Run the appropriate install script:")
            if platform.system() == "Darwin":
                print("      ./scripts/install_mac.sh")
            elif platform.system() == "Windows":
                print("      .\\scripts\\install_win.ps1")
            print("   2. Re-run this doctor: make doctor")
            return 1
        else:
            print("\n🎉 All required tools are installed!")
            print("💡 Your development environment is ready!")
            return 0


def main() -> None:
    """Main entry point."""
    doctor = DevDoctor()
    doctor.run_checks()
    exit_code = doctor.print_summary()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
