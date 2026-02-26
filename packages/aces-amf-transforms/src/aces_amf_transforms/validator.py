# SPDX-License-Identifier: Apache-2.0
"""
Transform ID validator — validates transform IDs against the official registry.

This validator is registered via entry point and integrates with the
aces-amf-lib validation plugin system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aces_amf_lib.validation.core_validators._nested import collect_sub_transforms
from aces_amf_lib.validation.types import (
    ValidationContext,
    ValidationLevel,
    ValidationMessage,
    ValidationType,
)

from .registry import ACESTransformRegistry

if TYPE_CHECKING:
    from aces_amf_lib.amf_v2 import AcesMetadataFile, PipelineType


class TransformIdValidator:
    """Validates transform IDs against the official ACES transform registry.

    This validator checks that all transform IDs referenced in an AMF file
    exist in the bundled ACES transforms registry, issuing warnings for
    unknown IDs.
    """

    name = "transform_id_registry"

    def __init__(self, registry: ACESTransformRegistry | None = None):
        self._registry = registry or ACESTransformRegistry()

    def validate(self, amf: AcesMetadataFile, context: ValidationContext) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []

        if amf.pipeline:
            self._validate_pipeline(amf.pipeline, "", messages, context)

        for idx, archived in enumerate(amf.archived_pipeline):
            self._validate_pipeline(archived, f"Archived pipeline #{idx + 1} ", messages, context)

        return messages

    def _validate_pipeline(
        self, pipeline: PipelineType, prefix: str, messages: list[ValidationMessage], context: ValidationContext
    ) -> None:
        def _check_id(transform_id: str, label: str) -> None:
            if not self._registry.is_valid_transform_id(transform_id):
                messages.append(
                    ValidationMessage(
                        level=ValidationLevel.WARNING,
                        validation_type=ValidationType.INVALID_TRANSFORM_ID,
                        message=f"{label} uses unknown transform ID: {transform_id}",
                        file_path=context.amf_path,
                    )
                )

        # Input transform + nested sub-transforms
        if pipeline.input_transform:
            if pipeline.input_transform.transform_id:
                _check_id(pipeline.input_transform.transform_id, f"{prefix}Input transform")
            for sub_label, sub in collect_sub_transforms(pipeline.input_transform, f"{prefix}Input"):
                if sub.transform_id:
                    _check_id(sub.transform_id, sub_label)

        # Look transforms + working space transforms
        for idx, lt in enumerate(pipeline.look_transform):
            if lt.transform_id:
                desc = lt.description or f"Look transform #{idx + 1}"
                _check_id(lt.transform_id, f"{prefix}{desc}")

            if lt.cdl_working_space:
                ws = lt.cdl_working_space
                if ws.from_cdl_working_space and ws.from_cdl_working_space.transform_id:
                    _check_id(ws.from_cdl_working_space.transform_id, f"{prefix}Look #{idx+1} fromCdlWorkingSpace")
                if ws.to_cdl_working_space and ws.to_cdl_working_space.transform_id:
                    _check_id(ws.to_cdl_working_space.transform_id, f"{prefix}Look #{idx+1} toCdlWorkingSpace")

        # Output transform + nested sub-transforms
        if pipeline.output_transform:
            if pipeline.output_transform.transform_id:
                _check_id(pipeline.output_transform.transform_id, f"{prefix}Output transform")
            for sub_label, sub in collect_sub_transforms(pipeline.output_transform, f"{prefix}Output"):
                if sub.transform_id:
                    _check_id(sub.transform_id, sub_label)
