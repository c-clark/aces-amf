#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Basic usage example for aces-amf-lib."""

from pathlib import Path

from aces_amf_lib import ACESAMF, validate_amf, amf_v2
from aces_amf_lib.semantic_validation import validate_semantic


def create_amf_with_cdl(output_path: Path):
    """Create a new AMF file with a CDL look transform."""
    amf = ACESAMF()

    # Set metadata
    amf.amf_description = "Example Show - Episode 1"
    amf.pipeline_description = "DI Grade Pipeline"

    # Add an author
    author = amf_v2.AuthorType()
    author.name = "Jane Colorist"
    author.email_address = "jane@example.com"
    amf.add_amf_author(author)

    # Set input transform by transform ID
    input_transform = amf_v2.InputTransformType()
    input_transform.transform_id = "urn:ampas:aces:transformId:v1.5:IDT.ARRI.Alexa-v3-logC-EI800.a1.v2"
    input_transform.applied = True
    amf.set_input_transform(input_transform)

    # Add a CDL look transform
    amf.add_cdl_look_transform({
        'asc_sop': {
            'slope': [1.1, 1.0, 0.9],
            'offset': [0.01, 0.0, -0.01],
            'power': [1.0, 1.0, 1.0],
        },
        'asc_sat': 1.05
    })

    # Set output transform
    output_transform = amf_v2.OutputTransformType()
    output_transform.transform_id = "urn:ampas:aces:transformId:v1.5:RRTODT.Academy.Rec709_100nits_dim.a1.0.3"
    output_transform.applied = True
    amf.set_output_transform(output_transform)

    # Write to file
    amf.write(output_path)
    print(f"Created AMF: {output_path}")

    return output_path


def validate_amf_file(amf_path: Path):
    """Validate an AMF file using both XSD and semantic validation."""
    # XSD schema validation
    print(f"\nValidating: {amf_path}")
    xsd_messages = validate_amf(amf_path)
    if xsd_messages:
        for msg in xsd_messages:
            print(f"  XSD: {msg.validation_message}")
    else:
        print("  XSD: PASS")

    # Semantic validation
    sem_messages = validate_semantic(amf_path)
    if sem_messages:
        for msg in sem_messages:
            print(f"  Semantic: {msg}")
    else:
        print("  Semantic: PASS")


def load_and_inspect(amf_path: Path):
    """Load an AMF file and print its contents."""
    amf = ACESAMF.from_file(amf_path)

    print(f"\nAMF: {amf_path.name}")
    print(f"  Description: {amf.amf_description}")
    print(f"  Pipeline: {amf.pipeline_description}")
    print(f"  ACES Version: {'.'.join(str(v) for v in amf.aces_version)}")
    print(f"  Authors: {[a.name for a in amf.amf_authors]}")

    if amf.amf.pipeline:
        if amf.amf.pipeline.input_transform:
            print(f"  Input Transform: {amf.amf.pipeline.input_transform.transform_id}")
        print(f"  Look Transforms: {len(amf.amf.pipeline.look_transform)}")
        if amf.amf.pipeline.output_transform:
            print(f"  Output Transform: {amf.amf.pipeline.output_transform.transform_id}")


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "example_output.amf"
        create_amf_with_cdl(output)
        validate_amf_file(output)
        load_and_inspect(output)
