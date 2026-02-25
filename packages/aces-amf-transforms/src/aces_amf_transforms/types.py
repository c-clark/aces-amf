# SPDX-License-Identifier: Apache-2.0
"""Transform data types."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TransformInfo:
    """Information about a single ACES transform."""

    transform_id: str
    user_name: str
    transform_type: str
    inverse_transform_id: Optional[str] = None
    previous_equivalent_ids: list[str] = field(default_factory=list)
