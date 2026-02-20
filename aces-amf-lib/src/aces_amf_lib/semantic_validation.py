# SPDX-License-Identifier: Apache-2.0
"""
Semantic validation for AMF files.

Provides validation beyond XSD schema compliance, including date logic,
UUID uniqueness, CDL values, applied order, metadata completeness,
file path security, and URN format validation.

This trimmed version does NOT include:
- Transform ID registry lookups (no network fetching)
- File reference existence checks
- File hash validation
- LUT content validation (no OCIO dependency)
- CCC collection parsing
"""

import logging
import re
from datetime import datetime
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from .aces_amf import ACESAMF

logger = logging.getLogger(__name__)


def _normalize_file_list(file_field) -> list[str]:
    """
    Convert file field to list, handling None, string, or list.

    Args:
        file_field: File field which may be None, a string, or a list

    Returns:
        List of file references (empty list if None)
    """
    if not file_field:
        return []
    return file_field if isinstance(file_field, list) else [file_field]


# CDL validation constants
CDL_SLOPE_MAX = 5.0
CDL_OFFSET_MIN = -5.0
CDL_OFFSET_MAX = 5.0
CDL_POWER_MAX = 5.0
CDL_SATURATION_MIN = 0.0
CDL_SATURATION_MAX = 2.0
CDL_IDENTITY_TOLERANCE = 1e-6

# ACES transform ID URN pattern (format validation only, not registry lookup)
ACES_TRANSFORM_ID_PATTERN = re.compile(
    r"^urn:ampas:aces:transformId:v[12]\.\d+:"
    r"[A-Za-z][A-Za-z0-9]*"       # Transform type (e.g., IDT, ODT, LMT, ACEScsc, ...)
    r"\.\S+"                        # Rest of the ID
    r"$"
)


class ValidationLevel(Enum):
    """Validation strictness levels."""

    ERROR = "error"  # Blocking issues
    WARNING = "warning"  # Non-blocking issues
    INFO = "info"  # Informational messages


class SemanticValidationType(Enum):
    """Types of semantic validations."""

    # Parse errors
    LOAD_ERROR = auto()

    # Temporal Logic
    INVALID_DATE_LOGIC = auto()
    FUTURE_TIMESTAMP = auto()

    # Identity
    DUPLICATE_UUID = auto()

    # CDL Validation
    CDL_IDENTITY = auto()
    CDL_INVALID_VALUES = auto()
    CDL_EXTREME_VALUES = auto()

    # Working Space
    MISSING_TO_CDL_WORKING_SPACE = auto()
    CDL_WORKING_SPACE_MISMATCH = auto()

    # Transform IDs (format only, no registry)
    INVALID_TRANSFORM_ID = auto()

    # Transform Application Order
    INVALID_APPLIED_ORDER = auto()

    # Metadata
    MISSING_DESCRIPTION = auto()
    MISSING_AUTHOR = auto()
    MISSING_TRANSFORM_DESCRIPTION = auto()

    # File Paths
    UNSAFE_FILE_PATH = auto()
    NON_PORTABLE_PATH = auto()


@dataclass
class SemanticValidationMessage:
    """A validation message with level and type."""

    level: ValidationLevel
    validation_type: SemanticValidationType
    message: str
    file_path: Optional[Path] = None

    def __str__(self) -> str:
        level_str = f"[{self.level.value.upper()}]"
        if self.file_path:
            return f"{level_str} {self.file_path}: {self.message}"
        return f"{level_str} {self.message}"


