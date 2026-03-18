# SPDX-License-Identifier: Apache-2.0
"""
Utilities for working with generated AMF classes.

Provides both low-level functions (dump_amf, write_amf, from_amf_file, from_amf_data)
and high-level convenience functions (load_amf, save_amf, render_amf, minimal_amf).
"""

import copy
import datetime
import json
import uuid
from io import BytesIO
from pathlib import Path
from typing import Callable, TextIO
from urllib.parse import quote, unquote

import lxml.etree
from pydantic import BaseModel
from xsdata.exceptions import ParserError
from xsdata.models.datatype import XmlDateTime
from xsdata_pydantic.bindings import JsonParser, JsonSerializer, XmlParser, XmlSerializer

from . import amf_v1
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
    """Parse AMF XML bytes into a v2 model and namespace map.

    Automatically upgrades v1 AMF data to v2 if needed.
    """
    parser = XmlParser()
    return _read_amf(amf_data, parser.from_bytes)


def from_amf_file(amf_path: Path | str) -> tuple[amf_v2.AcesMetadataFile, dict[str, str]]:
    """Parse an AMF file into a v2 model and namespace map.

    Automatically upgrades v1 AMF files to v2 if needed.
    """
    parser = XmlParser()
    return _read_amf(Path(amf_path), parser.from_path)


def _read_amf(amf_source: Path | bytes, parse_method: Callable) -> tuple[amf_v2.AcesMetadataFile, dict[str, str]]:
    """
    Read the provided AMF data and return the parsed data and the namespace map.
    """
    out_ns_map = {}
    v2_parse_error = None
    parsed = None
    try:
        # If it's a regular AMF V2, parse and return it
        parsed = parse_method(amf_source, amf_v2.AcesMetadataFile, out_ns_map)
    except ParserError as parse_error:
        # This may be an AMF V1 file, try to parse it as such and then convert it to V2
        v2_parse_error = parse_error

    if v2_parse_error is None:
        _decode_file_uris(parsed)
        return parsed, out_ns_map

    # If the first parse attempt failed, try parsing as V1 and upgrading
    try:
        parsed = parse_method(amf_source, amf_v1.AcesMetadataFile, out_ns_map)
    except ParserError:
        raise v2_parse_error

    # Push the JSON representation of V1 data through the V2 parser
    serialized = JsonSerializer().render(parsed)

    # Set the AMF version to 2.0
    data = json.loads(serialized)
    _upgrade_amf_v1_to_v2_in_place(data)
    serialized = json.dumps(data)
    parsed = JsonParser().from_string(serialized, amf_v2.AcesMetadataFile)

    _decode_file_uris(parsed)
    return parsed, DEFAULT_NS_MAP


def _amf_serializer() -> XmlSerializer:
    """
    Create a serializer for AMF data that will serialize in the example style.
    """
    serializer = XmlSerializer()
    serializer.config.indent = "    "
    return serializer


def _upgrade_amf_v1_to_v2_in_place(amf_json: dict):
    """
    Upgrade the provided AMF V1 JSON data to V2.

    V1→V2 differences handled:
    - ``uuid`` on amfInfo/pipelineInfo: optional in v1, required in v2
    - ``applied`` on outputTransform: absent in v1, required in v2
    - ``lookTransform`` renamed to ``working_location_or_look_transform``
      (v2 uses compound field for workingLocation/lookTransform interleaving)

    Note: This modifies the provided dictionary in place.
    """
    amf_json["version"] = "2.0"

    # Generate UUIDs where missing (optional in v1, required in v2)
    amf_info = amf_json.get("amfInfo")
    if amf_info and not amf_info.get("uuid"):
        amf_info["uuid"] = uuid.uuid4().urn

    pipeline = amf_json.get("pipeline")
    if not pipeline:
        return

    pipeline_info = pipeline.get("pipelineInfo")
    if pipeline_info:
        if not pipeline_info.get("uuid"):
            pipeline_info["uuid"] = uuid.uuid4().urn
        # Default systemVersion for legacy v1 files that omit it
        if not pipeline_info.get("systemVersion"):
            pipeline_info["systemVersion"] = {
                "majorVersion": 1, "minorVersion": 3, "patchVersion": 0,
            }

    # Rename lookTransform to compound field name (v2 uses xs:choice for
    # workingLocation/lookTransform interleaving)
    look_transforms = pipeline.pop("lookTransform", None)
    if look_transforms is not None:
        pipeline["working_location_or_look_transform"] = look_transforms

    # Add applied=false on outputTransform (absent in v1, required in v2)
    _ensure_applied(pipeline.get("outputTransform"))

    # Handle archivedPipeline entries the same way
    for archived in amf_json.get("archivedPipeline", []):
        archived_pipeline_info = archived.get("pipelineInfo")
        if archived_pipeline_info and not archived_pipeline_info.get("uuid"):
            archived_pipeline_info["uuid"] = uuid.uuid4().urn
        _ensure_applied(archived.get("outputTransform"))
        # Rename lookTransform in archived pipelines too
        archived_looks = archived.pop("lookTransform", None)
        if archived_looks is not None:
            archived["working_location_or_look_transform"] = archived_looks


def _ensure_applied(transform_dict: dict | None) -> None:
    """Set ``applied`` to ``false`` on a transform dict if not already present."""
    if transform_dict is not None and "applied" not in transform_dict:
        transform_dict["applied"] = False


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
        context = ValidationContext(amf_path=amf_path, transform_registry=transform_registry)
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


def get_amf_namespace(amf_data: bytes) -> str:
    """
    Peeks in the provided amf file data and returns the namespace using streaming parser.

    Uses iterparse for memory-efficient parsing - stops after finding the root element.
    """
    try:
        # Use iterparse to stream parse - stops after first element
        for event, elem in lxml.etree.iterparse(BytesIO(amf_data), events=('start',)):
            # Get namespace from first element (root)
            amf_version_urn = elem.nsmap.get("aces")
            if amf_version_urn:
                return amf_version_urn
            # If aces namespace not found in root, raise error
            raise ValueError("Missing ACES namespace in AMF")

        # Loop completed without finding any elements
        raise ValueError("Empty or invalid AMF file")

    except lxml.etree.XMLSyntaxError as e:
        raise ValueError(f"Syntax error in AMF: {e}")
