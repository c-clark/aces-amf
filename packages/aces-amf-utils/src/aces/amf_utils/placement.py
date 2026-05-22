# SPDX-License-Identifier: Apache-2.0
# Copyright Contributors to the ACES Project.
"""Transform placement validation for authoring APIs."""

from __future__ import annotations

from aces.common.constants import (
    V2_INPUT_TRANSFORM_PREFIXES,
    V2_LOOK_TRANSFORM_PREFIXES,
    V2_OUTPUT_TRANSFORM_PREFIXES,
)
from aces.common.types import TransformURN

INPUT_PLACEMENT = (V2_INPUT_TRANSFORM_PREFIXES, "InputTransform")
OUTPUT_PLACEMENT = (V2_OUTPUT_TRANSFORM_PREFIXES, "OutputTransform")
LOOK_PLACEMENT = (V2_LOOK_TRANSFORM_PREFIXES, "LookTransform")


def validate_transform_placement(
    transform_id: str | None,
    allowed: frozenset[str],
    label: str,
) -> None:
    """Validate that a transform_id URN prefix is allowed for the given container.

    Raises ValueError if the transform_id has a type prefix not in the allowed set.
    No-ops if transform_id is None or not a parseable ACES URN.
    """
    if transform_id is None:
        return
    parsed = TransformURN.parse(transform_id)
    if parsed and parsed.transform_type not in allowed:
        raise ValueError(
            f"Transform ID '{transform_id}' has type '{parsed.transform_type}' "
            f"which is not valid for {label}. "
            f"Allowed: {sorted(allowed)}"
        )
