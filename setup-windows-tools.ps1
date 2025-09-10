# --- Orca Day-1: system tools (Windows) ---
$ErrorActionPreference = "Stop"

Write-Host "Starting Orca development environment setup..." -ForegroundColor Green

# Winget installs
Write-Host "Installing Git..." -ForegroundColor Yellow
winget install -e --id Git.Git | Out-Null

Write-Host "Installing GitHub CLI..." -ForegroundColor Yellow
winget install -e --id GitHub.cli | Out-Null

Write-Host "Installing Python 3.12..." -ForegroundColor Yellow
winget install -e --id Python.Python.3.12 | Out-Null

Write-Host "Installing pipx..." -ForegroundColor Yellow
winget install -e --id Python.Pipx | Out-Null

Write-Host "Installing GNU Make..." -ForegroundColor Yellow
winget install -e --id GnuWin32.Make | Out-Null

Write-Host "Installing Node.js LTS..." -ForegroundColor Yellow
winget install -e --id OpenJS.NodeJS.LTS | Out-Null

# uv via pipx
Write-Host "Setting up pipx and installing uv..." -ForegroundColor Yellow
pipx ensurepath
pipx install uv

Write-Host "All tools installed successfully!" -ForegroundColor Green
Write-Host "Please reopen your terminal if 'pipx' command is not found." -ForegroundColor Cyan
Write-Host "Orca development environment is ready!" -ForegroundColor Green
