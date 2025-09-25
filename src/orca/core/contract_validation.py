"""
Contract Validation using ocn-common schemas.

This module provides validation utilities for AP2 contracts and CloudEvents
using schemas from ocn-common.
"""

import json
import logging
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import Draft202012Validator

logger = logging.getLogger(__name__)


class ContractValidator:
    """Validator for AP2 contracts and CloudEvents using ocn-common schemas."""

    def __init__(self, ocn_common_path: Path | None = None):
        """
        Initialize contract validator.

        Args:
            ocn_common_path: Path to ocn-common schemas directory
        """
        if ocn_common_path is None:
            # Default to external/ocn-common relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            ocn_common_path = project_root / "external" / "ocn-common"

        self.ocn_common_path = ocn_common_path
        self.schemas: dict[str, dict[str, Any]] = {}
        self._load_schemas()

    def _load_schemas(self) -> None:
        """Load all schemas from ocn-common."""
        try:
            # Load CloudEvents schemas
            events_path = self.ocn_common_path / "common" / "events" / "v1"
            if events_path.exists():
                for schema_file in events_path.glob("*.schema.json"):
                    with open(schema_file) as f:
                        schema = json.load(f)
                        schema_name = schema_file.stem
                        self.schemas[schema_name] = schema
                        logger.info(f"Loaded schema: {schema_name}")

            # Load AP2 schemas
            ap2_path = self.ocn_common_path / "common" / "mandates" / "ap2" / "v1"
            if ap2_path.exists():
                for schema_file in ap2_path.glob("*.schema.json"):
                    with open(schema_file) as f:
                        schema = json.load(f)
                        schema_name = f"ap2_{schema_file.stem}"
                        self.schemas[schema_name] = schema
                        logger.info(f"Loaded AP2 schema: {schema_name}")

        except Exception as e:
            logger.warning(f"Failed to load schemas from ocn-common: {e}")

    def validate_cloud_event(self, event_data: dict[str, Any], event_type: str) -> bool:
        """
        Validate CloudEvent against ocn-common schema.

        Args:
            event_data: CloudEvent data to validate
            event_type: Type of CloudEvent (e.g., 'orca.decision.v1')

        Returns:
            True if valid, False otherwise
        """
        try:
            schema_key = f"{event_type}.schema"
            if schema_key not in self.schemas:
                logger.error(f"No schema found for event type: {event_type}")
                return False

            schema = self.schemas[schema_key]
            Draft202012Validator(schema).validate(event_data)
            logger.info(f"CloudEvent validation passed for {event_type}")
            return True

        except jsonschema.ValidationError as e:
            logger.error(f"CloudEvent validation failed for {event_type}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error validating CloudEvent {event_type}: {e}")
            return False

    def validate_ap2_decision(self, decision_data: dict[str, Any]) -> bool:
        """
        Validate AP2 decision payload against ocn-common schema.

        Args:
            decision_data: AP2 decision data to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            schema_key = "ap2_decision"
            if schema_key not in self.schemas:
                logger.warning("No AP2 decision schema found, using basic validation")
                return self._basic_decision_validation(decision_data)

            schema = self.schemas[schema_key]
            Draft202012Validator(schema).validate(decision_data)
            logger.info("AP2 decision validation passed")
            return True

        except jsonschema.ValidationError as e:
            logger.error(f"AP2 decision validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error validating AP2 decision: {e}")
            return False

    def validate_ap2_explanation(self, explanation_data: dict[str, Any]) -> bool:
        """
        Validate AP2 explanation payload against ocn-common schema.

        Args:
            explanation_data: AP2 explanation data to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            schema_key = "ap2_explanation"
            if schema_key not in self.schemas:
                logger.warning("No AP2 explanation schema found, using basic validation")
                return self._basic_explanation_validation(explanation_data)

            schema = self.schemas[schema_key]
            Draft202012Validator(schema).validate(explanation_data)
            logger.info("AP2 explanation validation passed")
            return True

        except jsonschema.ValidationError as e:
            logger.error(f"AP2 explanation validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error validating AP2 explanation: {e}")
            return False

    def _basic_decision_validation(self, decision_data: dict[str, Any]) -> bool:
        """Basic decision validation when schema is not available."""
        required_fields = ["ap2_version", "intent", "cart", "payment", "decision", "signing"]

        for field in required_fields:
            if field not in decision_data:
                logger.error(f"Missing required field in decision: {field}")
                return False

        # Validate decision result
        decision = decision_data.get("decision", {})
        result = decision.get("result")
        if result not in ["APPROVE", "DECLINE", "REVIEW"]:
            logger.error(f"Invalid decision result: {result}")
            return False

        return True

    def _basic_explanation_validation(self, explanation_data: dict[str, Any]) -> bool:
        """Basic explanation validation when schema is not available."""
        required_fields = [
            "trace_id",
            "decision_result",
            "explanation",
            "confidence",
            "model_provenance",
        ]

        for field in required_fields:
            if field not in explanation_data:
                logger.error(f"Missing required field in explanation: {field}")
                return False

        # Validate confidence range
        confidence = explanation_data.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
            logger.error(f"Invalid confidence value: {confidence}")
            return False

        return True

    def validate_file(self, file_path: str | Path, schema_type: str) -> bool:
        """
        Validate a JSON file against a schema.

        Args:
            file_path: Path to JSON file
            schema_type: Type of schema to validate against

        Returns:
            True if valid, False otherwise
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return False

            with open(file_path) as f:
                data = json.load(f)

            if schema_type.startswith("cloudevent:"):
                event_type = schema_type.replace("cloudevent:", "")
                return self.validate_cloud_event(data, event_type)
            elif schema_type == "ap2_decision":
                return self.validate_ap2_decision(data)
            elif schema_type == "ap2_explanation":
                return self.validate_ap2_explanation(data)
            else:
                logger.error(f"Unknown schema type: {schema_type}")
                return False

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in file {file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error validating file {file_path}: {e}")
            return False

    def get_validation_errors(self, data: dict[str, Any], schema_type: str) -> list[str]:
        """
        Get detailed validation errors for data against schema.

        Args:
            data: Data to validate
            schema_type: Type of schema to validate against

        Returns:
            List of validation error messages
        """
        errors = []

        try:
            if schema_type.startswith("cloudevent:"):
                event_type = schema_type.replace("cloudevent:", "")
                schema_key = f"{event_type}.schema"
                if schema_key not in self.schemas:
                    errors.append(f"No schema found for event type: {event_type}")
                    return errors

                schema = self.schemas[schema_key]
                validator = Draft202012Validator(schema)

            elif schema_type == "ap2_decision":
                schema_key = "ap2_decision"
                if schema_key not in self.schemas:
                    errors.append("No AP2 decision schema found")
                    return errors

                schema = self.schemas[schema_key]
                validator = Draft202012Validator(schema)

            elif schema_type == "ap2_explanation":
                schema_key = "ap2_explanation"
                if schema_key not in self.schemas:
                    errors.append("No AP2 explanation schema found")
                    return errors

                schema = self.schemas[schema_key]
                validator = Draft202012Validator(schema)

            else:
                errors.append(f"Unknown schema type: {schema_type}")
                return errors

            # Collect all validation errors
            for error in validator.iter_errors(data):
                errors.append(f"{error.json_path}: {error.message}")

        except Exception as e:
            errors.append(f"Error during validation: {e}")

        return errors


def get_contract_validator() -> ContractValidator:
    """Get configured contract validator instance."""
    return ContractValidator()


def validate_decision_contract(decision_data: dict[str, Any]) -> bool:
    """
    Convenience function to validate AP2 decision contract.

    Args:
        decision_data: AP2 decision data

    Returns:
        True if valid, False otherwise
    """
    validator = get_contract_validator()
    return validator.validate_ap2_decision(decision_data)


def validate_explanation_contract(explanation_data: dict[str, Any]) -> bool:
    """
    Convenience function to validate AP2 explanation contract.

    Args:
        explanation_data: AP2 explanation data

    Returns:
        True if valid, False otherwise
    """
    validator = get_contract_validator()
    return validator.validate_ap2_explanation(explanation_data)


def validate_cloud_event_contract(event_data: dict[str, Any], event_type: str) -> bool:
    """
    Convenience function to validate CloudEvent contract.

    Args:
        event_data: CloudEvent data
        event_type: Event type (e.g., 'orca.decision.v1')

    Returns:
        True if valid, False otherwise
    """
    validator = get_contract_validator()
    return validator.validate_cloud_event(event_data, event_type)
