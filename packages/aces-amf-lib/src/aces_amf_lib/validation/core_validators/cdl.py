# SPDX-License-Identifier: Apache-2.0
"""CDL value validation: range checks, identity detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..types import ValidationContext, ValidationLevel, ValidationMessage, ValidationType

if TYPE_CHECKING:
    from ...aces_amf import ACESAMF

# CDL validation constants
CDL_SLOPE_MAX = 5.0
CDL_OFFSET_MIN = -5.0
CDL_OFFSET_MAX = 5.0
CDL_POWER_MAX = 5.0
CDL_SATURATION_MIN = 0.0
CDL_SATURATION_MAX = 2.0
CDL_IDENTITY_TOLERANCE = 1e-6


class CDLValidator:
    name = "cdl"

    def validate(self, amf: ACESAMF, context: ValidationContext) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []

        if not amf.amf.pipeline or not amf.amf.pipeline.look_transform:
            return messages

        for idx, lt in enumerate(amf.amf.pipeline.look_transform):
            desc = lt.description or f"Look transform #{idx + 1}"

            if not lt.asc_sop and not lt.asc_sat:
                continue

            # Identity check
            if _is_cdl_identity(lt):
                messages.append(
                    ValidationMessage(
                        level=ValidationLevel.INFO,
                        validation_type=ValidationType.CDL_IDENTITY,
                        message=f"{desc} has identity CDL (no effect)",
                        file_path=context.amf_path,
                    )
                )

            # Validate SOP values
            if lt.asc_sop:
                slope = lt.asc_sop.slope
                offset = lt.asc_sop.offset
                power = lt.asc_sop.power

                for label, values in [("slope", slope), ("offset", offset), ("power", power)]:
                    if values and len(values) != 3:
                        messages.append(
                            ValidationMessage(
                                level=ValidationLevel.ERROR,
                                validation_type=ValidationType.CDL_INVALID_VALUES,
                                message=f"{desc} has invalid {label} format (expected 3 values, got {len(values)})",
                                file_path=context.amf_path,
                            )
                        )

                if slope:
                    for i, s in enumerate(slope):
                        messages.extend(_check_sop_value(s, "slope", i, desc, context.amf_path))
                if offset:
                    for i, o in enumerate(offset):
                        messages.extend(_check_sop_value(o, "offset", i, desc, context.amf_path))
                if power:
                    for i, p in enumerate(power):
                        messages.extend(_check_sop_value(p, "power", i, desc, context.amf_path))

            # Validate saturation
            if lt.asc_sat and lt.asc_sat.saturation is not None:
                sat = lt.asc_sat.saturation
                if sat <= CDL_SATURATION_MIN:
                    messages.append(
                        ValidationMessage(
                            level=ValidationLevel.ERROR,
                            validation_type=ValidationType.CDL_INVALID_VALUES,
                            message=f"{desc} has invalid saturation = {sat} (must be > {CDL_SATURATION_MIN})",
                            file_path=context.amf_path,
                        )
                    )
                elif sat > CDL_SATURATION_MAX:
                    messages.append(
                        ValidationMessage(
                            level=ValidationLevel.WARNING,
                            validation_type=ValidationType.CDL_EXTREME_VALUES,
                            message=f"{desc} has extreme saturation = {sat} (recommended: {CDL_SATURATION_MIN}-{CDL_SATURATION_MAX})",
                            file_path=context.amf_path,
                        )
                    )

        return messages


def _is_cdl_identity(look_transform) -> bool:
    if not look_transform.asc_sop or not look_transform.asc_sat:
        return False

    slope = look_transform.asc_sop.slope or [1.0, 1.0, 1.0]
    offset = look_transform.asc_sop.offset or [0.0, 0.0, 0.0]
    power = look_transform.asc_sop.power or [1.0, 1.0, 1.0]
    sat = look_transform.asc_sat.saturation if look_transform.asc_sat.saturation is not None else 1.0

    return (
        all(abs(s - 1.0) < CDL_IDENTITY_TOLERANCE for s in slope)
        and all(abs(o) < CDL_IDENTITY_TOLERANCE for o in offset)
        and all(abs(p - 1.0) < CDL_IDENTITY_TOLERANCE for p in power)
        and abs(sat - 1.0) < CDL_IDENTITY_TOLERANCE
    )


def _check_sop_value(value: float, value_type: str, index: int, desc: str, amf_path) -> list[ValidationMessage]:
    messages = []

    if value_type == "slope":
        if value <= 0:
            messages.append(
                ValidationMessage(
                    level=ValidationLevel.ERROR,
                    validation_type=ValidationType.CDL_INVALID_VALUES,
                    message=f"{desc} has invalid slope[{index}] = {value} (must be > 0)",
                    file_path=amf_path,
                )
            )
        elif value > CDL_SLOPE_MAX:
            messages.append(
                ValidationMessage(
                    level=ValidationLevel.WARNING,
                    validation_type=ValidationType.CDL_EXTREME_VALUES,
                    message=f"{desc} has extreme slope[{index}] = {value} (recommended: 0-{CDL_SLOPE_MAX})",
                    file_path=amf_path,
                )
            )

    elif value_type == "offset":
        if value < CDL_OFFSET_MIN or value > CDL_OFFSET_MAX:
            messages.append(
                ValidationMessage(
                    level=ValidationLevel.WARNING,
                    validation_type=ValidationType.CDL_EXTREME_VALUES,
                    message=f"{desc} has extreme offset[{index}] = {value} (recommended: {CDL_OFFSET_MIN} to {CDL_OFFSET_MAX})",
                    file_path=amf_path,
                )
            )

    elif value_type == "power":
        if value <= 0:
            messages.append(
                ValidationMessage(
                    level=ValidationLevel.ERROR,
                    validation_type=ValidationType.CDL_INVALID_VALUES,
                    message=f"{desc} has invalid power[{index}] = {value} (must be > 0)",
                    file_path=amf_path,
                )
            )
        elif value > CDL_POWER_MAX:
            messages.append(
                ValidationMessage(
                    level=ValidationLevel.WARNING,
                    validation_type=ValidationType.CDL_EXTREME_VALUES,
                    message=f"{desc} has extreme power[{index}] = {value} (recommended: 0-{CDL_POWER_MAX})",
                    file_path=amf_path,
                )
            )

    return messages
