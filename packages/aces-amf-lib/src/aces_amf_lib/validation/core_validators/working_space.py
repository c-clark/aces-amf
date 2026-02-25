# SPDX-License-Identifier: Apache-2.0
"""CDL working space validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..types import ValidationContext, ValidationLevel, ValidationMessage, ValidationType

if TYPE_CHECKING:
    from ...aces_amf import ACESAMF


class WorkingSpaceValidator:
    name = "working_space"

    def validate(self, amf: ACESAMF, context: ValidationContext) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []

        if not amf.amf.pipeline or not amf.amf.pipeline.look_transform:
            return messages

        for idx, lt in enumerate(amf.amf.pipeline.look_transform):
            if not lt.asc_sop and not lt.asc_sat:
                continue

            desc = lt.description or f"Look transform #{idx + 1}"

            if not lt.cdl_working_space:
                messages.append(
                    ValidationMessage(
                        level=ValidationLevel.WARNING,
                        validation_type=ValidationType.MISSING_CDL_WORKING_SPACE,
                        message=f"{desc} has CDL but no working space specified",
                        file_path=context.amf_path,
                    )
                )
                continue

            if not lt.cdl_working_space.from_cdl_working_space:
                messages.append(
                    ValidationMessage(
                        level=ValidationLevel.ERROR,
                        validation_type=ValidationType.CDL_WORKING_SPACE_MISMATCH,
                        message=f"{desc} missing required fromCdlWorkingSpace",
                        file_path=context.amf_path,
                    )
                )

        return messages
