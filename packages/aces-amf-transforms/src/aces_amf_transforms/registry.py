# SPDX-License-Identifier: Apache-2.0
"""
ACES Transform Registry — implements the TransformRegistry protocol from aces-amf-lib.

Provides lookup and listing of known ACES transform URNs from a bundled
snapshot of the official ACES transforms registry.
"""

from __future__ import annotations

import importlib.resources
import json
import logging
from typing import Optional

from .types import TransformInfo

logger = logging.getLogger(__name__)

_data_dir = importlib.resources.files("aces_amf_transforms") / "data"


class ACESTransformRegistry:
    """Registry of official ACES transforms.

    Loads transform data from a bundled JSON snapshot of the official
    ACES transforms registry. Updates to the transform data require
    a new package release.

    Implements the ``TransformRegistry`` protocol from aces-amf-lib.
    """

    def __init__(self):
        self._data: Optional[dict] = None
        self._index: dict[str, TransformInfo] = {}
        self._previous_id_map: dict[str, str] = {}

    def _ensure_loaded(self):
        if self._data is not None:
            return

        data_path = _data_dir / "aces_transforms.json"
        with importlib.resources.as_file(data_path) as path:
            with open(path) as f:
                self._data = json.load(f)

        self._build_index()

    def _build_index(self):
        for version_key, version_data in self._data.get("transformsData", {}).items():
            for t in version_data.get("transforms", []):
                tid = t["transformId"]
                info = TransformInfo(
                    transform_id=tid,
                    user_name=t.get("userName", ""),
                    transform_type=t.get("transformType", ""),
                    inverse_transform_id=t.get("inverseTransformId") or None,
                    previous_equivalent_ids=t.get("previousEquivalentTransformIds", []),
                )

                # Index by current ID (latest version wins)
                if tid not in self._index:
                    self._index[tid] = info

                # Index previous equivalent IDs mapping to current ID
                for prev_id in info.previous_equivalent_ids:
                    if prev_id not in self._previous_id_map:
                        self._previous_id_map[prev_id] = tid

    def is_valid_transform_id(self, transform_id: str) -> bool:
        """Check if a transform ID exists in the registry.

        Also checks previous equivalent transform IDs for backward compatibility.
        """
        self._ensure_loaded()
        return transform_id in self._index or transform_id in self._previous_id_map

    def get_transform_info(self, transform_id: str) -> Optional[dict]:
        """Get information about a transform by ID.

        Returns a dict with transform metadata, or None if not found.
        Also resolves previous equivalent transform IDs.
        """
        self._ensure_loaded()

        info = self._index.get(transform_id)
        if info is None:
            # Check if it's a previous equivalent ID
            current_id = self._previous_id_map.get(transform_id)
            if current_id:
                info = self._index.get(current_id)

        if info is None:
            return None

        return {
            "transform_id": info.transform_id,
            "user_name": info.user_name,
            "transform_type": info.transform_type,
            "inverse_transform_id": info.inverse_transform_id,
            "previous_equivalent_ids": info.previous_equivalent_ids,
        }

    def list_transforms(self, *, category: Optional[str] = None) -> list[dict]:
        """List all known transforms, optionally filtered by category.

        Args:
            category: Filter by transform type (e.g., 'CSC', 'Output', 'IDT').
        """
        self._ensure_loaded()

        results = []
        seen = set()
        for info in self._index.values():
            if info.transform_id in seen:
                continue
            seen.add(info.transform_id)

            if category and info.transform_type != category:
                continue

            results.append({
                "transform_id": info.transform_id,
                "user_name": info.user_name,
                "transform_type": info.transform_type,
                "inverse_transform_id": info.inverse_transform_id,
            })

        return results

    def get_transform_categories(self) -> list[str]:
        """Get a sorted list of all transform categories/types."""
        self._ensure_loaded()
        return sorted({info.transform_type for info in self._index.values()})

    def are_transforms_inverses(self, id1: str, id2: str) -> bool:
        """Check if two transform IDs are declared inverses of each other."""
        info1 = self.get_transform_info(id1)
        info2 = self.get_transform_info(id2)

        if not info1 or not info2:
            return False

        return (
            info1.get("inverse_transform_id") == info2.get("transform_id")
            or info2.get("inverse_transform_id") == info1.get("transform_id")
        )

    @property
    def transform_count(self) -> int:
        """Total number of unique transforms in the registry."""
        self._ensure_loaded()
        return len(self._index)

    @property
    def schema_version(self) -> str:
        """Schema version of the bundled transforms data."""
        self._ensure_loaded()
        return self._data.get("schemaVersion", "unknown")
