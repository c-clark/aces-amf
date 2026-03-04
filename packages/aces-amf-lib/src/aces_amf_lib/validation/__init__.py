# SPDX-License-Identifier: Apache-2.0
"""
AMF validation: schema validation and extensible semantic validation.

Usage:
    from aces_amf_lib.validation import validate_schema, validate_semantic

    # Schema-only validation
    messages = validate_schema("example.amf")

    # Semantic validation (all registered validators)
    messages = validate_semantic("example.amf")

    # Both combined
    messages = validate_all("example.amf")
"""

from __future__ import annotations

from pathlib import Path

from .types import (
    AMFValidationError,
    ValidationContext,
    ValidationLevel,
    ValidationMessage,
    ValidationType,
)
from .schema import validate_schema
from .registry import ValidatorRegistry, get_default_registry

# Import core validators to trigger auto-registration
from . import core_validators  # noqa: F401


def validate_semantic(
    amf_path: Path | str,
    *,
    base_path: Path | None = None,
    validators: list[str] | None = None,
    exclude: list[str] | None = None,
    uuid_pool: set[str] | None = None,
    registry: ValidatorRegistry | None = None,
) -> list[ValidationMessage]:
    """Run semantic validation on an AMF file.

    Args:
        amf_path: Path to the AMF file.
        base_path: Base directory for resolving relative file paths.
        validators: If provided, only run these validators (by name).
        exclude: If provided, skip these validators (by name).
        uuid_pool: Set of UUIDs for cross-file duplicate detection.
        registry: Validator registry to use. Defaults to the global registry.

    Returns:
        List of validation messages.
    """
    from ..amf_utilities import load_amf

    amf_path = Path(amf_path)

    # Load the AMF
    try:
        amf = load_amf(amf_path, validate=False)
    except Exception as e:
        return [
            ValidationMessage(
                level=ValidationLevel.ERROR,
                validation_type=ValidationType.LOAD_ERROR,
                message=f"Failed to load AMF: {e}",
                file_path=amf_path,
            )
        ]

    context = ValidationContext(
        amf_path=amf_path,
        base_path=base_path,
        uuid_pool=uuid_pool,
    )

    reg = registry or get_default_registry()
    return reg.validate(amf, context, validators=validators, exclude=exclude)


def validate_all(
    amf_path: Path | str,
    *,
    base_path: Path | None = None,
    validators: list[str] | None = None,
    exclude: list[str] | None = None,
    uuid_pool: set[str] | None = None,
    registry: ValidatorRegistry | None = None,
) -> list[ValidationMessage]:
    """Run both schema and semantic validation on an AMF file.

    Args:
        amf_path: Path to the AMF file.
        base_path: Base directory for resolving relative file paths.
        validators: If provided, only run these semantic validators (by name).
        exclude: If provided, skip these semantic validators (by name).
        uuid_pool: Set of UUIDs for cross-file duplicate detection.
        registry: Validator registry to use. Defaults to the global registry.

    Returns:
        Combined list of validation messages (schema first, then semantic).
    """
    messages = validate_schema(amf_path)

    # Only run semantic validation if no schema errors
    schema_errors = [m for m in messages if m.level == ValidationLevel.ERROR]
    if not schema_errors:
        messages.extend(
            validate_semantic(
                amf_path,
                base_path=base_path,
                validators=validators,
                exclude=exclude,
                uuid_pool=uuid_pool,
                registry=registry,
            )
        )

    return messages


__all__ = [
    "validate_schema",
    "validate_semantic",
    "validate_all",
    "AMFValidationError",
    "ValidatorRegistry",
    "get_default_registry",
    "ValidationContext",
    "ValidationLevel",
    "ValidationMessage",
    "ValidationType",
]
