#!/bin/bash
# --- Orca Day-1: system tools (macOS) ---
set -e

echo "🍎 Starting Orca development environment setup for macOS..."

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "📦 Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add Homebrew to PATH for Apple Silicon Macs
    if [[ $(uname -m) == "arm64" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    echo "✅ Homebrew already installed"
fi

# Update Homebrew
echo "🔄 Updating Homebrew..."
brew update

# Install Git (usually pre-installed, but ensure latest)
if ! command -v git &> /dev/null; then
    echo "📦 Installing Git..."
    brew install git
else
    echo "✅ Git already installed"
fi

# Install GitHub CLI
if ! command -v gh &> /dev/null; then
    echo "📦 Installing GitHub CLI..."
    brew install gh
else
    echo "✅ GitHub CLI already installed"
fi

# Install Python 3.11+
if ! command -v python3 &> /dev/null || ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    echo "📦 Installing Python 3.12..."
    brew install python@3.12
    # Create symlink for python3 if it doesn't exist
    if ! command -v python3 &> /dev/null; then
        ln -sf /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3
    fi
else
    echo "✅ Python 3.11+ already installed"
fi

# Install pipx
if ! command -v pipx &> /dev/null; then
    echo "📦 Installing pipx..."
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
else
    echo "✅ pipx already installed"
fi

# Install uv via pipx
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv..."
    pipx install uv
else
    echo "✅ uv already installed"
fi

# Install Make (usually pre-installed)
if ! command -v make &> /dev/null; then
    echo "📦 Installing Make..."
    brew install make
else
    echo "✅ Make already installed"
fi

# Install Node.js (optional)
if ! command -v node &> /dev/null; then
    echo "📦 Installing Node.js LTS..."
    brew install node
else
    echo "✅ Node.js already installed"
fi

# Install Docker Desktop (optional)
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker Desktop..."
    brew install --cask docker
    echo "⚠️  Please start Docker Desktop manually from Applications"
else
    echo "✅ Docker already installed"
fi

# Install Python development tools
echo "📦 Installing Python development tools..."

# Install pre-commit
if ! python3 -c "import pre_commit" 2>/dev/null; then
    echo "  Installing pre-commit..."
    pipx install pre-commit
else
    echo "  ✅ pre-commit already installed"
fi

# Install ruff
if ! python3 -c "import ruff" 2>/dev/null; then
    echo "  Installing ruff..."
    pipx install ruff
else
    echo "  ✅ ruff already installed"
fi

# Install black
if ! python3 -c "import black" 2>/dev/null; then
    echo "  Installing black..."
    pipx install black
else
    echo "  ✅ black already installed"
fi

# Install mypy
if ! python3 -c "import mypy" 2>/dev/null; then
    echo "  Installing mypy..."
    pipx install mypy
else
    echo "  ✅ mypy already installed"
fi

# Install pytest
if ! python3 -c "import pytest" 2>/dev/null; then
    echo "  Installing pytest..."
    pipx install pytest
else
    echo "  ✅ pytest already installed"
fi

# Install streamlit
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "  Installing streamlit..."
    pipx install streamlit
else
    echo "  ✅ streamlit already installed"
fi

# Install bandit (optional security linter)
if ! python3 -c "import bandit" 2>/dev/null; then
    echo "  Installing bandit..."
    pipx install bandit
else
    echo "  ✅ bandit already installed"
fi

echo ""
echo "✅ All tools installed successfully!"
echo ""
echo "💡 Next steps:"
echo "   1. Restart your terminal or run: source ~/.zprofile"
echo "   2. Run the doctor to verify installation: make doctor"
echo "   3. Initialize the project: make init"
echo ""
echo "🎉 Orca development environment is ready!"

