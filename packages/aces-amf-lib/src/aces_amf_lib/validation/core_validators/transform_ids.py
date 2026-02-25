# SPDX-License-Identifier: Apache-2.0
"""Transform ID URN format validation (no registry lookup)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ..types import ValidationContext, ValidationLevel, ValidationMessage, ValidationType

if TYPE_CHECKING:
    from ...aces_amf import ACESAMF

ACES_TRANSFORM_ID_PATTERN = re.compile(
    r"^urn:ampas:aces:transformId:v[12]\.\d+:"
    r"[A-Za-z][A-Za-z0-9]*"
    r"\.\S+"
    r"$"
)


class TransformIdFormatValidator:
    name = "transform_ids"

    def validate(self, amf: ACESAMF, context: ValidationContext) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []

        def _check_id(transform_id: str, label: str):
            if not ACES_TRANSFORM_ID_PATTERN.match(transform_id):
                messages.append(
                    ValidationMessage(
                        level=ValidationLevel.WARNING,
                        validation_type=ValidationType.INVALID_TRANSFORM_ID,
                        message=f"{label} has malformed transform ID: {transform_id}",
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
