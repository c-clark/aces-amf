# SPDX-License-Identifier: Apache-2.0
"""CDL working space validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..types import ValidationContext, ValidationLevel, ValidationMessage, ValidationType

if TYPE_CHECKING:
    from ...amf_v2 import AcesMetadataFile


class WorkingSpaceValidator:
    name = "working_space"

    def validate(self, amf: AcesMetadataFile, context: ValidationContext) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []

        if amf.pipeline:
            messages.extend(_validate_pipeline_working_space(amf.pipeline.look_transform, "", context.amf_path))

        for idx, archived in enumerate(amf.archived_pipeline):
            messages.extend(
                _validate_pipeline_working_space(
                    archived.look_transform, f"Archived pipeline #{idx + 1} ", context.amf_path
                )
            )

        return messages


def _validate_pipeline_working_space(look_transforms, prefix: str, amf_path) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []

    for idx, lt in enumerate(look_transforms):
        # Resolve CDL element name alternates (ASC_SOP/SOPNode, ASC_SAT/SatNode)
        sop = lt.asc_sop or getattr(lt, "sopnode", None)
        sat = lt.asc_sat or getattr(lt, "sat_node", None)
        if not sop and not sat:
            continue

        desc = f"{prefix}{lt.description or f'Look transform #{idx + 1}'}"

        if not lt.cdl_working_space:
            messages.append(
                ValidationMessage(
                    level=ValidationLevel.WARNING,
                    validation_type=ValidationType.MISSING_CDL_WORKING_SPACE,
                    message=f"{desc} has CDL but no working space specified",
                    file_path=amf_path,
                )
            )
            continue

        if not lt.cdl_working_space.from_cdl_working_space:
            messages.append(
                ValidationMessage(
                    level=ValidationLevel.ERROR,
                    validation_type=ValidationType.CDL_WORKING_SPACE_MISMATCH,
                    message=f"{desc} missing required fromCdlWorkingSpace",
                    file_path=amf_path,
                )
            )

    return messages
