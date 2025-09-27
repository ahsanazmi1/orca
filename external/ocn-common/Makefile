.PHONY: test validate-schemas install-deps clean help

# Default target
help:
	@echo "OCN Common - Phase 3 CloudEvent Schemas"
	@echo "========================================"
	@echo ""
	@echo "Available targets:"
	@echo "  test            - Run all schema validation tests"
	@echo "  validate-schemas - Validate all JSON schemas and examples"
	@echo "  install-deps    - Install Python dependencies"
	@echo "  clean           - Clean up temporary files"
	@echo "  help            - Show this help message"

# Install Python dependencies
install-deps:
	@echo "Installing Python dependencies..."
	pip install jsonschema

# Run schema validation tests
test: install-deps
	@echo "Running Phase 3 schema validation tests..."
	cd tests && python test_phase3_schemas.py

# Validate JSON syntax
validate-schemas:
	@echo "Validating JSON syntax in schemas..."
	@for file in common/events/v1/*.json; do \
		echo "Validating $$file"; \
		python -m json.tool "$$file" > /dev/null || exit 1; \
	done
	@echo "Validating JSON syntax in examples..."
	@for file in examples/events/*.json; do \
		echo "Validating $$file"; \
		python -m json.tool "$$file" > /dev/null || exit 1; \
	done
	@echo "✅ All JSON files are valid"

# Clean up temporary files
clean:
	@echo "Cleaning up temporary files..."
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	find . -name "*.tmp" -delete

# Quick validation (no dependencies)
validate-quick:
	@echo "Quick validation of JSON syntax..."
	@python -m json.tool common/events/v1/weave.bid_request.v1.schema.json > /dev/null && echo "✅ weave.bid_request.v1.schema.json"
	@python -m json.tool common/events/v1/weave.bid_response.v1.schema.json > /dev/null && echo "✅ weave.bid_response.v1.schema.json"
	@python -m json.tool common/events/v1/oasis.constraint.v1.schema.json > /dev/null && echo "✅ oasis.constraint.v1.schema.json"
	@python -m json.tool common/events/v1/onyx.trust_signal.v1.schema.json > /dev/null && echo "✅ onyx.trust_signal.v1.schema.json"
	@python -m json.tool examples/events/weave.bid_request.example.json > /dev/null && echo "✅ weave.bid_request.example.json"
	@python -m json.tool examples/events/weave.bid_response.example.json > /dev/null && echo "✅ weave.bid_response.example.json"
	@python -m json.tool examples/events/oasis.constraint.example.json > /dev/null && echo "✅ oasis.constraint.example.json"
	@python -m json.tool examples/events/onyx.trust_signal.example.json > /dev/null && echo "✅ onyx.trust_signal.example.json"
	@echo "✅ All Phase 3 schemas and examples are valid JSON"
