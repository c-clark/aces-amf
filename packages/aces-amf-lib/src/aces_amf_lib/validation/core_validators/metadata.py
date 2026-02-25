# SPDX-License-Identifier: Apache-2.0
"""Metadata completeness validation: descriptions, authors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..types import ValidationContext, ValidationLevel, ValidationMessage, ValidationType

if TYPE_CHECKING:
    from ...aces_amf import ACESAMF


class MetadataValidator:
    name = "metadata"

    def validate(self, amf: ACESAMF, context: ValidationContext) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []

        # Check AMF description
        if not amf.amf_description or not amf.amf_description.strip():
            messages.append(
                ValidationMessage(
                    level=ValidationLevel.WARNING,
                    validation_type=ValidationType.MISSING_DESCRIPTION,
                    message="AMF description is missing or empty",
                    file_path=context.amf_path,
                )
            )

        # Check for at least one author
        if not amf.amf_authors:
            messages.append(
                ValidationMessage(
                    level=ValidationLevel.WARNING,
                    validation_type=ValidationType.MISSING_AUTHOR,
                    message="No authors specified",
                    file_path=context.amf_path,
                )
            )

        # Check pipeline description
        if not amf.pipeline_description or not amf.pipeline_description.strip():
            messages.append(
                ValidationMessage(
                    level=ValidationLevel.WARNING,
                    validation_type=ValidationType.MISSING_DESCRIPTION,
                    message="Pipeline description is missing or empty",
                    file_path=context.amf_path,
                )
            )

        # Check look transform descriptions
        if amf.amf.pipeline and amf.amf.pipeline.look_transform:
            for idx, lt in enumerate(amf.amf.pipeline.look_transform):
                if not lt.description or not lt.description.strip():
                    messages.append(
                        ValidationMessage(
                            level=ValidationLevel.INFO,
                            validation_type=ValidationType.MISSING_TRANSFORM_DESCRIPTION,
                            message=f"Look transform #{idx + 1} has no description",
                            file_path=context.amf_path,
                        )
                    )

        return messages
