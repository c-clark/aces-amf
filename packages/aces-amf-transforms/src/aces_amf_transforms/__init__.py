# SPDX-License-Identifier: Apache-2.0
"""
aces-amf-transforms — ACES transform URN registry for AMF validation.

Provides a bundled snapshot of the official ACES transforms registry
and a validator that checks transform IDs against it.

Usage:
    from aces_amf_transforms import ACESTransformRegistry

    registry = ACESTransformRegistry()
    if registry.is_valid_transform_id("urn:ampas:aces:transformId:v1.5:IDT.ARRI..."):
        info = registry.get_transform_info("urn:ampas:aces:transformId:v1.5:IDT.ARRI...")
"""

from .registry import ACESTransformRegistry
from .types import TransformInfo
from .validator import TransformIdValidator

__version__ = "0.1.0"

__all__ = [
    "ACESTransformRegistry",
    "TransformInfo",
    "TransformIdValidator",
]
