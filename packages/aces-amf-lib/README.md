# aces-amf-lib

Lightweight Python reference library for reading, writing, validating, and authoring ACES Metadata Files (AMF).

## Installation

```bash
pip install -e .
```

## Quick Start

```python
from aces_amf_lib import load_amf, save_amf, minimal_amf, cdl_look_transform, validate_all

# Read an AMF file (automatically upgrades v1 to v2)
amf = load_amf("example.amf")
print(f"Description: {amf.amf_info.description}")

# Create a new AMF with a CDL look transform
amf = minimal_amf()
amf.amf_info.description = "My Show"
amf.pipeline.pipeline_info.description = "DI Grade"
amf.pipeline.look_transform.append(
    cdl_look_transform(slope=[1.2, 1.0, 0.8], saturation=1.0)
)
save_amf(amf, "output.amf")

# Validate (schema + semantic checks)
messages = validate_all("output.amf")
```

## Features

- **Read/Write AMF files** — Load v1 or v2, always work with v2 internally
- **XSD Validation** — Validate against bundled v1/v2 schemas
- **Semantic Validation** — Date logic, UUID uniqueness, CDL value ranges, applied order, metadata completeness, file path security
- **Type-safe dataclasses** — xsdata-generated bindings for both AMF versions
- **Zero network calls** — Everything works offline

## License

Apache-2.0
