# SPDX-License-Identifier: Apache-2.0
"""
Core validators for AMF files.

Importing this module auto-registers all core validators with the default registry.
"""

from aces_amf_lib.validation.registry import get_default_registry
from aces_amf_lib.validation.core_validators.applied_order import AppliedOrderValidator
from aces_amf_lib.validation.core_validators.cdl import CDLValidator
from aces_amf_lib.validation.core_validators.file_hashes import FileHashValidator
from aces_amf_lib.validation.core_validators.file_paths import FilePathValidator
from aces_amf_lib.validation.core_validators.file_references import FileReferenceValidator
from aces_amf_lib.validation.core_validators.metadata import MetadataValidator
from aces_amf_lib.validation.core_validators.temporal import TemporalValidator
from aces_amf_lib.validation.core_validators.transform_ids import TransformIdFormatValidator
from aces_amf_lib.validation.core_validators.transform_registry import TransformRegistryValidator
from aces_amf_lib.validation.core_validators.uuid_validator import UUIDValidator
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
        FileReferenceValidator,
        WorkingSpaceValidator,
        TransformIdFormatValidator,
        FileHashValidator,
        TransformRegistryValidator,
    ]:
        registry.register(validator_cls())


_register_core_validators()
