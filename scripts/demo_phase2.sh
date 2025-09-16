#!/bin/bash

# Orca Core Phase 2 Demo Script
# This script demonstrates the AI/LLM explainability features

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_step() {
    echo -e "${CYAN}🔧 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if environment variable is set
check_env_var() {
    if [ -z "${!1}" ]; then
        print_error "$1 is not set"
        return 1
    fi
    return 0
}

# Function to wait for user input
wait_for_user() {
    echo -e "${YELLOW}Press Enter to continue...${NC}"
    read -r
}

# Function to run command with error handling
run_command() {
    local cmd="$1"
    local description="$2"

    print_step "$description"
    echo "Running: $cmd"

    if eval "$cmd"; then
        print_success "$description completed"
    else
        print_error "$description failed"
        return 1
    fi
}

# Main demo function
main() {
    print_header "Orca Core Phase 2 AI/LLM Demo"
    echo -e "${PURPLE}This demo showcases the explainability features including:${NC}"
    echo "• Azure OpenAI integration"
    echo "• XGBoost model predictions"
    echo "• LLM-generated explanations"
    echo "• Guardrails and safety features"
    echo "• Batch processing capabilities"
    echo "• Debug UI interface"
    echo ""
    echo -e "${YELLOW}💡 Tip: Copy .env.example to .env.local and configure your settings${NC}"
    echo ""

    # Check prerequisites
    print_header "Prerequisites Check"

    if ! command_exists python; then
        print_error "Python is not installed"
        exit 1
    fi

    if ! command_exists make; then
        print_error "Make is not installed"
        exit 1
    fi

    # Check if we're in the right directory
    if [ ! -f "Makefile" ] || [ ! -d "src/orca_core" ]; then
        print_error "Please run this script from the Orca Core project root directory"
        exit 1
    fi

    print_success "Prerequisites check passed"
    wait_for_user

    # Configuration check
    print_header "Configuration Check"

    print_step "Checking current configuration"
    if make test-config; then
        print_success "Configuration is valid"
    else
        print_warning "Configuration issues detected"
        echo -e "${YELLOW}You may need to run: make configure-azure-openai${NC}"
        wait_for_user
    fi

    wait_for_user

    # Model information
    print_header "Model Information"

    print_step "Displaying current model information"
    make model-info
    wait_for_user

    # Sample explanations demo
    print_header "Sample Explanations Demo"

    print_step "Testing stub model with template explanations"
    echo "Command: python -m orca_core.cli decide '{\"cart_total\": 100.0, \"currency\": \"USD\"}'"
    python -m orca_core.cli decide '{"cart_total": 100.0, "currency": "USD"}'
    wait_for_user

    print_step "Testing XGBoost model with template explanations"
    echo "Command: python -m orca_core.cli decide '{\"cart_total\": 1000.0, \"velocity_24h\": 3}' --ml xgb"
    python -m orca_core.cli decide '{"cart_total": 1000.0, "velocity_24h": 3}' --ml xgb
    wait_for_user

    # Check if Azure OpenAI is configured
    if check_env_var "AZURE_OPENAI_ENDPOINT" && check_env_var "AZURE_OPENAI_API_KEY"; then
        print_step "Testing LLM explanations with Azure OpenAI"
        echo "Command: python -m orca_core.cli decide '{\"cart_total\": 500.0, \"cross_border\": 1}' --ml xgb --mode ai --explain yes"
        python -m orca_core.cli decide '{"cart_total": 500.0, "cross_border": 1}' --ml xgb --mode ai --explain yes
        wait_for_user

        print_step "Testing LLM explanations with high-risk scenario"
        echo "Command: python -m orca_core.cli decide '{\"cart_total\": 5000.0, \"velocity_24h\": 10, \"cross_border\": 1}' --ml xgb --mode ai --explain yes"
        python -m orca_core.cli decide '{"cart_total": 5000.0, "velocity_24h": 10, "cross_border": 1}' --ml xgb --mode ai --explain yes
        wait_for_user
    else
        print_warning "Azure OpenAI not configured - skipping LLM explanation demos"
        echo -e "${YELLOW}To enable LLM explanations, run: make configure-azure-openai${NC}"
        wait_for_user
    fi

    # Batch processing demo
    print_header "Batch Processing Demo"

    print_step "Processing validation fixtures"
    echo "Command: python -m orca_core.cli decide-batch --glob 'fixtures/requests/*.json' --format table"
    python -m orca_core.cli decide-batch --glob 'fixtures/requests/*.json' --format table
    wait_for_user

    if [ -d "validation/phase2/fixtures" ]; then
        print_step "Processing Phase 2 validation fixtures"
        echo "Command: python -m orca_core.cli decide-batch --glob 'validation/phase2/fixtures/*.json' --format csv --output demo_results.csv"
        python -m orca_core.cli decide-batch --glob 'validation/phase2/fixtures/*.json' --format csv --output demo_results.csv
        print_success "Results saved to demo_results.csv"
        wait_for_user
    fi

    # Model training demo (if not already trained)
    print_header "Model Training Demo"

    if [ ! -f "models/xgb_model.joblib" ]; then
        print_step "Training XGBoost model (this may take a few minutes)"
        echo "Command: make train-xgb"
        make train-xgb
        wait_for_user
    else
        print_success "XGBoost model already exists - skipping training"
        wait_for_user
    fi

    # Generate plots demo
    print_header "Model Evaluation Plots"

    print_step "Generating model evaluation plots"
    echo "Command: make generate-plots"
    make generate-plots
    print_success "Plots generated in plots/ directory"
    wait_for_user

    # Debug UI demo
    print_header "Debug UI Demo"

    print_step "Launching Streamlit Debug UI"
    echo "Command: make debug-ui"
    echo -e "${YELLOW}The debug UI will open in your browser at http://localhost:8501${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop the debug UI when you're done exploring${NC}"
    wait_for_user

    # Start debug UI in background
    make debug-ui &
    DEBUG_UI_PID=$!

    echo -e "${GREEN}Debug UI started with PID: $DEBUG_UI_PID${NC}"
    echo -e "${YELLOW}Open http://localhost:8501 in your browser to explore the debug interface${NC}"
    echo -e "${YELLOW}Press Enter when you're done exploring the debug UI...${NC}"
    read -r

    # Stop debug UI
    print_step "Stopping debug UI"
    kill $DEBUG_UI_PID 2>/dev/null || true
    print_success "Debug UI stopped"

    # Summary
    print_header "Demo Summary"

    echo -e "${GREEN}🎉 Phase 2 Demo Completed Successfully!${NC}"
    echo ""
    echo -e "${PURPLE}What we demonstrated:${NC}"
    echo "✅ Configuration validation"
    echo "✅ Model information display"
    echo "✅ Template-based explanations"
    if check_env_var "AZURE_OPENAI_ENDPOINT" 2>/dev/null; then
        echo "✅ LLM-generated explanations with Azure OpenAI"
        echo "✅ Guardrails and safety features"
    else
        echo "⚠️  LLM explanations (Azure OpenAI not configured)"
    fi
    echo "✅ Batch processing capabilities"
    echo "✅ Model training and evaluation"
    echo "✅ Debug UI interface"
    echo ""
    echo -e "${CYAN}Next steps:${NC}"
    echo "• Review the generated plots in the plots/ directory"
    echo "• Check demo_results.csv for batch processing results"
    echo "• Explore the debug UI for interactive testing"
    echo "• Run 'make test' to ensure all tests pass"
    echo "• Review the documentation in docs/phase2_explainability.md"
    echo ""
    echo -e "${GREEN}Thank you for exploring Orca Core Phase 2! 🚀${NC}"
}

# Handle script interruption
trap 'print_error "Demo interrupted by user"; exit 1' INT

# Run main function
main "$@"
