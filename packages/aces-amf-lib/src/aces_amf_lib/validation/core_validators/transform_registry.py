# SPDX-License-Identifier: Apache-2.0
# Copyright Contributors to the ACES Project.
"""
Transform ID registry validation.

Validates transform IDs against a caller-provided TransformRegistry.
The registry must be injected via ValidationContext.transform_registry.
If no registry is provided, RegistryNotConfiguredError is raised.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..types import (
    RegistryNotConfiguredError,
    ValidationContext,
    ValidationLevel,
    ValidationMessage,
    ValidationType,
)
from ._nested import collect_sub_transforms

if TYPE_CHECKING:
    from ...amf_v2 import AcesMetadataFile, PipelineType


class TransformRegistryValidator:
    """Validates transform IDs against an injected TransformRegistry.

    Requires context.transform_registry to be set. If it is None,
    RegistryNotConfiguredError is raised — this is a configuration error,
    not a validation failure.

    To skip this validator, pass exclude=["transform_id_registry"] to validate_semantic().
    """

    name = "transform_id_registry"

    def validate(self, amf: AcesMetadataFile, context: ValidationContext) -> list[ValidationMessage]:
        if context.transform_registry is None:
            raise RegistryNotConfiguredError(
                "TransformRegistryValidator requires a transform registry but none was provided. "
                "Pass a TransformRegistry to validate_semantic(transform_registry=...) or "
                "exclude this validator with exclude=['transform_id_registry']."
            )

        messages: list[ValidationMessage] = []

        if amf.pipeline:
            self._validate_pipeline(amf.pipeline, "", messages, context)

        for idx, archived in enumerate(amf.archived_pipeline):
            self._validate_pipeline(archived, f"Archived pipeline #{idx + 1} ", messages, context)

        return messages

    def _validate_pipeline(
        self, pipeline: PipelineType, prefix: str, messages: list[ValidationMessage], context: ValidationContext
    ) -> None:
        registry = context.transform_registry

        # Extract ACES system version for version-scoped registry lookups
        version_str = None
        sv = getattr(getattr(pipeline, "pipeline_info", None), "system_version", None)
        if sv is not None:
            version_str = f"v{sv.major_version}.{sv.minor_version}"

        def _check_id(transform_id: str, label: str) -> None:
            if not registry.is_valid_transform_id(transform_id, version=version_str):
                scope = f" for ACES {version_str}" if version_str else ""
                messages.append(
                    ValidationMessage(
                        level=ValidationLevel.WARNING,
                        validation_type=ValidationType.INVALID_TRANSFORM_ID,
                        message=f"{label} uses unknown transform ID{scope}: {transform_id}",
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
        for idx, lt in enumerate(pipeline.look_transforms):
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
