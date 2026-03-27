# SPDX-License-Identifier: Apache-2.0
"""
Utilities for working with generated AMF classes.

Provides both low-level functions (dump_amf, write_amf, from_amf_file, from_amf_data)
and high-level convenience functions (load_amf, save_amf, render_amf, minimal_amf).
"""

import copy
import datetime
import uuid
from pathlib import Path
from typing import Callable, TextIO
from urllib.parse import quote, unquote
from pydantic import BaseModel
from xsdata.models.datatype import XmlDateTime
from xsdata_pydantic.bindings import XmlParser, XmlSerializer

from . import amf_v2


"""Minimal namespaces for AMF"""
AMF_NS_MAP = dict(
    aces="urn:ampas:aces:amf:v2.0",
    xsi="http://www.w3.org/2001/XMLSchema-instance",
)

"""Minimal namespaces for ASC CDL"""
CDL_NS_MAP = dict(
    cdl="urn:ASC:CDL:v1.01",
)

DEFAULT_NS_MAP = {**AMF_NS_MAP, **CDL_NS_MAP}


def _walk_file_uris(obj, transform_fn: Callable[[str], str]) -> None:
    """Walk a Pydantic model tree and apply *transform_fn* to all ``file`` string fields."""
    if not isinstance(obj, BaseModel):
        return
    for field_name in type(obj).model_fields:
        value = getattr(obj, field_name, None)
        if value is None:
            continue
        if field_name == "file" and isinstance(value, str):
            setattr(obj, field_name, transform_fn(value))
        elif isinstance(value, BaseModel):
            _walk_file_uris(value, transform_fn)
        elif isinstance(value, list):
            for item in value:
                _walk_file_uris(item, transform_fn)


def _decode_file_uris(amf) -> None:
    """Decode percent-encoded file paths in-place after parsing."""
    _walk_file_uris(amf, unquote)


def _encode_file_uris(amf):
    """Return a deep copy with file paths URI-encoded for serialization."""
    amf_copy = copy.deepcopy(amf)
    _walk_file_uris(amf_copy, lambda v: quote(v, safe="/"))
    return amf_copy


def amf_timestamp_string(time: datetime.datetime | None = None) -> str:
    """
    Generate a timestamp string in the AMF style.
    Example: 2024-04-26T17:52:45Z

    If time is None, the current time will be used. Time should be passed in with tzinfo set for proper conversion to UTC.

    This format is defined in the ACES AMF Specification: S-2019-001 section 6.3.5.1
    """
    # if the time is None, use the current utc time
    if time is None:
        time = datetime.datetime.now(datetime.timezone.utc)

    time_str = time.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return time_str


def amf_xml_date_time(time: datetime.datetime | None = None) -> XmlDateTime:
    """
    Create an XmlDateTime for AMF use (UTC, no fractional seconds).

    If time is None, the current UTC time is used.
    """
    if time is None:
        time = datetime.datetime.now(datetime.timezone.utc)
    utc_time = time.astimezone(datetime.timezone.utc)
    return XmlDateTime(
        utc_time.year, utc_time.month, utc_time.day,
        utc_time.hour, utc_time.minute, utc_time.second,
        fractional_second=0, offset=0,
    )


def amf_date_time_now() -> amf_v2.DateTimeType:
    """
    Create a DateTimeType with the current time.
    """
    now = amf_xml_date_time()
    return amf_v2.DateTimeType(creation_date_time=now, modification_date_time=now)


def get_working_location_index(pipeline: amf_v2.PipelineType) -> int | None:
    """Return the index of the workingLocation element in the compound field, or None if absent.

    The v2 schema merges workingLocation and lookTransform into a single
    ``working_location_or_look_transform`` list.  This helper finds the
    workingLocation (a ``WorkingLocationType`` instance) within that list.
    """
    for idx, item in enumerate(pipeline.working_location_or_look_transform):
        if isinstance(item, amf_v2.WorkingLocationType):
            return idx
    return None


def from_amf_data(amf_data: bytes) -> tuple[amf_v2.AcesMetadataFile, dict[str, str]]:
    """Parse AMF XML bytes into a v2 model and namespace map."""
    parser = XmlParser()
    ns_map: dict[str, str] = {}
    parsed = parser.from_bytes(amf_data, amf_v2.AcesMetadataFile, ns_map)
    _decode_file_uris(parsed)
    return parsed, ns_map


def from_amf_file(amf_path: Path | str) -> tuple[amf_v2.AcesMetadataFile, dict[str, str]]:
    """Parse an AMF file into a v2 model and namespace map."""
    parser = XmlParser()
    ns_map: dict[str, str] = {}
    parsed = parser.from_path(Path(amf_path), amf_v2.AcesMetadataFile, ns_map)
    _decode_file_uris(parsed)
    return parsed, ns_map


def _amf_serializer() -> XmlSerializer:
    """
    Create a serializer for AMF data that will serialize in the example style.
    """
    serializer = XmlSerializer()
    serializer.config.indent = "    "
    return serializer




def dump_amf(amf: amf_v2.AcesMetadataFile, ns_map: dict[str, str] = None) -> str:
    """Serialize the provided AMF data to an XML string."""
    if ns_map is None:
        ns_map = DEFAULT_NS_MAP

    serializer = _amf_serializer()
    return serializer.render(_encode_file_uris(amf), ns_map=ns_map)


def write_amf(out: TextIO, amf: amf_v2.AcesMetadataFile, ns_map: dict[str, str] = None) -> str:
    """Serialize the provided AMF data as XML to a text stream."""
    if ns_map is None:
        ns_map = DEFAULT_NS_MAP

    serializer = _amf_serializer()
    return serializer.write(out, _encode_file_uris(amf), ns_map=ns_map)


