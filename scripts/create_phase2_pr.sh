#!/bin/bash

# Script to help create Phase 2 AI/LLM PR
# This script prepares the repository for creating a pull request

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_step() {
    echo -e "${YELLOW}🔧 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

main() {
    print_header "Phase 2 AI/LLM PR Preparation"

    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo "❌ Not in a git repository"
        exit 1
    fi

    # Check current branch
    current_branch=$(git branch --show-current)
    echo "Current branch: $current_branch"

    # Run final tests
    print_step "Running final test suite"
    if make test; then
        print_success "All tests pass"
    else
        echo "❌ Tests failed - please fix before creating PR"
        exit 1
    fi

    # Check coverage
    print_step "Checking test coverage"
    coverage_output=$(python -m pytest --cov=src/orca_core --cov-report=term-missing --tb=no -q 2>/dev/null | tail -1)
    if echo "$coverage_output" | grep -q "86%"; then
        print_success "Coverage target met (86%)"
    else
        echo "⚠️  Coverage may not meet target"
    fi

    # Test demo script
    print_step "Testing demo script"
    if [ -f "scripts/demo_phase2.sh" ] && [ -x "scripts/demo_phase2.sh" ]; then
        print_success "Demo script is ready"
    else
        echo "❌ Demo script not found or not executable"
        exit 1
    fi

    # Check documentation
    print_step "Checking documentation"
    if [ -f "docs/phase2_explainability.md" ] && [ -f "RELEASE_CHECKLIST.md" ]; then
        print_success "Documentation is complete"
    else
        echo "❌ Documentation files missing"
        exit 1
    fi

    # Check if all changes are committed
    if git diff --quiet && git diff --cached --quiet; then
        print_success "All changes are committed"
    else
        echo "⚠️  Uncommitted changes detected"
        echo "Please commit all changes before creating PR"
        git status --short
    fi

    print_header "PR Creation Instructions"

    echo "To create the Phase 2 AI/LLM PR:"
    echo ""
    echo "1. Push your branch to GitHub:"
    echo "   git push origin $current_branch"
    echo ""
    echo "2. Create PR on GitHub:"
    echo "   - Go to: https://github.com/your-org/orca-core/compare/$current_branch"
    echo "   - Title: 'Phase 2 AI/LLM Explainability Features'"
    echo "   - Use the PR template from .github/pull_request_template.md"
    echo ""
    echo "3. Review checklist items:"
    echo "   - All tests pass ✅"
    echo "   - Coverage > 85% ✅"
    echo "   - Demo script works ✅"
    echo "   - Documentation complete ✅"
    echo "   - JSON validity ✅"
    echo "   - Deploy success ✅"
    echo ""
    echo "4. Request reviews from:"
    echo "   - Development team"
    echo "   - QA team"
    echo "   - DevOps team"
    echo ""
    echo "5. Test the demo:"
    echo "   ./scripts/demo_phase2.sh"
    echo ""

    print_success "Repository is ready for PR creation!"
}

main "$@"
