"""
OCN Common Contracts Validation Module

This module provides utilities for validating JSON payloads against OCN schemas
and CloudEvents against their respective schemas.
"""

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

# Constants
CONTENT_TYPE = "application/vnd.ocn.ap2+json; version=1"
SCHEMA_VERSION = "v1"


class ContractValidationError(Exception):
    """Raised when contract validation fails."""

    pass


class SchemaLoader:
    """Loads and caches JSON schemas from the common directory."""

    def __init__(self, base_path: Path | None = None):
        """
        Initialize schema loader.

        Args:
            base_path: Base path to schemas directory. If None, uses current file location.
        """
        if base_path is None:
            # Get the directory containing this file, then go up to project root
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent
            base_path = project_root

        self.base_path = base_path
        self._schemas_cache: dict[str, dict[str, Any]] = {}

    def _load_schema(self, schema_path: Path) -> dict[str, Any]:
        """Load a JSON schema from file."""
        try:
            with open(schema_path) as f:
                schema = json.load(f)

            # Remove $id to avoid remote reference resolution issues
            if "$id" in schema:
                del schema["$id"]

            # Resolve $ref references by inlining the referenced schemas
            schema = self._resolve_references(schema, schema_path)

            # Validate that it's a valid JSON Schema
            Draft202012Validator.check_schema(schema)
            return schema
        except (json.JSONDecodeError, ValidationError) as e:
            raise ContractValidationError(f"Invalid schema at {schema_path}: {e}") from e
        except FileNotFoundError as e:
            raise ContractValidationError(f"Schema not found at {schema_path}") from e

    def _resolve_references(self, schema: dict[str, Any], schema_path: Path) -> dict[str, Any]:
        """Resolve $ref references by inlining referenced schemas."""
        if isinstance(schema, dict):
            if "$ref" in schema:
                ref_path = schema["$ref"]
                # Handle relative references from events to mandates
                if ref_path.startswith("../mandates/"):
                    mandate_name = ref_path.split("/")[-1]
                    mandate_path = self.base_path / "common" / "mandates" / mandate_name
                    if mandate_path.exists():
                        with open(mandate_path) as f:
                            referenced_schema = json.load(f)
                        # Remove $id and recursively resolve any nested references
                        if "$id" in referenced_schema:
                            del referenced_schema["$id"]
                        return self._resolve_references(referenced_schema, mandate_path)
                    else:
                        raise ContractValidationError(
                            f"Referenced schema not found: {mandate_path}"
                        )
                # Handle references within mandates directory (same directory)
                elif not ref_path.startswith("/") and not ref_path.startswith("http"):
                    # This is a relative reference within the mandates directory
                    mandate_path = self.base_path / "common" / "mandates" / ref_path
                    if mandate_path.exists():
                        with open(mandate_path) as f:
                            referenced_schema = json.load(f)
                        # Remove $id and recursively resolve any nested references
                        if "$id" in referenced_schema:
                            del referenced_schema["$id"]
                        return self._resolve_references(referenced_schema, mandate_path)
                    else:
                        raise ContractValidationError(
                            f"Referenced schema not found: {mandate_path}"
                        )
                else:
                    # For other references, return as-is (they might be valid)
                    return schema
            else:
                # Recursively resolve references in nested objects
                resolved = {}
                for key, value in schema.items():
                    resolved[key] = self._resolve_references(value, schema_path)
                return resolved
        elif isinstance(schema, list):
            # Recursively resolve references in lists
            return [self._resolve_references(item, schema_path) for item in schema]
        else:
            # Return primitive values as-is
            return schema

    def get_schema(self, schema_name: str, schema_type: str = "mandates") -> dict[str, Any]:
        """
        Get a cached schema by name and type.

        Args:
            schema_name: Name of the schema (e.g., 'intent_mandate')
            schema_type: Type of schema ('mandates' or 'events')

        Returns:
            The JSON schema dictionary
        """
        cache_key = f"{schema_type}/{schema_name}"

        if cache_key not in self._schemas_cache:
            if schema_type == "mandates":
                schema_path = self.base_path / "common" / "mandates" / f"{schema_name}.schema.json"
            elif schema_type == "events":
                schema_path = (
                    self.base_path / "common" / "events" / "v1" / f"{schema_name}.schema.json"
                )
            else:
                raise ContractValidationError(f"Unknown schema type: {schema_type}")

            self._schemas_cache[cache_key] = self._load_schema(schema_path)

        return self._schemas_cache[cache_key]

    def list_available_schemas(self) -> dict[str, list]:
        """List all available schemas by type."""
        schemas: dict[str, list[str]] = {"mandates": [], "events": []}

        # List mandate schemas
        mandates_path = self.base_path / "common" / "mandates"
        if mandates_path.exists():
            for schema_file in mandates_path.glob("*.schema.json"):
                schemas["mandates"].append(schema_file.stem)

        # List event schemas
        events_path = self.base_path / "common" / "events" / "v1"
        if events_path.exists():
            for schema_file in events_path.glob("*.schema.json"):
                schemas["events"].append(schema_file.stem)

        return schemas


