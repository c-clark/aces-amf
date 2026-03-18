# SPDX-License-Identifier: Apache-2.0
"""
High-level wrapper for ACES Metadata Files.

Provides a fluent API for loading, inspecting, mutating, and saving AMF files.

Usage:
    from aces_amf_utils import ACESAMF

    # Load and modify an existing AMF
    amf = ACESAMF.from_file("input.amf")
    amf.with_description("Updated Show").rev_up().write("output.amf")

    # Build a new AMF from scratch
    amf = (ACESAMF.new()
        .with_description("My Show - Ep 1")
        .author("Jane Doe", "jane@example.com")
        .input_transform(transform_id="urn:ampas:aces:transformId:v1.5:IDT.ARRI...")
        .look_transform(file="grade.clf", description="Primary grade")
        .output_transform(transform_id="urn:ampas:aces:transformId:v1.5:RRTODT..."))
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, Self

from aces_amf_lib import (
    AcesMetadataFile,
    DEFAULT_HASH_ALGORITHM,
    amf_v2,
    compute_file_hash,
    load_amf,
    load_amf_data,
    render_amf,
    save_amf,
)
from .factories import minimal_amf, prepare_for_write

from .builder import _AMFMutatorMixin


def _default_registry():
    """Return a default ACESTransformRegistry instance."""
    from aces_transforms import ACESTransformRegistry
    return ACESTransformRegistry()


class ACESAMF(_AMFMutatorMixin):
    """High-level wrapper around an ``AcesMetadataFile``.

    Inherits all fluent mutation methods from ``_AMFMutatorMixin``
    (``input_transform``, ``look_transform``, ``output_transform``, etc.).
    All mutation methods return ``self`` for chaining.
    """

    def __init__(self, amf: AcesMetadataFile, registry=None):
        self._amf = amf
        self._registry = registry

    @property
    def amf(self) -> AcesMetadataFile:
        """Direct model access for interop with lib functions."""
        return self._amf

    # ------------------------------------------------------------------
    # Construction / I/O
    # ------------------------------------------------------------------

    @classmethod
    def new(cls, aces_version: tuple[int, int, int] = (1, 3, 0), *, registry=None) -> ACESAMF:
        """Create a new minimal AMF.

        Args:
            aces_version: ACES system version tuple (major, minor, patch).
            registry: TransformRegistry for validation. Defaults to ACESTransformRegistry.
        """
        return cls(minimal_amf(aces_version=aces_version), registry=registry)

    @classmethod
    def from_file(cls, path: Path | str, *, validate: bool = True, registry=None) -> ACESAMF:
        """Load an AMF from a file path.

        Automatically upgrades v1 AMFs to v2.

        Args:
            path: Path to the AMF file.
            validate: Run semantic validation after loading.
            registry: TransformRegistry for validation. Defaults to ACESTransformRegistry.
        """
        effective_registry = registry or _default_registry()
        return cls(load_amf(path, validate=validate, transform_registry=effective_registry), registry=effective_registry)

    @classmethod
    def from_data(cls, data: bytes, *, validate: bool = True, registry=None) -> ACESAMF:
        """Load an AMF from raw bytes.

        Automatically upgrades v1 AMFs to v2.

        Args:
            data: Raw AMF XML bytes.
            validate: Run semantic validation after loading.
            registry: TransformRegistry for validation. Defaults to ACESTransformRegistry.
        """
        effective_registry = registry or _default_registry()
        return cls(load_amf_data(data, validate=validate, transform_registry=effective_registry), registry=effective_registry)

    def write(self, path: Path | str, *, validate: bool = True, registry=None) -> None:
        """Write the AMF to a file.

        Args:
            path: Destination file path.
            validate: Run semantic validation before writing.
            registry: TransformRegistry override for this write. Falls back to instance registry.
        """
        effective_registry = registry or self._registry or _default_registry()
        save_amf(self._amf, path, validate=validate, transform_registry=effective_registry)

    def dump(self, *, validate: bool = True, registry=None) -> str:
        """Serialize the AMF to an XML string.

        Args:
            validate: Run semantic validation before serializing.
            registry: TransformRegistry override for this call. Falls back to instance registry.
        """
        effective_registry = registry or self._registry or _default_registry()
        return render_amf(self._amf, validate=validate, transform_registry=effective_registry)

    def rev_up(self) -> Self:
        """Update modification timestamps and UUIDs.

        Should be called before writing after making changes.
        """
        prepare_for_write(self._amf)
        return self

    def compute_file_hashes(
        self,
        base_path: Path | str | None = None,
        algorithm: str = DEFAULT_HASH_ALGORITHM,
    ) -> dict[str, bytes]:
        """Compute and set file hashes on all transforms with file references.

        Walks all transforms in the active pipeline and sets ``hash.algorithm``
        and ``hash.value`` for each transform that has a ``file`` reference
        pointing to an existing file.

        Args:
            base_path: Base directory to resolve relative file paths against.
                Defaults to current working directory.
            algorithm: AMF hash algorithm URI. Defaults to SHA-256.

        Returns:
            Dict mapping file reference strings to their computed hash bytes.
            Only includes files that were successfully hashed.

        Raises:
            ValueError: If the algorithm URI is not supported.
        """
        from aces_amf_lib.validation.core_validators.file_hashes import (
            HASH_ALGO_MAP,
            _collect_transforms_with_hashes,
        )

        if algorithm not in HASH_ALGO_MAP:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

        base = Path(base_path) if base_path is not None else Path.cwd()
        results: dict[str, bytes] = {}

        for _, transform in _collect_transforms_with_hashes(self._amf):
            file_ref = getattr(transform, "file", None)
            if not file_ref:
                continue
            resolved = base / file_ref
            if not resolved.is_file():
                continue
            digest = compute_file_hash(resolved, HASH_ALGO_MAP[algorithm])
            transform.hash = amf_v2.HashType(
                value=digest,
                algorithm=amf_v2.HashAlgoType(algorithm),
            )
            results[file_ref] = digest

        return results

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def aces_version(self) -> tuple[int, int, int] | None:
        """ACES system version as a (major, minor, patch) tuple."""
        sv = self._amf.pipeline.pipeline_info.system_version
        if sv is None:
            return None
        try:
            return (int(sv.major_version), int(sv.minor_version), int(sv.patch_version))
        except (TypeError, ValueError):
            return None

    @property
    def aces_major_version(self) -> int | None:
        """Major version of the ACES system, or None if not set."""
        v = self.aces_version
        return v[0] if v is not None else None

    @property
    def amf_description(self) -> str | None:
        """Top-level AMF description."""
        return self._amf.amf_info.description

    @amf_description.setter
    def amf_description(self, value: str) -> None:
        self._amf.amf_info.description = value

    @property
    def pipeline_description(self) -> str | None:
        """Pipeline description."""
        pi = self._amf.pipeline.pipeline_info
        return pi.description if pi else None

    @pipeline_description.setter
    def pipeline_description(self, value: str) -> None:
        self._amf.pipeline.pipeline_info.description = value

    @property
    def amf_authors(self) -> list[amf_v2.AuthorType]:
        """List of AMF authors."""
        return self._amf.amf_info.author

    # ------------------------------------------------------------------
    # Author management
    # ------------------------------------------------------------------

    def add_amf_author(self, name: str, email: str = "") -> Self:
        """Append an author to the AMF.

        Args:
            name: Author name.
            email: Author email address.
        """
        self._amf.amf_info.author.append(
            amf_v2.AuthorType(name=name, email_address=email)
        )
        return self

    def clear_amf_authors(self) -> Self:
        """Remove all authors from the AMF."""
        self._amf.amf_info.author.clear()
        return self

    # ------------------------------------------------------------------
    # Direct transform setters
    # ------------------------------------------------------------------

    def set_input_transform(self, input_transform: amf_v2.InputTransformType) -> Self:
        """Set the input transform directly from an InputTransformType object.

        Use this when you already have a constructed ``InputTransformType``.
        For building inline, use the fluent ``input_transform()`` method instead.

        Args:
            input_transform: The input transform to set.
        """
        self._amf.pipeline.input_transform = input_transform
        return self

    def set_output_transform(self, output_transform: amf_v2.OutputTransformType) -> Self:
        """Set the output transform directly from an OutputTransformType object.

        Use this when you already have a constructed ``OutputTransformType``.
        For building inline, use the fluent ``output_transform()`` method instead.

        Args:
            output_transform: The output transform to set.
        """
        self._amf.pipeline.output_transform = output_transform
        return self

    # ------------------------------------------------------------------
    # Look stack management
    # ------------------------------------------------------------------

    def _look_positions(self) -> list[int]:
        """Return compound-list indices of all LookTransformType items."""
        return [
            i
            for i, item in enumerate(
                self._amf.pipeline.working_location_or_look_transform
            )
            if isinstance(item, amf_v2.LookTransformType)
        ]

    def get_looks(self) -> list[amf_v2.LookTransformType]:
        """Return all look transforms (excludes working location markers)."""
        return self._amf.pipeline.look_transforms

    def get_look(self, idx: int) -> amf_v2.LookTransformType:
        """Return the look transform at logical index ``idx``.

        Supports negative indices.

        Args:
            idx: Logical look index.
        """
        return self.get_looks()[idx]

    def count_looks(self) -> int:
        """Return the number of look transforms."""
        return len(self.get_looks())

    def iter_looks(self) -> Iterator[tuple[int, amf_v2.LookTransformType]]:
        """Yield ``(index, look)`` pairs for all look transforms."""
        return enumerate(self.get_looks())

    def insert_look(self, idx: int, lt: amf_v2.LookTransformType) -> Self:
        """Insert a look transform at logical index ``idx``.

        Working location markers are preserved. If ``idx`` is beyond the
        current number of looks, the look is appended.

        Args:
            idx: Logical look index at which to insert.
            lt: The look transform to insert.
        """
        compound = self._amf.pipeline.working_location_or_look_transform
        positions = self._look_positions()
        if idx >= len(positions):
            compound.append(lt)
        else:
            compound.insert(positions[idx], lt)
        return self

    def remove_look(self, idx: int) -> Self:
        """Remove the look transform at logical index ``idx``.

        Working location markers are preserved. Supports negative indices.

        Args:
            idx: Logical look index to remove.
        """
        compound = self._amf.pipeline.working_location_or_look_transform
        positions = self._look_positions()
        del compound[positions[idx]]
        return self

    def move_look(self, from_idx: int, to_idx: int) -> Self:
        """Move a look transform from one logical index to another.

        Indices are evaluated before the move (``to_idx`` is applied after
        the item at ``from_idx`` is removed).

        Args:
            from_idx: Source logical look index.
            to_idx: Destination logical look index.
        """
        lt = self.get_look(from_idx)
        self.remove_look(from_idx)
        self.insert_look(to_idx, lt)
        return self

    def clear_looks(self) -> Self:
        """Remove all look transforms, preserving working location markers."""
        self._amf.pipeline.working_location_or_look_transform = [
            item
            for item in self._amf.pipeline.working_location_or_look_transform
            if not isinstance(item, amf_v2.LookTransformType)
        ]
        return self

    def add_look_transform(
        self,
        *,
        description: str | None = None,
        transform_id: str | None = None,
        file: str | None = None,
        applied: bool = False,
    ) -> Self:
        """Append a file/ID-based look transform.

        Convenience alias for ``look_transform()`` without CDL.

        Args:
            description: Description of the look.
            transform_id: Transform URN.
            file: File reference.
            applied: Whether this transform has been applied.
        """
        return self.look_transform(
            description=description,
            transform_id=transform_id,
            file=file,
            applied=applied,
        )

    def add_cdl_look_transform(
        self,
        *,
        slope: tuple[float, float, float] = (1.0, 1.0, 1.0),
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        power: tuple[float, float, float] = (1.0, 1.0, 1.0),
        saturation: float = 1.0,
        description: str | None = None,
        applied: bool = False,
    ) -> Self:
        """Append a CDL look transform.

        Convenience alias for ``look_transform()`` with a CDL payload.

        Args:
            slope: ASC SOP slope (R, G, B).
            offset: ASC SOP offset (R, G, B).
            power: ASC SOP power (R, G, B).
            saturation: ASC SAT saturation value.
            description: Description of the look.
            applied: Whether this transform has been applied.
        """
        return self.look_transform(
            description=description,
            applied=applied,
            cdl={
                "asc_sop": {
                    "slope": list(slope),
                    "offset": list(offset),
                    "power": list(power),
                },
                "asc_sat": saturation,
            },
        )

