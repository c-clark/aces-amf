# SPDX-License-Identifier: Apache-2.0
"""File path security and portability validation."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import unquote

from ..types import ValidationContext, ValidationLevel, ValidationMessage, ValidationType

if TYPE_CHECKING:
    from ...aces_amf import ACESAMF


class FilePathValidator:
    name = "file_paths"

    def validate(self, amf: ACESAMF, context: ValidationContext) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []

        # Check input transform
        if amf.amf.pipeline and amf.amf.pipeline.input_transform:
            it = amf.amf.pipeline.input_transform
            for file_ref in _normalize_file_list(getattr(it, "file", None)):
                if file_ref:
                    messages.extend(_check_path_security(unquote(file_ref), "Input transform", context.amf_path))

        # Check look transforms
        if amf.amf.pipeline and amf.amf.pipeline.look_transform:
            for idx, lt in enumerate(amf.amf.pipeline.look_transform):
                desc = lt.description or f"Look transform #{idx + 1}"
                for file_ref in _normalize_file_list(lt.file):
                    if file_ref:
                        messages.extend(_check_path_security(unquote(file_ref), desc, context.amf_path))

        # Check output transform
        if amf.amf.pipeline and amf.amf.pipeline.output_transform:
            ot = amf.amf.pipeline.output_transform
            for file_ref in _normalize_file_list(getattr(ot, "file", None)):
                if file_ref:
                    messages.extend(_check_path_security(unquote(file_ref), "Output transform", context.amf_path))

        return messages


def _normalize_file_list(file_field) -> list[str]:
    """Convert file field to list, handling None, string, or list."""
    if not file_field:
        return []
    return file_field if isinstance(file_field, list) else [file_field]


def _check_path_security(file_ref: str, label: str, amf_path) -> list[ValidationMessage]:
    messages = []

    if ".." in file_ref:
        messages.append(
            ValidationMessage(
                level=ValidationLevel.WARNING,
                validation_type=ValidationType.UNSAFE_FILE_PATH,
                message=f"{label} contains parent directory reference (..): {file_ref}",
                file_path=amf_path,
            )
        )

    if file_ref.startswith("/") or (len(file_ref) > 1 and file_ref[1] == ":"):
        messages.append(
            ValidationMessage(
                level=ValidationLevel.WARNING,
                validation_type=ValidationType.NON_PORTABLE_PATH,
                message=f"{label} uses absolute path (not portable): {file_ref}",
                file_path=amf_path,
            )
        )

    if "\\" in file_ref:
        messages.append(
            ValidationMessage(
                level=ValidationLevel.WARNING,
                validation_type=ValidationType.NON_PORTABLE_PATH,
                message=f"{label} uses backslashes (not portable): {file_ref}",
                file_path=amf_path,
            )
        )

    return messages