class SemanticValidator:
    """Performs semantic validation on AMF files."""

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize validator.

        Args:
            base_path: Base directory for resolving relative file paths
        """
        self.base_path = base_path

    def validate(
        self,
        amf_path: Path,
        check_dates: bool = True,
        check_uuids: bool = True,
        check_cdl: bool = True,
        check_working_space: bool = True,
        check_transform_ids: bool = True,
        check_applied_order: bool = True,
        check_metadata: bool = True,
        check_file_paths: bool = True,
        uuid_pool: Optional[set[str]] = None,
    ) -> list[SemanticValidationMessage]:
        """
        Perform semantic validation on an AMF file.

        Args:
            amf_path: Path to AMF file
            check_dates: Validate date logic
            check_uuids: Validate UUID uniqueness
            check_cdl: Validate CDL values
            check_working_space: Validate CDL working spaces
            check_transform_ids: Validate transform ID URN format
            check_applied_order: Validate look transform applied order is correct
            check_metadata: Check metadata completeness
            check_file_paths: Check file path security/portability
            uuid_pool: Set of UUIDs seen across multiple files (for recursive validation)

        Returns:
            List of validation messages
        """
        messages: list[SemanticValidationMessage] = []

        try:
            amf = ACESAMF.from_file(amf_path)
        except Exception as e:
            messages.append(
                SemanticValidationMessage(
                    level=ValidationLevel.ERROR,
                    validation_type=SemanticValidationType.LOAD_ERROR,
                    message=f"Failed to load AMF: {e}",
                    file_path=amf_path,
                )
            )
            return messages

        # Date logic validation
        if check_dates:
            messages.extend(self._validate_date_logic(amf, amf_path))

        # UUID validation
        if check_uuids:
            messages.extend(self._validate_uuids(amf, amf_path, uuid_pool))

        # CDL validation
        if check_cdl:
            messages.extend(self._validate_cdl(amf, amf_path))

        # Working space validation
        if check_working_space:
            messages.extend(self._validate_working_space(amf, amf_path))

        # Transform ID format validation
        if check_transform_ids:
            messages.extend(self._validate_transform_ids(amf, amf_path))

        # Applied order validation
        if check_applied_order:
            messages.extend(self._validate_applied_order(amf, amf_path))

        # Metadata completeness
        if check_metadata:
            messages.extend(self._validate_metadata(amf, amf_path))

        # File path security
        if check_file_paths:
            messages.extend(self._validate_file_paths(amf, amf_path))

        return messages

    def _validate_date_pair(
        self,
        creation_dt,
        modification_dt,
        context: str,
        amf_path: Path
    ) -> list[SemanticValidationMessage]:
        """
        Validate creation and modification date logic.
        """
        from datetime import timezone

        messages = []
        now = datetime.now(timezone.utc)

        try:
            # Convert to datetime if needed
            creation = creation_dt.to_datetime() if hasattr(creation_dt, "to_datetime") else creation_dt
            modification = modification_dt.to_datetime() if hasattr(modification_dt, "to_datetime") else modification_dt

            # Make timezone-aware if needed
            if creation and creation.tzinfo is None:
                creation = creation.replace(tzinfo=timezone.utc)
            if modification and modification.tzinfo is None:
                modification = modification.replace(tzinfo=timezone.utc)

            # Check creation <= modification
            if creation and modification and creation > modification:
                messages.append(
                    SemanticValidationMessage(
                        level=ValidationLevel.ERROR,
                        validation_type=SemanticValidationType.INVALID_DATE_LOGIC,
                        message=f"{context} creation date ({creation}) is after modification date ({modification})",
                        file_path=amf_path,
                    )
                )

            # Check modification not in future
            if modification and modification > now:
                messages.append(
                    SemanticValidationMessage(
                        level=ValidationLevel.WARNING,
                        validation_type=SemanticValidationType.FUTURE_TIMESTAMP,
                        message=f"{context} modification date ({modification}) is in the future",
                        file_path=amf_path,
                    )
                )
        except (ValueError, AttributeError) as e:
            logger.debug(f"Could not parse {context} dates: {e}")

        return messages

    def _validate_date_logic(self, amf: ACESAMF, amf_path: Path) -> list[SemanticValidationMessage]:
        """Validate date logic consistency."""
        messages = []

        # AMF info dates
        if amf.amf.amf_info and amf.amf.amf_info.date_time:
            dt = amf.amf.amf_info.date_time
            messages.extend(
                self._validate_date_pair(
                    dt.creation_date_time,
                    dt.modification_date_time,
                    "AMF",
                    amf_path
                )
            )

        # Pipeline info dates
        if amf.amf.pipeline and amf.amf.pipeline.pipeline_info and amf.amf.pipeline.pipeline_info.date_time:
            dt = amf.amf.pipeline.pipeline_info.date_time
            messages.extend(
                self._validate_date_pair(
                    dt.creation_date_time,
                    dt.modification_date_time,
                    "Pipeline",
                    amf_path
                )
            )

        return messages

    def _validate_uuids(self, amf: ACESAMF, amf_path: Path, uuid_pool: Optional[set[str]] = None) -> list[SemanticValidationMessage]:
        """Validate UUID uniqueness."""
        messages = []
        local_uuids = set()

        # Collect UUIDs
        if amf.amf.amf_info and amf.amf.amf_info.uuid:
            local_uuids.add(amf.amf.amf_info.uuid)

        if amf.amf.pipeline and amf.amf.pipeline.pipeline_info and amf.amf.pipeline.pipeline_info.uuid:
            local_uuids.add(amf.amf.pipeline.pipeline_info.uuid)

        if amf.amf.pipeline and amf.amf.pipeline.look_transform:
            for lt in amf.amf.pipeline.look_transform:
                if lt.uuid:
                    local_uuids.add(lt.uuid)

        # Check for duplicates within this file
        expected_count = sum(
            [
                1 if amf.amf.amf_info and amf.amf.amf_info.uuid else 0,
                1 if amf.amf.pipeline and amf.amf.pipeline.pipeline_info and amf.amf.pipeline.pipeline_info.uuid else 0,
                sum(1 for lt in (amf.amf.pipeline.look_transform or []) if lt.uuid),
            ]
        )

        if len(local_uuids) != expected_count:
            messages.append(
                SemanticValidationMessage(
                    level=ValidationLevel.ERROR,
                    validation_type=SemanticValidationType.DUPLICATE_UUID,
                    message="Duplicate UUIDs found within AMF file",
                    file_path=amf_path,
                )
            )

        # Check against UUID pool (for recursive validation)
        if uuid_pool is not None:
            for uuid in local_uuids:
                if uuid in uuid_pool:
                    messages.append(
                        SemanticValidationMessage(
                            level=ValidationLevel.ERROR,
                            validation_type=SemanticValidationType.DUPLICATE_UUID,
                            message=f"UUID {uuid} appears in multiple AMF files",
                            file_path=amf_path,
                        )
                    )
                uuid_pool.add(uuid)

        return messages

    def _is_cdl_identity(self, look_transform) -> bool:
        """Check if a CDL is identity (no effect)."""
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

    def _check_cdl_sop_value(
        self,
        value: float,
        value_type: str,
        index: int,
        transform_desc: str,
        amf_path: Path
    ) -> list[SemanticValidationMessage]:
        """Check a single CDL SOP value (slope/offset/power)."""
        messages = []

        if value_type == "slope":
            if value <= 0:
                messages.append(
                    SemanticValidationMessage(
                        level=ValidationLevel.ERROR,
                        validation_type=SemanticValidationType.CDL_INVALID_VALUES,
                        message=f"{transform_desc} has invalid slope[{index}] = {value} (must be > 0)",
                        file_path=amf_path,
                    )
                )
            elif value > CDL_SLOPE_MAX:
                messages.append(
                    SemanticValidationMessage(
                        level=ValidationLevel.WARNING,
                        validation_type=SemanticValidationType.CDL_EXTREME_VALUES,
                        message=f"{transform_desc} has extreme slope[{index}] = {value} "
                               f"(recommended: 0-{CDL_SLOPE_MAX})",
                        file_path=amf_path,
                    )
                )

        elif value_type == "offset":
            if value < CDL_OFFSET_MIN or value > CDL_OFFSET_MAX:
                messages.append(
                    SemanticValidationMessage(
                        level=ValidationLevel.WARNING,
                        validation_type=SemanticValidationType.CDL_EXTREME_VALUES,
                        message=f"{transform_desc} has extreme offset[{index}] = {value} "
                               f"(recommended: {CDL_OFFSET_MIN} to {CDL_OFFSET_MAX})",
                        file_path=amf_path,
                    )
                )

        elif value_type == "power":
            if value <= 0:
                messages.append(
                    SemanticValidationMessage(
                        level=ValidationLevel.ERROR,
                        validation_type=SemanticValidationType.CDL_INVALID_VALUES,
                        message=f"{transform_desc} has invalid power[{index}] = {value} (must be > 0)",
                        file_path=amf_path,
                    )
                )
            elif value > CDL_POWER_MAX:
                messages.append(
                    SemanticValidationMessage(
                        level=ValidationLevel.WARNING,
                        validation_type=SemanticValidationType.CDL_EXTREME_VALUES,
                        message=f"{transform_desc} has extreme power[{index}] = {value} "
                               f"(recommended: 0-{CDL_POWER_MAX})",
                        file_path=amf_path,
                    )
                )

        return messages

    def _validate_cdl(self, amf: ACESAMF, amf_path: Path) -> list[SemanticValidationMessage]:
        """Validate CDL values."""
        messages = []

        if not amf.amf.pipeline or not amf.amf.pipeline.look_transform:
            return messages

        for idx, lt in enumerate(amf.amf.pipeline.look_transform):
            desc = lt.description or f"Look transform #{idx + 1}"

            # Check if CDL exists
            if not lt.asc_sop and not lt.asc_sat:
                continue

            # Check for identity CDL
            if self._is_cdl_identity(lt):
                messages.append(
                    SemanticValidationMessage(
                        level=ValidationLevel.INFO,
                        validation_type=SemanticValidationType.CDL_IDENTITY,
                        message=f"{desc} has identity CDL (no effect)",
                        file_path=amf_path,
                    )
                )

            # Validate SOP values
            if lt.asc_sop:
                slope = lt.asc_sop.slope
                offset = lt.asc_sop.offset
                power = lt.asc_sop.power

                # Check format
                if slope and len(slope) != 3:
                    messages.append(
                        SemanticValidationMessage(
                            level=ValidationLevel.ERROR,
                            validation_type=SemanticValidationType.CDL_INVALID_VALUES,
                            message=f"{desc} has invalid slope format (expected 3 values, got {len(slope)})",
                            file_path=amf_path,
                        )
                    )
                if offset and len(offset) != 3:
                    messages.append(
                        SemanticValidationMessage(
                            level=ValidationLevel.ERROR,
                            validation_type=SemanticValidationType.CDL_INVALID_VALUES,
                            message=f"{desc} has invalid offset format (expected 3 values, got {len(offset)})",
                            file_path=amf_path,
                        )
                    )
                if power and len(power) != 3:
                    messages.append(
                        SemanticValidationMessage(
                            level=ValidationLevel.ERROR,
                            validation_type=SemanticValidationType.CDL_INVALID_VALUES,
                            message=f"{desc} has invalid power format (expected 3 values, got {len(power)})",
                            file_path=amf_path,
                        )
                    )

                # Check value ranges using helper
                if slope:
                    for i, s in enumerate(slope):
                        messages.extend(self._check_cdl_sop_value(s, "slope", i, desc, amf_path))

                if offset:
                    for i, o in enumerate(offset):
                        messages.extend(self._check_cdl_sop_value(o, "offset", i, desc, amf_path))

                if power:
                    for i, p in enumerate(power):
                        messages.extend(self._check_cdl_sop_value(p, "power", i, desc, amf_path))

            # Validate saturation
            if lt.asc_sat and lt.asc_sat.saturation is not None:
                sat = lt.asc_sat.saturation
                if sat <= CDL_SATURATION_MIN:
                    messages.append(
                        SemanticValidationMessage(
                            level=ValidationLevel.ERROR,
                            validation_type=SemanticValidationType.CDL_INVALID_VALUES,
                            message=f"{desc} has invalid saturation = {sat} (must be > {CDL_SATURATION_MIN})",
                            file_path=amf_path,
                        )
                    )
                elif sat > CDL_SATURATION_MAX:
                    messages.append(
                        SemanticValidationMessage(
                            level=ValidationLevel.WARNING,
                            validation_type=SemanticValidationType.CDL_EXTREME_VALUES,
                            message=f"{desc} has extreme saturation = {sat} (recommended: {CDL_SATURATION_MIN}-{CDL_SATURATION_MAX})",
                            file_path=amf_path,
                        )
                    )

        return messages

    def _validate_working_space(self, amf: ACESAMF, amf_path: Path) -> list[SemanticValidationMessage]:
        """Validate CDL working space consistency."""
        messages = []

        if not amf.amf.pipeline or not amf.amf.pipeline.look_transform:
            return messages

        for idx, lt in enumerate(amf.amf.pipeline.look_transform):
            # Only check if CDL exists
            if not lt.asc_sop and not lt.asc_sat:
                continue

            desc = lt.description or f"Look transform #{idx + 1}"

            if not lt.cdl_working_space:
                messages.append(
                    SemanticValidationMessage(
                        level=ValidationLevel.WARNING,
                        validation_type=SemanticValidationType.MISSING_TO_CDL_WORKING_SPACE,
                        message=f"{desc} has CDL but no working space specified",
                        file_path=amf_path,
                    )
                )
                continue

            # Check fromCdlWorkingSpace is present (required)
            if not lt.cdl_working_space.from_cdl_working_space:
                messages.append(
                    SemanticValidationMessage(
                        level=ValidationLevel.ERROR,
                        validation_type=SemanticValidationType.CDL_WORKING_SPACE_MISMATCH,
                        message=f"{desc} missing required fromCdlWorkingSpace",
                        file_path=amf_path,
                    )
                )

            # Note: inverse check dropped — would require transforms registry

        return messages

    def _validate_transform_ids(self, amf: ACESAMF, amf_path: Path) -> list[SemanticValidationMessage]:
        """Validate transform ID URN format (not registry lookup)."""
        messages = []

        def _check_id(transform_id: str, context: str):
            if not ACES_TRANSFORM_ID_PATTERN.match(transform_id):
                messages.append(
                    SemanticValidationMessage(
                        level=ValidationLevel.WARNING,
                        validation_type=SemanticValidationType.INVALID_TRANSFORM_ID,
                        message=f"{context} has malformed transform ID: {transform_id}",
                        file_path=amf_path,
                    )
                )

        # Check input transform
        if amf.amf.pipeline and amf.amf.pipeline.input_transform and amf.amf.pipeline.input_transform.transform_id:
            _check_id(amf.amf.pipeline.input_transform.transform_id, "Input transform")

        # Check look transforms
        if amf.amf.pipeline and amf.amf.pipeline.look_transform:
            for idx, lt in enumerate(amf.amf.pipeline.look_transform):
                if lt.transform_id:
                    desc = lt.description or f"Look transform #{idx + 1}"
                    _check_id(lt.transform_id, desc)

        # Check output transform
        if amf.amf.pipeline and amf.amf.pipeline.output_transform and amf.amf.pipeline.output_transform.transform_id:
            _check_id(amf.amf.pipeline.output_transform.transform_id, "Output transform")

        # Check working space transforms
        if amf.amf.pipeline and amf.amf.pipeline.look_transform:
            for idx, lt in enumerate(amf.amf.pipeline.look_transform):
                if lt.cdl_working_space:
                    if lt.cdl_working_space.from_cdl_working_space and lt.cdl_working_space.from_cdl_working_space.transform_id:
                        _check_id(lt.cdl_working_space.from_cdl_working_space.transform_id, f"Look #{idx+1} fromCdlWorkingSpace")
                    if lt.cdl_working_space.to_cdl_working_space and lt.cdl_working_space.to_cdl_working_space.transform_id:
                        _check_id(lt.cdl_working_space.to_cdl_working_space.transform_id, f"Look #{idx+1} toCdlWorkingSpace")

        return messages

    def _validate_applied_order(self, amf: ACESAMF, amf_path: Path) -> list[SemanticValidationMessage]:
        """Validate that look transforms have correct applied order.

        Once a look transform has applied=False, all subsequent transforms must also be applied=False.
        Valid: [True, True, False, False] or [True, True, True] or [False, False]
        Invalid: [False, True] or [True, False, True]
        """
        messages = []

        if not amf.amf.pipeline or not amf.amf.pipeline.look_transform:
            return messages

        # Track if we've seen a non-applied transform
        seen_non_applied = False

        for idx, lt in enumerate(amf.amf.pipeline.look_transform):
            desc = lt.description or f"Look transform #{idx + 1}"
            is_applied = lt.applied if lt.applied is not None else True  # Default is True

            # If we've seen a non-applied transform and this one is applied, that's an error
            if seen_non_applied and is_applied:
                messages.append(
                    SemanticValidationMessage(
                        level=ValidationLevel.ERROR,
                        validation_type=SemanticValidationType.INVALID_APPLIED_ORDER,
                        message=f"{desc} has applied=True but appears after a non-applied transform. "
                        f"Once applied=False, all subsequent transforms must be applied=False.",
                        file_path=amf_path,
                    )
                )

            # Track if this is non-applied
            if not is_applied:
                seen_non_applied = True

        return messages

    def _validate_metadata(self, amf: ACESAMF, amf_path: Path) -> list[SemanticValidationMessage]:
        """Validate metadata completeness."""
        messages = []

        # Check AMF description
        if not amf.amf_description or not amf.amf_description.strip():
            messages.append(
                SemanticValidationMessage(
                    level=ValidationLevel.WARNING,
                    validation_type=SemanticValidationType.MISSING_DESCRIPTION,
                    message="AMF description is missing or empty",
                    file_path=amf_path,
                )
            )

        # Check for at least one author
        if not amf.amf_authors:
            messages.append(
                SemanticValidationMessage(
                    level=ValidationLevel.WARNING,
                    validation_type=SemanticValidationType.MISSING_AUTHOR,
                    message="No authors specified",
                    file_path=amf_path,
                )
            )

        # Check pipeline description
        if not amf.pipeline_description or not amf.pipeline_description.strip():
            messages.append(
                SemanticValidationMessage(
                    level=ValidationLevel.WARNING,
                    validation_type=SemanticValidationType.MISSING_DESCRIPTION,
                    message="Pipeline description is missing or empty",
                    file_path=amf_path,
                )
            )

        # Check look transform descriptions
        if amf.amf.pipeline and amf.amf.pipeline.look_transform:
            for idx, lt in enumerate(amf.amf.pipeline.look_transform):
                if not lt.description or not lt.description.strip():
                    messages.append(
                        SemanticValidationMessage(
                            level=ValidationLevel.INFO,
                            validation_type=SemanticValidationType.MISSING_TRANSFORM_DESCRIPTION,
                            message=f"Look transform #{idx + 1} has no description",
                            file_path=amf_path,
                        )
                    )

        return messages

    def _check_file_path_security(
        self,
        file_ref: str,
        context: str,
        amf_path: Path
    ) -> list[SemanticValidationMessage]:
        """Check file path for security and portability issues."""
        messages = []

        # Check for parent directory references
        if ".." in file_ref:
            messages.append(
                SemanticValidationMessage(
                    level=ValidationLevel.WARNING,
                    validation_type=SemanticValidationType.UNSAFE_FILE_PATH,
                    message=f"{context} contains parent directory reference (..): {file_ref}",
                    file_path=amf_path,
                )
            )

        # Check for absolute paths
        if file_ref.startswith("/") or (len(file_ref) > 1 and file_ref[1] == ":"):
            messages.append(
                SemanticValidationMessage(
                    level=ValidationLevel.WARNING,
                    validation_type=SemanticValidationType.NON_PORTABLE_PATH,
                    message=f"{context} uses absolute path (not portable): {file_ref}",
                    file_path=amf_path,
                )
            )

        # Check for backslashes (Windows paths)
        if "\\" in file_ref:
            messages.append(
                SemanticValidationMessage(
                    level=ValidationLevel.WARNING,
                    validation_type=SemanticValidationType.NON_PORTABLE_PATH,
                    message=f"{context} uses backslashes (not portable): {file_ref}",
                    file_path=amf_path,
                )
            )

        return messages

    def _validate_file_paths(self, amf: ACESAMF, amf_path: Path) -> list[SemanticValidationMessage]:
        """Validate file path security and portability."""
        messages = []

        # Check input transform
        if amf.amf.pipeline and amf.amf.pipeline.input_transform:
            it = amf.amf.pipeline.input_transform
            for file_ref in _normalize_file_list(getattr(it, 'file', None)):
                if file_ref:
                    messages.extend(self._check_file_path_security(unquote(file_ref), "Input transform", amf_path))

        # Check look transforms
        if amf.amf.pipeline and amf.amf.pipeline.look_transform:
            for idx, lt in enumerate(amf.amf.pipeline.look_transform):
                desc = lt.description or f"Look transform #{idx + 1}"
                for file_ref in _normalize_file_list(lt.file):
                    if file_ref:
                        messages.extend(self._check_file_path_security(unquote(file_ref), desc, amf_path))

        # Check output transform
        if amf.amf.pipeline and amf.amf.pipeline.output_transform:
            ot = amf.amf.pipeline.output_transform
            for file_ref in _normalize_file_list(getattr(ot, 'file', None)):
                if file_ref:
                    messages.extend(self._check_file_path_security(unquote(file_ref), "Output transform", amf_path))

        return messages


def validate_semantic(amf_path: Path, base_path: Optional[Path] = None, **kwargs) -> list[SemanticValidationMessage]:
    """
    Perform semantic validation on an AMF file (convenience function).

    Args:
        amf_path: Path to AMF file
        base_path: Base directory for resolving relative file paths
        **kwargs: Additional arguments passed to SemanticValidator.validate()

    Returns:
        List of validation messages
    """
    validator = SemanticValidator(base_path=base_path)
    return validator.validate(amf_path, **kwargs)
