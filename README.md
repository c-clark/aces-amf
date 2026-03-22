<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright Contributors to the ACES Project. -->

# ACES Metadata File (AMF)

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
![AMF Schema and Example
Validation](https://github.com/ampas/aces-amf/actions/workflows/validate-xml.yml/badge.svg)
![GitHub release (with
filter)](https://img.shields.io/github/v/release/ampas/aces-amf) [![CLA
assistant](https://cla-assistant.io/readme/badge/ampas/aces-amf)](https://cla-assistant.io/ampas/aces-amf)

The ACES Metadata File (AMF) is an XML sidecar format for exchanging the
metadata required to reconstruct ACES viewing pipelines. It specifies the
transforms needed to configure an ACES pipeline for a set of related image
files.

This directory includes:

- The ACES Metadata File XML Schema:
  [acesMetadataFile.xsd](./schema/acesMetadataFile.xsd)

- Copies of dependent XML schemas

- [Example AMF files](./examples/)

For details on the AMF format and its use cases, see the [ACES
Documentation](https://docs.acescentral.com/amf/specification/).

## Python Packages

This repository includes a suite of Python packages for working with AMF files programmatically. The packages are organized as a [uv workspace](https://docs.astral.sh/uv/concepts/workspaces/) monorepo under `packages/`.

### Getting Started

```bash
# Install the high-level CLI and utilities (pulls in all dependencies)
pip install aces-amf-utils

# Or install individual packages
pip install aces-amf-lib        # core library only
pip install aces-transforms     # transform registry only
```

### Package Overview

| Package | Description |
|---------|-------------|
| [**aces-amf-utils**](./packages/aces-amf-utils/) | CLI, builder, and utilities for creating, modifying, and analyzing AMF files |
| [**aces-amf-lib**](./packages/aces-amf-lib/) | Reference library for reading, writing, and validating AMF files |
| [**aces-transforms**](./packages/aces-transforms/) | ACES transform ID registry with offline lookup and version mapping |
| [**aces-common**](./packages/aces-common/) | Shared protocols and types |

### Dependency Graph

```
aces-common          (shared protocols, zero dependencies)
  |
  +-- aces-transforms   (transform ID registry)
  |
  +-- aces-amf-lib      (AMF I/O, schema bindings, validation)
        |
        +-- aces-amf-utils  (CLI, builder, high-level API)
```

### Quick Example

```python
from aces_amf_lib import amf_v2
from aces_amf_utils import ACESAMF

# Build a new AMF
amf = (ACESAMF.new()
    .with_description("My Show - Ep 1")
    .with_author(amf_v2.AuthorType(name="Jane Doe", email_address="jane@example.com"))
    .with_input_transform(amf_v2.InputTransformType(
        transform_id="urn:ampas:aces:transformId:v1.5:IDT.ARRI.ARRI-LogC4.a1.v1",
        applied=False))
    .with_output_transform(amf_v2.OutputTransformType(
        transform_id="urn:ampas:aces:transformId:v1.5:ODT.Academy.Rec709_100nits_dim.a1.0.3",
        applied=False)))

amf.write("output.amf")
```

### Development Setup

```bash
# Clone and set up the workspace
git clone https://github.com/ampas/aces-amf.git
cd aces-amf
uv sync

# Run all tests
uv run pytest
```

Requires Python >= 3.10.

## Contributing

ACES depends on community participation. Developers, manufacturers, and end
users are encouraged to contribute code, bug fixes, documentation, and other
technical artifacts.

All contributors must have a signed Contributor License Agreement (CLA) on file
to ensure that the project can freely use your contributions. 

See [CONTRIBUTING.md](./CONTRIBUTING.md) for more details.

## Governance

This repository is a submodule of the ACES project, which is governed by the
Academy Software Foundation.

For details about how the project operates, refer to the
[GOVERNANCE.md](https://github.com/ampas/aces/blob/main/GOVERNANCE.md) file
found in in the top-level ACES repository.

## Reporting Issues

To report a problem with AMF, please open an
[issue](https://github.com/ampas/aces-amf/issues).

If the issue is senstive in nature or a security related issue, please do not
report in the issue tracker. Instead refer to [SECURITY.md](SECURITY.md) for
more information about the project security policy.

## License

The ACES Project is licensed under the [Apache 2.0 license](./LICENSE).