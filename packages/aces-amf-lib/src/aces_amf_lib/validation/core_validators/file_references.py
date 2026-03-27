# SPDX-License-Identifier: Apache-2.0
"""
Deep file reference validation: existence, hash verification, CCC cross-refs.

Requires base_path in ValidationContext to resolve relative file paths.
Skips silently when base_path is None (e.g., when loading from bytes).
"""

from __future__ import annotations

import base64
import hashlib
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote

from ..types import ValidationContext, ValidationLevel, ValidationMessage, ValidationType
from ._nested import collect_sub_transforms

if TYPE_CHECKING:
    from ...amf_v2 import AcesMetadataFile, PipelineType

logger = logging.getLogger(__name__)

HASH_ALGORITHM_MAP = {
    "http://www.w3.org/2001/04/xmlenc#sha256": "sha256",
    "http://www.w3.org/2000/09/xmldsig#sha1": "sha1",
    "http://www.w3.org/2001/04/xmldsig-more#md5": "md5",
}

CDL_COLLECTION_EXTENSIONS = {".ccc", ".cdl"}


class FileReferenceValidator:
    """Validates file references, hashes, and CCC cross-references.

    Only runs when context.base_path is set (file-system access required).
    """

    name = "file_references"

    def validate(self, amf: AcesMetadataFile, context: ValidationContext) -> list[ValidationMessage]:
        if context.base_path is None:
            return []

        messages: list[ValidationMessage] = []

        if amf.pipeline:
            self._validate_pipeline(amf.pipeline, "", messages, context)

        for idx, archived in enumerate(amf.archived_pipeline):
            self._validate_pipeline(archived, f"Archived pipeline #{idx + 1} ", messages, context)

        return messages

    def _validate_pipeline(
        self, pipeline: PipelineType, prefix: str, messages: list[ValidationMessage], context: ValidationContext
    ) -> None:
        base_path = context.base_path

        def _check_file_ref(transform, label: str) -> None:
            file_ref = getattr(transform, "file", None)
            if not file_ref:
                return

            # Resolve relative to base_path, URL-decode
            file_path = base_path / unquote(file_ref)

            # 1. File existence
            if not file_path.exists():
                messages.append(
                    ValidationMessage(
                        level=ValidationLevel.ERROR,
                        validation_type=ValidationType.MISSING_REFERENCED_FILE,
                        message=f"{label} references missing file: {file_ref}",
                        file_path=context.amf_path,
                    )
                )
                return  # Can't check hash or CCC if file doesn't exist

            # 2. Hash verification
            hash_obj = getattr(transform, "hash_value", None)
            if hash_obj is not None:
                _verify_hash(file_path, hash_obj, label, messages, context)

            # 3. CCC cross-reference
            ccc_ref = getattr(transform, "color_correction_ref", None)
            if ccc_ref is not None and getattr(ccc_ref, "ref", None):
                if file_path.suffix.lower() in CDL_COLLECTION_EXTENSIONS:
                    _verify_ccc_ref(file_path, ccc_ref.ref, label, messages, context)

        # Input transform
        if pipeline.input_transform:
            _check_file_ref(pipeline.input_transform, f"{prefix}Input transform")
            for sub_label, sub in collect_sub_transforms(pipeline.input_transform, f"{prefix}Input"):
                _check_file_ref(sub, sub_label)

        # Look transforms
        for idx, lt in enumerate(pipeline.look_transforms):
            desc = f"{prefix}{lt.description or f'Look transform #{idx + 1}'}"
            _check_file_ref(lt, desc)

        # Output transform
        if pipeline.output_transform:
            _check_file_ref(pipeline.output_transform, f"{prefix}Output transform")
            for sub_label, sub in collect_sub_transforms(pipeline.output_transform, f"{prefix}Output"):
                _check_file_ref(sub, sub_label)


def _verify_hash(
    file_path: Path, hash_obj, label: str, messages: list[ValidationMessage], context: ValidationContext
) -> None:
    """Verify the file hash matches the declared value."""
    algo_uri = getattr(hash_obj, "algorithm", None)
    if not algo_uri:
        return

    algo_name = HASH_ALGORITHM_MAP.get(algo_uri)
    if algo_name is None:
        logger.debug("Unknown hash algorithm: %s", algo_uri)
        return

    try:
        hasher = hashlib.new(algo_name)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        computed = hasher.digest()

        # hash_obj.value is the declared hash — may be base64-encoded bytes or raw bytes
        expected = hash_obj.value
        if isinstance(expected, str):
            expected = base64.b64decode(expected)

        if computed != expected:
            computed_b64 = base64.b64encode(computed).decode("ascii")
            expected_b64 = base64.b64encode(expected).decode("ascii") if isinstance(expected, bytes) else str(expected)
            messages.append(
                ValidationMessage(
                    level=ValidationLevel.ERROR,
                    validation_type=ValidationType.HASH_MISMATCH,
                    message=(
                        f"{label} hash mismatch for {file_path.name}: "
                        f"expected {expected_b64}, computed {computed_b64}"
                    ),
                    file_path=context.amf_path,
                )
            )
    except OSError as e:
        logger.debug("Could not read file for hash verification: %s", e)


def _verify_ccc_ref(
    ccc_path: Path, ref_id: str, label: str, messages: list[ValidationMessage], context: ValidationContext
) -> None:
    """Verify that a ColorCorrectionRef ID exists in the referenced CCC/CDL file."""
    try:
        tree = ET.parse(ccc_path)
        root = tree.getroot()

        # Extract ColorCorrection IDs (with and without namespace)
        ns = {"cdl": "urn:ASC:CDL:v1.01"}
        ids = set()
        for cc in root.findall(".//cdl:ColorCorrection", ns):
            cc_id = cc.get("id")
            if cc_id:
                ids.add(cc_id)
        # Fallback for files without namespace
        if not ids:
            for cc in root.findall(".//ColorCorrection"):
                cc_id = cc.get("id")
                if cc_id:
                    ids.add(cc_id)

        if ref_id not in ids:
            available = ", ".join(sorted(ids)[:5])
            messages.append(
                ValidationMessage(
                    level=ValidationLevel.ERROR,
                    validation_type=ValidationType.CCC_MISSING_ID,
                    message=(
                        f"{label} references ColorCorrection ID '{ref_id}' "
                        f"not found in {ccc_path.name}. "
                        f"Available IDs: [{available}]"
                        if ids else
                        f"{label} references ColorCorrection ID '{ref_id}' "
                        f"but {ccc_path.name} contains no ColorCorrection elements"
                    ),
                    file_path=context.amf_path,
                )
            )
    except ET.ParseError as e:
        messages.append(
            ValidationMessage(
                level=ValidationLevel.ERROR,
                validation_type=ValidationType.CCC_PARSE_ERROR,
                message=f"{label} could not parse CCC file {ccc_path.name}: {e}",
                file_path=context.amf_path,
            )
        )
