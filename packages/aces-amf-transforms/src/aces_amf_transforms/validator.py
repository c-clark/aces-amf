# SPDX-License-Identifier: Apache-2.0
"""
Transform ID validator — validates transform IDs against the official registry.

This validator is registered via entry point and integrates with the
aces-amf-lib validation plugin system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aces_amf_lib.validation.types import (
    ValidationContext,
    ValidationLevel,
    ValidationMessage,
    ValidationType,
)

from .registry import ACESTransformRegistry

if TYPE_CHECKING:
    from aces_amf_lib import ACESAMF


class TransformIdValidator:
    """Validates transform IDs against the official ACES transform registry.

    This validator checks that all transform IDs referenced in an AMF file
    exist in the bundled ACES transforms registry, issuing warnings for
    unknown IDs.
    """

    name = "transform_id_registry"

    def __init__(self, registry: ACESTransformRegistry | None = None):
        self._registry = registry or ACESTransformRegistry()

    def validate(self, amf: ACESAMF, context: ValidationContext) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []

        def _check_id(transform_id: str, label: str):
            if not self._registry.is_valid_transform_id(transform_id):
                messages.append(
                    ValidationMessage(
                        level=ValidationLevel.WARNING,
                        validation_type=ValidationType.INVALID_TRANSFORM_ID,
                        message=f"{label} uses unknown transform ID: {transform_id}",
                        file_path=context.amf_path,
                    )
                )

        # Input transform
        if amf.amf.pipeline and amf.amf.pipeline.input_transform and amf.amf.pipeline.input_transform.transform_id:
            _check_id(amf.amf.pipeline.input_transform.transform_id, "Input transform")

        # Look transforms
        if amf.amf.pipeline and amf.amf.pipeline.look_transform:
            for idx, lt in enumerate(amf.amf.pipeline.look_transform):
                if lt.transform_id:
                    desc = lt.description or f"Look transform #{idx + 1}"
                    _check_id(lt.transform_id, desc)

        # Output transform
        if amf.amf.pipeline and amf.amf.pipeline.output_transform and amf.amf.pipeline.output_transform.transform_id:
            _check_id(amf.amf.pipeline.output_transform.transform_id, "Output transform")

        # Working space transforms
        if amf.amf.pipeline and amf.amf.pipeline.look_transform:
            for idx, lt in enumerate(amf.amf.pipeline.look_transform):
                if lt.cdl_working_space:
                    ws = lt.cdl_working_space
                    if ws.from_cdl_working_space and ws.from_cdl_working_space.transform_id:
                        _check_id(ws.from_cdl_working_space.transform_id, f"Look #{idx+1} fromCdlWorkingSpace")
                    if ws.to_cdl_working_space and ws.to_cdl_working_space.transform_id:
                        _check_id(ws.to_cdl_working_space.transform_id, f"Look #{idx+1} toCdlWorkingSpace")

        return messages
