# SPDX-License-Identifier: Apache-2.0
"""
Custom xsdata hooks for handling xs:anyURI encoding/decoding.

This module provides custom parser and serializer classes that automatically
handle URL encoding/decoding for xs:anyURI fields in the AMF schema.

When parsing XML:
  - Values like "%2Fvol%2F..." are decoded to "/vol/..."

When serializing to XML:
  - Values like "/vol/..." are encoded to "%2Fvol%2F..."
"""

from typing import Any
from urllib.parse import quote, unquote

from pydantic import BaseModel
from xsdata_pydantic.bindings import XmlParser, XmlSerializer


def _decode_uris_in_object(obj: Any) -> None:
    """
    Recursively decode URI-encoded strings in 'file' attributes of Pydantic model objects.

    This modifies the object in place.
    """
    if not isinstance(obj, BaseModel):
        return

    for field_name in type(obj).model_fields:
        value = getattr(obj, field_name)

        # If this is a 'file' field, decode the URI(s)
        if field_name == "file":
            if isinstance(value, str):
                setattr(obj, field_name, unquote(value))
            elif isinstance(value, list):
                setattr(obj, field_name, [unquote(v) if isinstance(v, str) else v for v in value])

        # Recursively process nested models
        elif isinstance(value, BaseModel):
            _decode_uris_in_object(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, BaseModel):
                    _decode_uris_in_object(item)


def _encode_uris_in_object(obj: Any) -> None:
    """
    Recursively encode strings in 'file' attributes of Pydantic model objects.

    This modifies the object in place.
    """
    if not isinstance(obj, BaseModel):
        return

    for field_name in type(obj).model_fields:
        value = getattr(obj, field_name)

        # If this is a 'file' field, encode the URI(s)
        if field_name == "file":
            if isinstance(value, str):
                setattr(obj, field_name, quote(value, safe=""))
            elif isinstance(value, list):
                setattr(obj, field_name, [quote(v, safe="") if isinstance(v, str) else v for v in value])

        # Recursively process nested models
        elif isinstance(value, BaseModel):
            _encode_uris_in_object(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, BaseModel):
                    _encode_uris_in_object(item)


class UriXmlParser(XmlParser):
    """
    Custom XML parser that automatically decodes xs:anyURI values.

    This parser should be used in place of the standard XmlParser when working
    with AMF files to ensure URI fields are properly decoded.

    Example:
        parser = UriXmlParser()
        amf = parser.from_path("example.amf", AcesMetadataFile)
        # Any 'file' elements will have their URL-encoded values decoded
    """

    def parse(self, source: Any, clazz: Any = None, ns_map: dict = None):
        """Parse and decode URIs in the result."""
        result = super().parse(source, clazz, ns_map)
        _decode_uris_in_object(result)
        return result


class UriXmlSerializer(XmlSerializer):
    """
    Custom XML serializer that automatically encodes xs:anyURI values.

    This serializer should be used in place of the standard XmlSerializer when
    working with AMF files to ensure URI fields are properly encoded.

    Example:
        serializer = UriXmlSerializer()
        serializer.config.indent = "    "
        xml_string = serializer.render(amf, ns_map=ns_map)
        # Any 'file' elements will have their values URL-encoded
    """

    def render(self, obj: Any, ns_map: dict = None) -> str:
        """Render with URI encoding."""
        import copy
        import re
        from io import StringIO

        # Make a deep copy to avoid modifying the original object
        obj_copy = copy.deepcopy(obj)
        _encode_uris_in_object(obj_copy)

        # Use a StringIO buffer and call the parent's write method directly
        output = StringIO()
        super().write(output, obj_copy, ns_map)
        xml_string = output.getvalue()

        # The XML serializer escapes % as %25, so we need to unescape it for URI-encoded values
        # We look for patterns like %25XX where XX are hex digits (URL-encoded characters)
        # and convert them back to %XX
        xml_string = re.sub(r"%25([0-9A-Fa-f]{2})", r"%\1", xml_string)

        return xml_string

    def write(self, out: Any, obj: Any, ns_map: dict = None) -> None:
        """Write with URI encoding."""
        import copy
        import re
        from io import StringIO

        # Make a deep copy to avoid modifying the original object
        obj_copy = copy.deepcopy(obj)
        _encode_uris_in_object(obj_copy)

        # Use a StringIO buffer and call the parent's write method directly
        output = StringIO()
        super().write(output, obj_copy, ns_map)
        xml_string = output.getvalue()

        # The XML serializer escapes % as %25, so we need to unescape it for URI-encoded values
        xml_string = re.sub(r"%25([0-9A-Fa-f]{2})", r"%\1", xml_string)

        out.write(xml_string)