class ContractValidator:
    """Validates JSON payloads against OCN schemas."""

    def __init__(self, schema_loader: SchemaLoader | None = None):
        """
        Initialize contract validator.

        Args:
            schema_loader: Schema loader instance. If None, creates a new one.
        """
        self.schema_loader = schema_loader or SchemaLoader()
        self._validators_cache: dict[str, Draft202012Validator] = {}

    def _get_validator(
        self, schema_name: str, schema_type: str = "mandates"
    ) -> Draft202012Validator:
        """Get a cached validator for a schema."""
        cache_key = f"{schema_type}/{schema_name}"

        if cache_key not in self._validators_cache:
            schema = self.schema_loader.get_schema(schema_name, schema_type)
            self._validators_cache[cache_key] = Draft202012Validator(schema)

        return self._validators_cache[cache_key]

    def validate_json(self, payload: dict[str, Any] | str, schema_name: str) -> bool:
        """
        Validate a JSON payload against a mandate schema.

        Args:
            payload: JSON payload to validate (dict or JSON string)
            schema_name: Name of the mandate schema (e.g., 'intent_mandate')

        Returns:
            True if validation passes

        Raises:
            ContractValidationError: If validation fails
        """
        try:
            # Parse payload if it's a string
            if isinstance(payload, str):
                payload = json.loads(payload)

            validator = self._get_validator(schema_name, "mandates")
            validator.validate(payload)
            return True

        except json.JSONDecodeError as e:
            raise ContractValidationError(f"Invalid JSON payload: {e}") from e
        except ValidationError as e:
            raise ContractValidationError(
                f"Validation failed for schema '{schema_name}': {e.message}"
            ) from e
        except Exception as e:
            raise ContractValidationError(f"Unexpected validation error: {e}") from e

    def validate_cloudevent(self, payload: dict[str, Any] | str, type_name: str) -> bool:
        """
        Validate a CloudEvent payload against its schema.

        Args:
            payload: CloudEvent payload to validate (dict or JSON string)
            type_name: Type name of the CloudEvent (e.g., 'orca.decision.v1')

        Returns:
            True if validation passes

        Raises:
            ContractValidationError: If validation fails
        """
        try:
            # Parse payload if it's a string
            if isinstance(payload, str):
                payload = json.loads(payload)

            # Map type names to schema names
            type_to_schema = {
                "ocn.orca.decision.v1": "orca.decision.v1",
                "ocn.orca.explanation.v1": "orca.explanation.v1",
                "ocn.weave.audit.v1": "weave.audit.v1",
            }

            schema_name = type_to_schema.get(type_name)
            if not schema_name:
                raise ContractValidationError(f"Unknown CloudEvent type: {type_name}")

            validator = self._get_validator(schema_name, "events")
            validator.validate(payload)
            return True

        except json.JSONDecodeError as e:
            raise ContractValidationError(f"Invalid JSON payload: {e}") from e
        except ValidationError as e:
            raise ContractValidationError(
                f"Validation failed for CloudEvent type '{type_name}': {e.message}"
            ) from e
        except Exception as e:
            raise ContractValidationError(f"Unexpected validation error: {e}") from e

    def get_validation_errors(
        self, payload: dict[str, Any] | str, schema_name: str, schema_type: str = "mandates"
    ) -> list:
        """
        Get detailed validation errors for a payload.

        Args:
            payload: JSON payload to validate (dict or JSON string)
            schema_name: Name of the schema
            schema_type: Type of schema ('mandates' or 'events')

        Returns:
            List of validation error messages
        """
        try:
            # Parse payload if it's a string
            if isinstance(payload, str):
                payload = json.loads(payload)

            validator = self._get_validator(schema_name, schema_type)
            errors = []

            for error in validator.iter_errors(payload):
                errors.append(
                    {
                        "path": ".".join(str(p) for p in error.path),
                        "message": error.message,
                        "schema_path": ".".join(str(p) for p in error.schema_path),
                    }
                )

            return errors

        except json.JSONDecodeError as e:
            return [{"path": "", "message": f"Invalid JSON: {e}", "schema_path": ""}]
        except Exception as e:
            return [{"path": "", "message": f"Validation error: {e}", "schema_path": ""}]


# Global validator instance
_global_validator: ContractValidator | None = None


def get_contract_validator() -> ContractValidator:
    """Get the global contract validator instance."""
    global _global_validator
    if _global_validator is None:
        _global_validator = ContractValidator()
    return _global_validator


def validate_json(payload: dict[str, Any] | str, schema_name: str) -> bool:
    """
    Validate a JSON payload against a mandate schema.

    Convenience function using the global validator.

    Args:
        payload: JSON payload to validate (dict or JSON string)
        schema_name: Name of the mandate schema (e.g., 'intent_mandate')

    Returns:
        True if validation passes

    Raises:
        ContractValidationError: If validation fails
    """
    validator = get_contract_validator()
    return validator.validate_json(payload, schema_name)


def validate_cloudevent(payload: dict[str, Any] | str, type_name: str) -> bool:
    """
    Validate a CloudEvent payload against its schema.

    Convenience function using the global validator.

    Args:
        payload: CloudEvent payload to validate (dict or JSON string)
        type_name: Type name of the CloudEvent (e.g., 'ocn.orca.decision.v1')

    Returns:
        True if validation passes

    Raises:
        ContractValidationError: If validation fails
    """
    validator = get_contract_validator()
    return validator.validate_cloudevent(payload, type_name)


def list_available_schemas() -> dict[str, list]:
    """List all available schemas by type."""
    validator = get_contract_validator()
    return validator.schema_loader.list_available_schemas()


# Export constants and main functions
__all__ = [
    "CONTENT_TYPE",
    "SCHEMA_VERSION",
    "ContractValidationError",
    "ContractValidator",
    "SchemaLoader",
    "validate_json",
    "validate_cloudevent",
    "get_contract_validator",
    "list_available_schemas",
]
