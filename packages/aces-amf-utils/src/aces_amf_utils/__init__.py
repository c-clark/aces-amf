# SPDX-License-Identifier: Apache-2.0
"""CLI, builder, and utilities for ACES Metadata Files (AMF)."""

from aces_amf_utils.aces_amf import ACESAMF
from aces_amf_utils.builder import AMFBuilder
from aces_amf_utils.diff import DiffResult, FieldDiff, diff_amf
from aces_amf_utils.factories import cdl_look_transform, cdl_look_transform_to_dict, minimal_amf, prepare_for_write
from aces_amf_utils.template_registry import (
    REGISTRY,
    TemplateCategory,
    TemplateMetadata,
    TemplateRegistry,
)

__version__ = "0.1.0"

__all__ = [
    "ACESAMF",
    "AMFBuilder",
    "DiffResult",
    "FieldDiff",
    "diff_amf",
    "REGISTRY",
    "TemplateCategory",
    "TemplateMetadata",
    "TemplateRegistry",
    "minimal_amf",
    "cdl_look_transform",
    "cdl_look_transform_to_dict",
    "prepare_for_write",
]
