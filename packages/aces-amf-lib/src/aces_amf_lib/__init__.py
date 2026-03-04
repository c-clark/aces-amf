# SPDX-License-Identifier: Apache-2.0
"""
aces-amf-lib — Lightweight reference library for ACES Metadata Files (AMF).

Example usage:
    from aces_amf_lib import load_amf, save_amf, minimal_amf

    # Read an AMF file (automatically upgrades v1 to v2)
    amf = load_amf("example.amf")

    # Access metadata
    print(f"Description: {amf.amf_info.description}")

    # Create a new AMF and write it
    amf = minimal_amf()
    save_amf(amf, "output.amf")
"""

from .amf_utilities import (
    DEFAULT_NS_MAP,
    cdl_look_transform,
    cdl_look_transform_to_dict,
    dump_amf,
    get_working_location_index,
    load_amf,
    load_amf_data,
    minimal_amf,
    prepare_for_write,
    render_amf,
    save_amf,
    write_amf,
)
from .amf_v2 import AcesMetadataFile
from .validation import (
    AMFValidationError,
    ValidationContext,
    ValidationLevel,
    ValidationMessage,
    ValidationType,
    ValidatorRegistry,
    get_default_registry,
    validate_all,
    validate_schema,
    validate_semantic,
)
from .protocols import AMFValidator, TransformRegistry
from . import amf_utilities
from . import amf_v1
from . import amf_v2

__version__ = "0.1.0"

__all__ = [
    "AcesMetadataFile",
    "load_amf",
    "load_amf_data",
    "save_amf",
    "render_amf",
    "prepare_for_write",
    "minimal_amf",
    "cdl_look_transform",
    "cdl_look_transform_to_dict",
    "dump_amf",
    "get_working_location_index",
    "write_amf",
    "DEFAULT_NS_MAP",
    "validate_schema",
    "validate_semantic",
    "validate_all",
    "AMFValidationError",
    "ValidatorRegistry",
    "get_default_registry",
    "ValidationContext",
    "ValidationLevel",
    "ValidationMessage",
    "ValidationType",
    "AMFValidator",
    "TransformRegistry",
    "amf_utilities",
    "amf_v1",
    "amf_v2",
]