def _run_validation(amf: amf_v2.AcesMetadataFile, amf_path: Path | None = None, transform_registry=None) -> None:
    """Run validation and raise AMFValidationError on errors.

    Calls schema validation (if path available) + semantic validation directly,
    bypassing validate_semantic() to avoid circular imports.

    Args:
        amf: The parsed AMF model.
        amf_path: Optional file path for schema validation.
        transform_registry: TransformRegistry implementation for validating transform IDs.
            Required if the 'transform_id_registry' validator is active.

    Raises:
        RegistryNotConfiguredError: If transform_id_registry validator runs without a registry.
        AMFValidationError: If validation finds ERROR-level messages.
    """
    from .validation.types import AMFValidationError, ValidationContext, ValidationLevel
    from .validation.schema import validate_schema
    from .validation.registry import get_default_registry

    messages = []

    # Schema validation (needs a file path)
    if amf_path is not None:
        messages.extend(validate_schema(amf_path))

    # Semantic validation — direct registry call, no circular import
    schema_errors = [m for m in messages if m.level == ValidationLevel.ERROR]
    if not schema_errors:
        base_path = amf_path.parent if amf_path is not None else None
        context = ValidationContext(amf_path=amf_path, base_path=base_path, transform_registry=transform_registry)
        registry = get_default_registry()
        messages.extend(registry.validate(amf, context))

    errors = [m for m in messages if m.level == ValidationLevel.ERROR]
    if errors:
        raise AMFValidationError(messages)


def load_amf(path: Path | str, *, validate: bool = True, transform_registry=None) -> amf_v2.AcesMetadataFile:
    """Load an AMF file. Auto-upgrades v1 to v2.

    Args:
        path: Path to the AMF file.
        validate: Run semantic validation on the loaded model. Defaults to True.
        transform_registry: TransformRegistry for transform ID validation.
            Required if validate=True and the 'transform_id_registry' validator is active.

    Returns:
        Parsed AcesMetadataFile (v2).

    Raises:
        RegistryNotConfiguredError: If validate=True and no transform_registry provided.
        AMFValidationError: If validation is enabled and errors are found.
    """
    path = Path(path)
    amf, _ = from_amf_file(path)
    if validate:
        _run_validation(amf, amf_path=None, transform_registry=transform_registry)
    return amf


def load_amf_data(data: bytes, *, validate: bool = True, transform_registry=None) -> amf_v2.AcesMetadataFile:
    """Load AMF from bytes. Auto-upgrades v1 to v2.

    Args:
        data: Raw AMF XML bytes.
        validate: Run semantic validation after loading. Defaults to True.
            Schema validation is skipped (no file path available).
        transform_registry: TransformRegistry for transform ID validation.

    Returns:
        Parsed AcesMetadataFile (v2).

    Raises:
        RegistryNotConfiguredError: If validate=True and no transform_registry provided.
        AMFValidationError: If validation is enabled and errors are found.
    """
    amf, _ = from_amf_data(data)
    if validate:
        _run_validation(amf, amf_path=None, transform_registry=transform_registry)
    return amf


def _prepare_for_write(amf: amf_v2.AcesMetadataFile) -> None:
    """Update modification timestamps and regenerate UUIDs before serialization."""
    now = amf_xml_date_time()
    if amf.amf_info:
        amf.amf_info.date_time.modification_date_time = now
        amf.amf_info.uuid = uuid.uuid4().urn
    if amf.pipeline and amf.pipeline.pipeline_info:
        amf.pipeline.pipeline_info.date_time.modification_date_time = now
        amf.pipeline.pipeline_info.uuid = uuid.uuid4().urn
    for archived in amf.archived_pipeline:
        if archived.pipeline_info and archived.pipeline_info.date_time:
            archived.pipeline_info.date_time.modification_date_time = now


def save_amf(
    amf: amf_v2.AcesMetadataFile,
    path: Path | str,
    *,
    ns_map: dict[str, str] = None,
    validate: bool = True,
    transform_registry=None,
) -> None:
    """Prepare housekeeping fields and write AMF to file.

    Calls ``prepare_for_write`` then serializes to the given path.

    Args:
        amf: The AMF model to write.
        path: Output file path.
        ns_map: Optional namespace map. Defaults to ``DEFAULT_NS_MAP``.
        validate: Run semantic validation after writing. Defaults to True.
        transform_registry: TransformRegistry for transform ID validation.

    Raises:
        RegistryNotConfiguredError: If validate=True and no transform_registry provided.
        AMFValidationError: If validation is enabled and errors are found.
    """
    _prepare_for_write(amf)
    path = Path(path)
    with open(path, "w") as f:
        write_amf(f, amf, ns_map)
    if validate:
        _run_validation(amf, amf_path=None, transform_registry=transform_registry)


def render_amf(
    amf: amf_v2.AcesMetadataFile,
    *,
    ns_map: dict[str, str] = None,
    validate: bool = True,
    transform_registry=None,
) -> str:
    """Prepare housekeeping fields and serialize AMF to an XML string.

    Calls ``prepare_for_write`` then serializes to string.

    Args:
        amf: The AMF model to serialize.
        ns_map: Optional namespace map. Defaults to ``DEFAULT_NS_MAP``.
        validate: Run semantic validation after rendering. Defaults to True.
            Schema validation is skipped (no file path available).
        transform_registry: TransformRegistry for transform ID validation.

    Returns:
        XML string.

    Raises:
        RegistryNotConfiguredError: If validate=True and no transform_registry provided.
        AMFValidationError: If validation is enabled and errors are found.
    """
    _prepare_for_write(amf)
    xml_str = dump_amf(amf, ns_map)
    if validate:
        _run_validation(amf, amf_path=None, transform_registry=transform_registry)
    return xml_str


