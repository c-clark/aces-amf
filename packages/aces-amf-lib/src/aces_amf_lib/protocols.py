# SPDX-License-Identifier: Apache-2.0
"""
Protocol definitions for plugin interfaces.

These protocols define the contracts that external packages can implement
to extend aces-amf-lib functionality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .amf_v2 import AcesMetadataFile
    from .validation.types import ValidationContext, ValidationMessage


@runtime_checkable
class AMFValidator(Protocol):
    """Protocol for AMF validation plugins.

    Validators are registered with the ValidatorRegistry and invoked
    during semantic validation. Each validator has a unique name and
    a validate method that checks a specific aspect of an AMF file.
    """

    name: str

    def validate(self, amf: AcesMetadataFile, context: ValidationContext) -> list[ValidationMessage]: ...


try:
    from aces_transforms.protocols import TransformRegistry
except ImportError:
    # Fallback: define locally if aces-transforms is not installed
    @runtime_checkable
    class TransformRegistry(Protocol):  # type: ignore[no-redef]
        """Protocol for transform ID registries.

        Implementations provide lookup and listing of known ACES transform URNs.
        The canonical definition lives in ``aces_transforms.protocols``;
        this fallback is provided for backward compatibility when
        ``aces-transforms`` is not installed.
        """

        def is_valid_transform_id(self, transform_id: str) -> bool: ...

        def get_transform_info(self, transform_id: str) -> dict | None: ...

        def list_transforms(self, *, category: str | None = None) -> list[dict]: ...
