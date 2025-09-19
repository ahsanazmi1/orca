#!/bin/bash

# Orca Core Release Script
# Usage: ./scripts/create_release.sh <version> <tag_type>
# Example: ./scripts/create_release.sh v0.3.0-ap2 ap2

set -e

VERSION=${1:-"v0.3.0-ap2"}
TAG_TYPE=${2:-"ap2"}
RELEASE_NOTES_FILE="RELEASE_NOTES_${VERSION}.md"

echo "🚀 Creating Orca Core Release: $VERSION"
echo "=================================="

# Check if we're on the right branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "master" ]; then
    echo "⚠️  Warning: Not on master branch (current: $CURRENT_BRANCH)"
    echo "   Make sure to merge the PR first!"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if release notes exist
if [ ! -f "$RELEASE_NOTES_FILE" ]; then
    echo "❌ Release notes file not found: $RELEASE_NOTES_FILE"
    exit 1
fi

# Verify model artifacts exist
echo "🔍 Verifying model artifacts..."
MODEL_DIR="models/xgb/1.0.0"
REQUIRED_FILES=("calibrator.pkl" "scaler.pkl" "feature_spec.json" "metadata.json" "model.json")

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$MODEL_DIR/$file" ]; then
        echo "❌ Missing model artifact: $MODEL_DIR/$file"
        exit 1
    fi
done

# Generate SHA-256 hashes for model artifacts
echo "🔐 Generating model artifact hashes..."
echo "Model Artifacts (v1.0.0):" > model_hashes.txt
for file in "${REQUIRED_FILES[@]}"; do
    hash=$(sha256sum "$MODEL_DIR/$file" | cut -d' ' -f1)
    echo "- $file: $hash" >> model_hashes.txt
done

# Run tests to ensure everything works
echo "🧪 Running validation tests..."
python scripts/validate_samples.py

# Create and push tag
echo "🏷️  Creating tag: $VERSION"
git tag -a "$VERSION" -m "Release $VERSION: AP2-compliant decision engine with ML integration

$(cat model_hashes.txt)

This release introduces:
- Complete AP2 contract implementation
- Real XGBoost model with calibration and SHAP
- Cryptographic signing and receipt hashing
- Legacy adapter for backward compatibility
- Comprehensive testing and documentation

See RELEASE_NOTES_${VERSION}.md for full details."

echo "📤 Pushing tag to remote..."
git push origin "$VERSION"

# Create GitHub release
echo "📋 Creating GitHub release..."
gh release create "$VERSION" \
    --title "🚀 Orca Core $VERSION - AP2-Compliant Decision Engine" \
    --notes-file "$RELEASE_NOTES_FILE" \
    --verify-tag

# Clean up
rm -f model_hashes.txt

echo "✅ Release $VERSION created successfully!"
echo "🔗 View release: https://github.com/ahsanazmi1/orca/releases/tag/$VERSION"

# Next steps
echo ""
echo "🎯 Next Steps:"
echo "1. Update version in pyproject.toml for next development cycle"
echo "2. Create v0.3.1-ml branch for ML enhancements"
echo "3. Update documentation with new version references"
echo "4. Notify stakeholders of the release"
