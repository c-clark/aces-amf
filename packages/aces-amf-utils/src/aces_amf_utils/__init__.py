# SPDX-License-Identifier: Apache-2.0
"""CLI, builder, and utilities for ACES Metadata Files (AMF)."""

from .builder import AMFBuilder
from .diff import DiffResult, FieldDiff, diff_amf
from .template_registry import (
    REGISTRY,
    TemplateCategory,
    TemplateMetadata,
    TemplateRegistry,
)

__version__ = "0.1.0"

__all__ = [
    "AMFBuilder",
    "DiffResult",
    "FieldDiff",
    "diff_amf",
    "REGISTRY",
    "TemplateCategory",
    "TemplateMetadata",
    "TemplateRegistry",
]
