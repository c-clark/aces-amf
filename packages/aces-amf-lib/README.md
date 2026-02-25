# aces-amf-lib

Lightweight Python reference library for reading, writing, validating, and authoring ACES Metadata Files (AMF).

## Installation

```bash
pip install -e .
```

## Quick Start

```python
from aces_amf_lib import ACESAMF, validate_amf

# Read an AMF file (automatically upgrades v1 to v2)
amf = ACESAMF.from_file("example.amf")
print(f"Description: {amf.amf_description}")
print(f"ACES version: {amf.aces_version}")

# Create a new AMF with a CDL look transform
amf = ACESAMF()
amf.amf_description = "My Show"
amf.pipeline_description = "DI Grade"
amf.add_cdl_look_transform({
    'asc_sop': {'slope': [1.2, 1.0, 0.8], 'offset': [0, 0, 0], 'power': [1, 1, 1]},
    'asc_sat': 1.0
})
amf.write("output.amf")

# Validate against XSD schema
messages = validate_amf("output.amf")
```

## Features

- **Read/Write AMF files** — Load v1 or v2, always work with v2 internally
- **XSD Validation** — Validate against bundled v1/v2 schemas
- **Semantic Validation** — Date logic, UUID uniqueness, CDL value ranges, applied order, metadata completeness, file path security
- **Type-safe dataclasses** — xsdata-generated bindings for both AMF versions
- **Zero network calls** — Everything works offline

## License

Apache-2.0
