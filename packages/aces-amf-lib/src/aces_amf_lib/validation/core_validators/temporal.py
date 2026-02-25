# SPDX-License-Identifier: Apache-2.0
"""Date/time validation: creation <= modification, no future timestamps."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from ..types import ValidationContext, ValidationLevel, ValidationMessage, ValidationType

if TYPE_CHECKING:
    from ...aces_amf import ACESAMF

logger = logging.getLogger(__name__)


class TemporalValidator:
    name = "temporal"

    def validate(self, amf: ACESAMF, context: ValidationContext) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []

        # AMF info dates
        if amf.amf.amf_info and amf.amf.amf_info.date_time:
            dt = amf.amf.amf_info.date_time
            messages.extend(
                _validate_date_pair(dt.creation_date_time, dt.modification_date_time, "AMF", context.amf_path)
            )

        # Pipeline info dates
        if amf.amf.pipeline and amf.amf.pipeline.pipeline_info and amf.amf.pipeline.pipeline_info.date_time:
            dt = amf.amf.pipeline.pipeline_info.date_time
            messages.extend(
                _validate_date_pair(dt.creation_date_time, dt.modification_date_time, "Pipeline", context.amf_path)
            )

        return messages


def _validate_date_pair(creation_dt, modification_dt, label: str, amf_path) -> list[ValidationMessage]:
    messages = []
    now = datetime.now(timezone.utc)

    try:
        creation = creation_dt.to_datetime() if hasattr(creation_dt, "to_datetime") else creation_dt
        modification = modification_dt.to_datetime() if hasattr(modification_dt, "to_datetime") else modification_dt

        if creation and creation.tzinfo is None:
            creation = creation.replace(tzinfo=timezone.utc)
        if modification and modification.tzinfo is None:
            modification = modification.replace(tzinfo=timezone.utc)

        if creation and modification and creation > modification:
            messages.append(
                ValidationMessage(
                    level=ValidationLevel.ERROR,
                    validation_type=ValidationType.INVALID_DATE_LOGIC,
                    message=f"{label} creation date ({creation}) is after modification date ({modification})",
                    file_path=amf_path,
                )
            )

        if modification and modification > now:
            messages.append(
                ValidationMessage(
                    level=ValidationLevel.WARNING,
                    validation_type=ValidationType.FUTURE_TIMESTAMP,
                    message=f"{label} modification date ({modification}) is in the future",
                    file_path=amf_path,
                )
            )
    except (ValueError, AttributeError) as e:
        logger.debug("Could not parse %s dates: %s", label, e)

    return messages
