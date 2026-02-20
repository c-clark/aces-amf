# SPDX-License-Identifier: Apache-2.0
"""
Utilities for working with generated AMF classes.

These handle direct interactions with the AMF classes. For a higher level
interface that maintains more semantic correctness, see the ACESAMF class.
"""

import datetime
import json
import uuid
from pathlib import Path
from typing import TextIO

import lxml.etree
from xsdata.exceptions import ParserError
from xsdata.formats.dataclass.parsers import JsonParser
from xsdata.formats.dataclass.serializers import JsonSerializer

from . import amf_v1
from . import amf_v2
from .uri_codec import UriXmlParser, UriXmlSerializer


FloatVector = tuple[float, float, float]

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


def amf_date_time_now() -> amf_v2.DateTimeType:
    """
    Create a DateTimeType with the current time.
    """
    date_time = amf_v2.DateTimeType()
    date_time.creation_date_time = amf_timestamp_string()
    date_time.modification_date_time = amf_timestamp_string()

    return date_time


def minimal_amf(aces_version: tuple[int, int, int] = (1, 3, 0)) -> amf_v2.AcesMetadataFile:
    """
    Create the minimal amf
    """
    amf = amf_v2.AcesMetadataFile()
    amf.amf_info = amf_v2.InfoType(date_time=amf_date_time_now(), uuid=uuid.uuid4().urn)

    aces_version = amf_v2.VersionType(major_version=aces_version[0], minor_version=aces_version[1], patch_version=aces_version[2])
    amf.pipeline = amf_v2.PipelineType()
    amf.pipeline.pipeline_info = amf_v2.PipelineInfoType(date_time=amf_date_time_now(), uuid=uuid.uuid4().urn, system_version=aces_version)

    return amf


def cdl_look_transform(
    *, slope: FloatVector = None, offset: FloatVector = None, power: FloatVector = None, saturation: float = None
) -> amf_v2.LookTransformType:
    """
    Create a CDL look transform from the provided parameters.
    """
    if slope is None:
        slope = (1.0, 1.0, 1.0)
    if offset is None:
        offset = (0.0, 0.0, 0.0)
    if power is None:
        power = (1.0, 1.0, 1.0)
    if saturation is None:
        saturation = 1.0

    if len(slope) != 3 or len(offset) != 3 or len(power) != 3:
        raise ValueError("Slope, offset, and power must be 3 element tuples")

    working_space = amf_v2.CdlWorkingSpaceType(
        from_cdl_working_space=amf_v2.WorkingSpaceTransformType(
            transform_id="urn:ampas:aces:transformId:v1.5:ACEScsc.Academy.ACEScct_to_ACES.a1.0.3"
        ),
    )
    sop_node = amf_v2.AscSop(slope=list(slope), offset=list(offset), power=list(power))
    sat_node = amf_v2.AscSat(saturation=saturation)
    return amf_v2.LookTransformType(cdl_working_space=working_space, asc_sop=sop_node, asc_sat=sat_node, applied=False)


def cdl_look_transform_to_dict(look_transform: amf_v2.LookTransformType) -> dict:
    """
    Convert the provided CDL look transform to a dictionary.
    """
    if look_transform.asc_sop is None:
        raise ValueError("Missing ASC SOP node in CDL look transform")

    asc_cdl = {
        "asc_sop": {
            "slope": look_transform.asc_sop.slope or [1.0, 1.0, 1.0],
            "offset": look_transform.asc_sop.offset or [0.0, 0.0, 0.0],
            "power": look_transform.asc_sop.power or [1.0, 1.0, 1.0],
        },
        "asc_sat": 1.0,
    }
    if look_transform.asc_sat is not None and look_transform.asc_sat.saturation is not None:
        asc_cdl["asc_sat"] = look_transform.asc_sat.saturation

    return asc_cdl


def from_amf_data(amf_data: bytes) -> tuple[amf_v2.AcesMetadataFile, dict[str, str]]:
    """
    Read the provided AMF data and return the parsed data and the namespace map.

    Note: Uses UriXmlParser to automatically decode URL-encoded xs:anyURI values.
    """
    parser = UriXmlParser()
    return _read_amf(amf_data, parser.from_bytes)


def from_amf_file(amf_path: Path | str) -> tuple[amf_v2.AcesMetadataFile, dict[str, str]]:
    """
    Read the provided AMF data and return the parsed data and the namespace map.

    Note: Uses UriXmlParser to automatically decode URL-encoded xs:anyURI values.
    """
    parser = UriXmlParser()
    return _read_amf(Path(amf_path), parser.from_path)


def _read_amf(amf_source: Path | bytes, parse_method: callable) -> tuple[amf_v2.AcesMetadataFile, dict[str, str]]:
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

    return parsed, DEFAULT_NS_MAP


def _amf_serializer() -> UriXmlSerializer:
    """
    Create a serializer for AMF data that will serialize in the example style.

    Note: Uses UriXmlSerializer to automatically encode xs:anyURI values.
    """
    serializer = UriXmlSerializer()
    serializer.config.indent = "    "
    return serializer


def _upgrade_amf_v1_to_v2_in_place(amf_json: dict):
    """
    Upgrade the provided AMF V1 JSON data to V2.

    Note: This modifies the provided dictionary in place.
    """
    amf_json["version"] = "2.0"

    # Change file elements to lists
    try:
        look_transforms = amf_json["pipeline"]["lookTransform"]
    except KeyError:
        return

    for look_transform in look_transforms:
        try:
            file = look_transform["file"]
            if file is None:
                look_transform["file"] = []
            else:
                look_transform["file"] = [file]
        except KeyError:
            pass


def dump_amf(amf: amf_v2.AcesMetadataFile, ns_map: dict[str, str] = None) -> str:
    """
    Write the provided AMF data to bytes.
    """
    if ns_map is None:
        ns_map = DEFAULT_NS_MAP

    serializer = _amf_serializer()
    return serializer.render(amf, ns_map=ns_map)


def write_amf(out: TextIO, amf: amf_v2.AcesMetadataFile, ns_map: dict[str, str] = None) -> str:
    """
    Write the provided AMF data to bytes.
    """
    if ns_map is None:
        ns_map = DEFAULT_NS_MAP

    serializer = _amf_serializer()
    return serializer.write(out, amf, ns_map=ns_map)


def get_amf_namespace(amf_data: bytes) -> str:
    """
    Peeks in the provided amf file data and returns the namespace using streaming parser.

    Uses iterparse for memory-efficient parsing - stops after finding the root element.
    """
    from io import BytesIO

    try:
        # Use iterparse to stream parse - stops after first element
        for event, elem in lxml.etree.iterparse(BytesIO(amf_data), events=('start',)):
            # Get namespace from first element (root)
            amf_version_urn = elem.nsmap.get("aces")
            if amf_version_urn:
                return amf_version_urn
            # If aces namespace not found in root, raise error
            raise ValueError("Missing ACES namespace in AMF")

    except lxml.etree.XMLSyntaxError as e:
        raise ValueError(f"Syntax error in AMF: {e}")
    except StopIteration:
        raise ValueError("Empty or invalid AMF file")
