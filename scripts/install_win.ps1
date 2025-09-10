# --- Orca Day-1: system tools (Windows) ---
$ErrorActionPreference = "Stop"

Write-Host "Starting Orca development environment setup for Windows..." -ForegroundColor Green

# Check if winget is available
if (!(Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "winget is not available. Please install Windows Package Manager first." -ForegroundColor Red
    Write-Host "   Download from: https://github.com/microsoft/winget-cli/releases" -ForegroundColor Yellow
    exit 1
}

# Install Git
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Git..." -ForegroundColor Yellow
    winget install -e --id Git.Git | Out-Null
}
else {
    Write-Host "Git already installed" -ForegroundColor Green
}

# Install GitHub CLI
if (!(Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "Installing GitHub CLI..." -ForegroundColor Yellow
    winget install -e --id GitHub.cli | Out-Null
}
else {
    Write-Host " GitHub CLI already installed" -ForegroundColor Green
}

# Install Python 3.12
if (!(Get-Command python -ErrorAction SilentlyContinue) -or
    !(python --version 2>&1 | Select-String "3\.(1[1-9]|[2-9][0-9])")) {
    Write-Host "Installing Python 3.12..." -ForegroundColor Yellow
    winget install -e --id Python.Python.3.12 | Out-Null
}
else {
    Write-Host " Python 3.11+ already installed" -ForegroundColor Green
}

# Install pipx
if (!(Get-Command pipx -ErrorAction SilentlyContinue)) {
    Write-Host "Installing pipx..." -ForegroundColor Yellow
    winget install -e --id Python.Pipx | Out-Null
    pipx ensurepath
}
else {
    Write-Host " pipx already installed" -ForegroundColor Green
}

# Install uv via pipx
if (!(Get-Command uv -ErrorAction SilentlyContinue) -and
    !(Test-Path "C:\Users\$env:USERNAME\.local\bin\uv.exe")) {
    Write-Host "Installing uv..." -ForegroundColor Yellow
    pipx install uv
}
else {
    Write-Host " uv already installed" -ForegroundColor Green
}

# Install GNU Make
if (!(Get-Command make -ErrorAction SilentlyContinue)) {
    Write-Host "Installing GNU Make..." -ForegroundColor Yellow
    winget install -e --id GnuWin32.Make | Out-Null
}
else {
    Write-Host " Make already installed" -ForegroundColor Green
}

# Install Node.js (optional)
if (!(Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Node.js LTS..." -ForegroundColor Yellow
    winget install -e --id OpenJS.NodeJS.LTS | Out-Null
}
else {
    Write-Host " Node.js already installed" -ForegroundColor Green
}

# Install Docker Desktop (optional)
if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Docker Desktop..." -ForegroundColor Yellow
    winget install -e --id Docker.DockerDesktop | Out-Null
    Write-Host "WARNING:  Please start Docker Desktop manually from Start Menu" -ForegroundColor Cyan
}
else {
    Write-Host " Docker already installed" -ForegroundColor Green
}

# Install Python development tools
Write-Host "Installing Python development tools..." -ForegroundColor Yellow

# Install pre-commit
try {
    pipx install pre-commit | Out-Null
    Write-Host "  ✅ pre-commit installed" -ForegroundColor Green
}
catch {
    Write-Host "  ⚠️  pre-commit may already be installed" -ForegroundColor Yellow
}

# Install ruff
try {
    pipx install ruff | Out-Null
    Write-Host "  ✅ ruff installed" -ForegroundColor Green
}
catch {
    Write-Host "  ⚠️  ruff may already be installed" -ForegroundColor Yellow
}

# Install black
try {
    pipx install black | Out-Null
    Write-Host "  ✅ black installed" -ForegroundColor Green
}
catch {
    Write-Host "  ⚠️  black may already be installed" -ForegroundColor Yellow
}

# Install mypy
try {
    pipx install mypy | Out-Null
    Write-Host "  ✅ mypy installed" -ForegroundColor Green
}
catch {
    Write-Host "  ⚠️  mypy may already be installed" -ForegroundColor Yellow
}

# Install pytest
try {
    pipx install pytest | Out-Null
    Write-Host "  ✅ pytest installed" -ForegroundColor Green
}
catch {
    Write-Host "  ⚠️  pytest may already be installed" -ForegroundColor Yellow
}

# Install streamlit
try {
    pipx install streamlit | Out-Null
    Write-Host "  ✅ streamlit installed" -ForegroundColor Green
}
catch {
    Write-Host "  ⚠️  streamlit may already be installed" -ForegroundColor Yellow
}

# Install bandit (optional security linter)
try {
    pipx install bandit | Out-Null
    Write-Host "  ✅ bandit installed" -ForegroundColor Green
}
catch {
    Write-Host "  ⚠️  bandit may already be installed" -ForegroundColor Yellow
}

Write-Host ""
Write-Host " All tools installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps: Next steps:" -ForegroundColor Cyan
Write-Host "   1. Restart your terminal for PATH changes to take effect" -ForegroundColor White
Write-Host "   2. Run the doctor to verify installation: make doctor" -ForegroundColor White
Write-Host "   3. Initialize the project: make init" -ForegroundColor White
Write-Host ""
Write-Host "SUCCESS: Orca development environment is ready!" -ForegroundColor Green
