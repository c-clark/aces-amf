# SPDX-License-Identifier: Apache-2.0
"""
Core validators for AMF files.

Importing this module auto-registers all core validators with the default registry.
"""

from ..registry import get_default_registry
from .applied_order import AppliedOrderValidator
from .cdl import CDLValidator
from .file_hashes import FileHashValidator
from .file_paths import FilePathValidator
from .metadata import MetadataValidator
from .temporal import TemporalValidator
from .transform_ids import TransformIdFormatValidator
from .uuid_validator import UUIDValidator
from .working_space import WorkingSpaceValidator


def _register_core_validators():
    registry = get_default_registry()
    for validator_cls in [
        TemporalValidator,
        UUIDValidator,
        CDLValidator,
        MetadataValidator,
        AppliedOrderValidator,
        FilePathValidator,
        WorkingSpaceValidator,
        TransformIdFormatValidator,
        FileHashValidator,
    ]:
        registry.register(validator_cls())


_register_core_validators()
