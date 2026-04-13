# aces-transforms

Python package for querying the official [ACES](https://acescentral.com/) transform registry. Provides lookup, validation, and version mapping of ACES transform IDs across all ACES system versions.

This package bundles a snapshot of the official ACES `transforms.json` from the [aces-aswf/aces](https://github.com/aces-aswf/aces) repository. It has **zero dependencies** and works offline out of the box.

## Installation

```bash
pip install aces-transforms
```

## Quick start

```python
from aces.transforms import ACESTransformRegistry

registry = ACESTransformRegistry()

# Look up a transform
info = registry.get_transform_info(
    "urn:ampas:aces:transformId:v2.0:CSC.Academy.ACES_to_ACEScc.a2.v1"
)
print(info["user_name"])  # "ACES2065-1 to ACEScc"

# List all Output transforms for ACES v2.0
outputs = registry.list_transforms(category="Output", version="v2.0")

# Validate a transform ID
registry.is_valid_transform_id(
    "urn:ampas:aces:transformId:v2.0:CSC.Academy.ACES_to_ACEScc.a2.v1"
)  # True
```

## Version-scoped queries

All query methods accept an optional `version` parameter to scope results to a specific ACES system version. Short version strings resolve to the latest matching release:

```python
# "v1.3" resolves to v1.3.1 (latest patch)
registry.list_transforms(version="v1.3")

# "v2.0.0" resolves to the latest build (e.g., v2.0.0+2025.04.04)
registry.list_transforms(version="v2.0.0")

# Exact pin with build suffix
registry.list_transforms(version="v2.0.0+2025.04.04")

# No version = search across all versions
registry.is_valid_transform_id("urn:ampas:aces:transformId:v1.5:IDT.ARRI...")
```

## Version migration

Resolve legacy transform IDs to their canonical equivalent:

```python
# Old v1.x ID -> canonical v2.0 equivalent
registry.get_equivalent_id("ACEScsc.ACES_to_ACEScc.a1.0.3")
# -> "urn:ampas:aces:transformId:v2.0:CSC.Academy.ACES_to_ACEScc.a2.v1"

# What are the equivalent IDs for this transform?
registry.get_equivalent_ids(
    "urn:ampas:aces:transformId:v2.0:CSC.Academy.ACES_to_ACEScc.a2.v1"
)
# -> ["urn:ampas:aces:transformId:v1.5:ACEScsc.Academy.ACES_to_ACEScc.a1.0.3", ...]
```

## API reference

### `ACESTransformRegistry`

| Method | Description |
|--------|-------------|
| `is_valid_transform_id(id, *, version=None)` | Check if a transform ID exists (includes previous equivalent IDs) |
| `get_transform_info(id, *, version=None)` | Get transform metadata as a dict, or `None` |
| `list_transforms(*, category=None, version=None)` | List transforms, optionally filtered by type and version |
| `get_transform_categories(*, version=None)` | Get sorted list of transform types (e.g., CSC, Output, IDT) |
| `are_transforms_inverses(id1, id2, *, version=None)` | Check if two transforms are declared inverses |
| `list_versions()` | List all available ACES version keys |
| `get_equivalent_id(id)` | Resolve a legacy ID to its canonical equivalent |
| `get_equivalent_ids(id)` | Get all equivalent IDs for a transform |
| `transform_count` | Total unique transforms across all versions |
| `schema_version` | Schema version of the bundled data |

### Transform info dict

`get_transform_info()` and `list_transforms()` return dicts with these keys:

```python
{
    "transform_id": "urn:ampas:aces:transformId:v2.0:CSC.Academy.ACES_to_ACEScc.a2.v1",
    "user_name": "ACES2065-1 to ACEScc",
    "transform_type": "CSC",
    "aces_version": "v2.0.0+2025.04.04",
    "inverse_transform_id": "urn:ampas:aces:transformId:v2.0:CSC.Academy.ACEScc_to_ACES.a2.v1",
    "previous_equivalent_ids": [
        "urn:ampas:aces:transformId:v1.5:ACEScsc.Academy.ACES_to_ACEScc.a1.0.3",
        "ACEScsc.ACES_to_ACEScc.a1.0.3",
    ],
}
```

## Updating for a new ACES release

When a new version of ACES is released:

1. **Get the updated `transforms.json`** from the [aces-aswf/aces](https://github.com/aces-aswf/aces) repository. The new version will appear as a new entry in `transformsData`.

2. **Replace the bundled data file** at `src/aces/transforms/data/aces_transforms.json`.

3. **Bump the package version** in `pyproject.toml` and `src/aces/transforms/__init__.py`.

4. **Run tests** to verify:
   ```bash
   pytest tests/ -v
   ```

5. **Release** to PyPI. Downstream consumers update with:
   ```bash
   pip install --upgrade aces-transforms
   ```

No code changes are needed — the registry reads the JSON data dynamically. Only the data file and version number change.

## ACES versions currently included

| Version | Transforms | Package Date |
|---------|-----------|--------------|
| v2.0.0 | 164 | 2025.04.04 |
| v1.3.1 | 993 | |
| v1.3 | 975 | |
| v1.2 | 970 | |
| v1.1 | 948 | |
| v1.0.3 | 930 | |
| v1.0.2 | 925 | |
| v1.0.1 | 922 | |
| v1.0 | 916 | |

## License

Apache-2.0. See [LICENSE](../../LICENSE) for details.
