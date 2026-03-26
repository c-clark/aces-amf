# SPDX-License-Identifier: Apache-2.0
"""
aces-amf-lib — Lightweight reference library for ACES Metadata Files (AMF).

Example usage:
    from aces_amf_lib import load_amf, save_amf

    # Read an AMF file
    amf = load_amf("example.amf")

    # Access metadata
    print(f"Description: {amf.amf_info.description}")

    # Write back
    save_amf(amf, "output.amf")
"""

from .amf_helpers import (
    DEFAULT_NS_MAP,
    dump_amf,
    get_working_location_index,
    load_amf,
    load_amf_data,
    render_amf,
    save_amf,
    write_amf,
)
from .amf_v2 import AcesMetadataFile
from .validation import (
    AMFValidationError,
    RegistryNotConfiguredError,
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
from .validation.core_validators.file_hashes import compute_file_hash, DEFAULT_HASH_ALGORITHM
from . import amf_helpers
from . import amf_v2

__version__ = "0.1.0"

__all__ = [
    "AcesMetadataFile",
    "load_amf",
    "load_amf_data",
    "save_amf",
    "render_amf",
    "dump_amf",
    "get_working_location_index",
    "write_amf",
    "DEFAULT_NS_MAP",
    "validate_schema",
    "validate_semantic",
    "validate_all",
    "AMFValidationError",
    "RegistryNotConfiguredError",
    "ValidatorRegistry",
    "get_default_registry",
    "ValidationContext",
    "ValidationLevel",
    "ValidationMessage",
    "ValidationType",
    "AMFValidator",
    "TransformRegistry",
    "compute_file_hash",
    "DEFAULT_HASH_ALGORITHM",
    "amf_helpers",
    "amf_v2",
]
