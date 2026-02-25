# SPDX-License-Identifier: Apache-2.0
"""UUID uniqueness validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..types import ValidationContext, ValidationLevel, ValidationMessage, ValidationType

if TYPE_CHECKING:
    from ...aces_amf import ACESAMF


class UUIDValidator:
    name = "uuid"

    def validate(self, amf: ACESAMF, context: ValidationContext) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []
        local_uuids: set[str] = set()
        expected_count = 0

        # Collect UUIDs
        if amf.amf.amf_info and amf.amf.amf_info.uuid:
            local_uuids.add(amf.amf.amf_info.uuid)
            expected_count += 1

        if amf.amf.pipeline and amf.amf.pipeline.pipeline_info and amf.amf.pipeline.pipeline_info.uuid:
            local_uuids.add(amf.amf.pipeline.pipeline_info.uuid)
            expected_count += 1

        if amf.amf.pipeline and amf.amf.pipeline.look_transform:
            for lt in amf.amf.pipeline.look_transform:
                if lt.uuid:
                    expected_count += 1
                    local_uuids.add(lt.uuid)

        # Check for duplicates within this file
        if len(local_uuids) != expected_count:
            messages.append(
                ValidationMessage(
                    level=ValidationLevel.ERROR,
                    validation_type=ValidationType.DUPLICATE_UUID,
                    message="Duplicate UUIDs found within AMF file",
                    file_path=context.amf_path,
                )
            )

        # Check against cross-file UUID pool
        if context.uuid_pool is not None:
            for uid in local_uuids:
                if uid in context.uuid_pool:
                    messages.append(
                        ValidationMessage(
                            level=ValidationLevel.ERROR,
                            validation_type=ValidationType.DUPLICATE_UUID,
                            message=f"UUID {uid} appears in multiple AMF files",
                            file_path=context.amf_path,
                        )
                    )
                context.uuid_pool.add(uid)

        return messages
