# SPDX-License-Identifier: Apache-2.0
"""
XSD schema validation for AMF files.
"""

import importlib.resources
from importlib import resources
from dataclasses import dataclass
from enum import auto, Enum
from pathlib import Path

from lxml import etree


# Location of acesMetadataFile.xsd for each AMF version
_data_dir = importlib.resources.files("aces_amf_lib") / "data"
AMF_XSD_PATH_MAP = {
    "urn:ampas:aces:amf:v1.0": _data_dir / "amf-schema" / "v1",
    "urn:ampas:aces:amf:v2.0": _data_dir / "amf-schema" / "v2",
}


class ValidationType(Enum):
    SCHEMA_VIOLATION = auto()


@dataclass
class ValidationMessage:
    validation_type: ValidationType
    validation_message: str


def validate_amf(amf_path: Path | str) -> list[ValidationMessage]:
    amf_path = Path(amf_path)
    validation_messages: list[ValidationMessage] = []

    # Peek the file to find the AMF version from the XML namespace
    try:
        with open(amf_path, "rb") as xml_file:
            tree = etree.parse(xml_file)
        amf_version_urn = tree.getroot().nsmap["aces"]
    except etree.XMLSyntaxError as e:
        validation_messages.append(ValidationMessage(ValidationType.SCHEMA_VIOLATION, f"Syntax error in AMF {amf_path}: {e}"))
        return validation_messages
    except KeyError:
        validation_messages.append(ValidationMessage(ValidationType.SCHEMA_VIOLATION, f"Missing ACES namespace in AMF {amf_path}"))
        return validation_messages

    # Find the XSD for the AMF version
    try:
        xsd_resource_path = AMF_XSD_PATH_MAP[amf_version_urn]
    except KeyError:
        validation_messages.append(
            ValidationMessage(ValidationType.SCHEMA_VIOLATION, f"Unsupported AMF version in AMF {amf_path}: {amf_version_urn}")
        )
        return validation_messages

    # load and validate the document against the schema
    try:
        with resources.as_file(xsd_resource_path) as xsd_dir:
            xsd_path = xsd_dir / "acesMetadataFile.xsd"
            xsd_doc = etree.parse(str(xsd_path))
            schema = etree.XMLSchema(xsd_doc)

        parser = etree.XMLParser(schema=schema)
        with open(amf_path, "rb") as xml_file:
            etree.parse(xml_file, parser)
    except etree.XMLSyntaxError as e:
        validation_messages.append(ValidationMessage(ValidationType.SCHEMA_VIOLATION, f"Syntax error in AMF {amf_path}: {e}"))
    except etree.XMLSchemaParseError as e:
        validation_messages.append(ValidationMessage(ValidationType.SCHEMA_VIOLATION, f"Schema error in AMF {amf_path}: {e}"))
    except Exception as e:
        validation_messages.append(ValidationMessage(ValidationType.SCHEMA_VIOLATION, f"Unexpected error in AMF {amf_path}: {str(e)}"))

    return validation_messages
