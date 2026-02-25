# SPDX-License-Identifier: Apache-2.0
"""Transform applied order validation.

Once a look transform has applied=False, all subsequent transforms
must also be applied=False.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..types import ValidationContext, ValidationLevel, ValidationMessage, ValidationType

if TYPE_CHECKING:
    from ...aces_amf import ACESAMF


class AppliedOrderValidator:
    name = "applied_order"

    def validate(self, amf: ACESAMF, context: ValidationContext) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []

        if not amf.amf.pipeline or not amf.amf.pipeline.look_transform:
            return messages

        seen_non_applied = False

        for idx, lt in enumerate(amf.amf.pipeline.look_transform):
            desc = lt.description or f"Look transform #{idx + 1}"
            is_applied = lt.applied if lt.applied is not None else True

            if seen_non_applied and is_applied:
                messages.append(
                    ValidationMessage(
                        level=ValidationLevel.ERROR,
                        validation_type=ValidationType.INVALID_APPLIED_ORDER,
                        message=f"{desc} has applied=True but appears after a non-applied transform. "
                        f"Once applied=False, all subsequent transforms must be applied=False.",
                        file_path=context.amf_path,
                    )
                )

            if not is_applied:
                seen_non_applied = True

        return messages
