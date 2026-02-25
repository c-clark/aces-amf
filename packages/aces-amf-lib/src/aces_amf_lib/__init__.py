# SPDX-License-Identifier: Apache-2.0
"""
aces-amf-lib — Lightweight reference library for ACES Metadata Files (AMF).

Example usage:
    from aces_amf_lib import ACESAMF

    # Read an AMF file (automatically upgrades v1 to v2)
    amf = ACESAMF.from_file("example.amf")

    # Access metadata
    print(f"Description: {amf.amf_description}")

    # Add a CDL transform
    amf.add_cdl_look_transform({
        'asc_sop': {'slope': [1.2, 1.0, 0.8], 'offset': [0, 0, 0], 'power': [1, 1, 1]},
        'asc_sat': 1.0
    })

    # Write back
    amf.write("modified.amf")
"""

from .aces_amf import ACESAMF
from .validation import (
    validate_schema,
    validate_semantic,
    validate_all,
    ValidatorRegistry,
    get_default_registry,
    ValidationContext,
    ValidationLevel,
    ValidationMessage,
    ValidationType,
)
from .protocols import AMFValidator, TransformRegistry
from . import amf_utilities
from . import amf_v1
from . import amf_v2

__version__ = "0.1.0"

# Backward compat: old validate_amf was schema-only
validate_amf = validate_schema

__all__ = [
    "ACESAMF",
    "validate_amf",
    "validate_schema",
    "validate_semantic",
    "validate_all",
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
