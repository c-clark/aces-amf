# aces-amf-lib

Reference Python library for reading, writing, and validating ACES Metadata Files (AMF).

Provides type-safe Pydantic schema bindings, I/O helpers, and a pluggable validation system. For high-level builder and CLI tools, see [aces-amf-utils](../aces-amf-utils/).

## Installation

```bash
pip install aces-amf-lib
```

## Quick Start

```python
from aces_amf_lib import load_amf, save_amf, amf, validate_all

# Load an AMF file (automatically upgrades v1 to v2)
amf = load_amf("example.amf")
print(f"Description: {amf.amf_info.description}")
print(f"Input: {amf.pipeline.input_transform}")

# Modify directly via Pydantic models
amf.amf_info.description = "Updated Show"
amf.pipeline.input_transform = amf.InputTransformType(
    transform_id="urn:ampas:aces:transformId:v1.5:IDT.ARRI.ARRI-LogC4.a1.v1",
    applied=False,
)
save_amf(amf, "output.amf")

# Validate (schema + semantic checks)
messages = validate_all("output.amf")
for msg in messages:
    print(f"[{msg.level.name}] {msg.message}")
```

## Features

- **Read/Write AMF files** -- Load v1 or v2, always work with v2 internally
- **Automatic v1-to-v2 upgrade** -- v1 files are transparently upgraded on load
- **XSD schema validation** -- Validate against bundled v1/v2 XML schemas
- **Semantic validation** -- Date logic, UUID uniqueness, CDL value ranges, applied order, metadata completeness, file path security, transform ID verification
- **Pluggable validators** -- Register custom validators via the `aces_amf.validators` entry point
- **Type-safe Pydantic models** -- xsdata-generated Pydantic `BaseModel` bindings for both schema versions
- **Zero network calls** -- Everything works offline with bundled schemas

## I/O Functions

```python
from aces_amf_lib import load_amf, load_amf_data, save_amf, render_amf

# Load from file or bytes
amf = load_amf("file.amf", validate=True)
amf = load_amf_data(xml_bytes, validate=True)

# Save to file or serialize to string
save_amf(amf, "output.amf", validate=True)
xml_string = render_amf(amf, validate=True)
```

All I/O functions accept `validate=True` (default) to run semantic validation automatically. Pass `validate=False` to skip.

## Schema Bindings

The `amf` module provides Pydantic models generated from the ACES AMF v2 XSD schema:

```python
from aces_amf_lib import AcesMetadataFile, amf

# Root document
amf = AcesMetadataFile(...)

# Key types
amf.InputTransformType       # input transform (transform_id, file, applied, ...)
amf.OutputTransformType      # output transform
amf.LookTransformType        # look transforms (file, CDL, transform_id, applied, ...)
amf.AuthorType               # author (name, email_address)
amf.ClipIdType               # clip identification (clip_name, file, uuid, sequence)
amf.VersionType              # system version (major, minor, patch)
amf.WorkingLocationType      # working location marker in compound list
amf.HashType                 # file hash (value, algorithm)
amf.DateTimeType             # creation and modification timestamps
amf.CdlWorkingSpaceType     # CDL working space transforms
amf.AscSop                   # ASC CDL slope/offset/power
amf.AscSat                   # ASC CDL saturation
```

### Compound Field: Working Location + Looks

The pipeline stores look transforms and working location markers in a single interleaved list:

```python
# The compound list preserves ordering between looks and the working location marker
pipeline.working_location_or_look_transform  # list[WorkingLocationType | LookTransformType]

# Convenience property for just the looks (filtered view)
pipeline.look_transforms  # list[LookTransformType]

# Find the working location marker index
from aces_amf_lib import get_working_location_index
idx = get_working_location_index(pipeline)  # int | None
```

## Validation

### Schema Validation

Validates AMF XML against the bundled XSD schemas (v1 or v2 auto-detected):

```python
from aces_amf_lib import validate_schema
messages = validate_schema("file.amf")
```

### Semantic Validation

Runs pluggable validators that check logical correctness:

```python
from aces_amf_lib import validate_semantic
messages = validate_semantic("file.amf", transform_registry=registry)
```

Built-in semantic validators:

| Validator | Checks |
|-----------|--------|
| `temporal` | Creation <= modification, no future timestamps |
| `uuid` | UUIDs exist, URN format valid, no duplicates |
| `cdl` | Slope/offset/power/saturation ranges, identity detection |
| `metadata` | Description, authors, transform descriptions present |
| `applied_order` | Applied transforms follow correct logical order |
| `file_paths` | No path traversal, portable characters |
| `working_space` | At most one working location, CDL transforms have working space |
| `transform_ids` | Transform ID URN format validation |
| `file_hashes` | File hash integrity (SHA256, SHA1, MD5) |
| `transform_id_registry` | Transform IDs exist in provided registry |

### Combined Validation

```python
from aces_amf_lib import validate_all
messages = validate_all("file.amf", transform_registry=registry)
```

### Custom Validators

Register custom validators via the `aces_amf.validators` entry point in your package's `pyproject.toml`:

```toml
[project.entry-points."aces_amf.validators"]
my_validator = "my_package:MyValidator"
```

Validators implement the `AMFValidator` protocol:

```python
from aces_amf_lib import AMFValidator, AcesMetadataFile, ValidationContext, ValidationMessage

class MyValidator:
    name = "my_validator"

    def validate(self, amf: AcesMetadataFile, context: ValidationContext) -> list[ValidationMessage]:
        ...
```

## Utilities

```python
from aces_amf_lib import compute_file_hash, DEFAULT_HASH_ALGORITHM

# Compute file hash
digest = compute_file_hash("grade.clf", "sha256")
```

## License

Apache-2.0
