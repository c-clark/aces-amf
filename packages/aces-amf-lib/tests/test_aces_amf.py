# SPDX-License-Identifier: Apache-2.0
"""Tests for the public AMF API (load, save, render, minimal_amf)."""

import time

import pytest

from aces_amf_lib import (
    load_amf,
    load_amf_data,
    save_amf,
    render_amf,
    prepare_for_write,
    minimal_amf,
    cdl_look_transform,
)
from aces_amf_lib.amf_v2 import AcesMetadataFile, VersionType
from aces_amf_lib.validation import validate_schema


def test_load_amf_v2(aces_amf_examples_path):
    """Test loading a v2 AMF file."""
    amf_path = aces_amf_examples_path / "example6.amf"
    amf = load_amf(amf_path)
    assert isinstance(amf, AcesMetadataFile)
    assert amf.amf_info.uuid == "urn:uuid:afe122be-59d3-4360-ad69-33c10108fa7a"


def test_load_amf_data(aces_amf_examples_path):
    """Test loading AMF from bytes."""
    amf_path = aces_amf_examples_path / "example6.amf"
    with amf_path.open("rb") as f:
        amf = load_amf_data(f.read())
    assert amf.amf_info.uuid == "urn:uuid:afe122be-59d3-4360-ad69-33c10108fa7a"


def test_render_amf(aces_amf_examples_path):
    amf_path = aces_amf_examples_path / "example6.amf"
    amf = load_amf(amf_path)
    dumped = render_amf(amf)

    assert isinstance(dumped, str)
    assert "<aces:amfInfo>" in dumped
    assert "<aces:uuid>" in dumped
    # Verify actual data survives the render (not just tags)
    assert amf.pipeline is not None
    assert "urn:ampas:aces:amf:v2.0" in dumped


def test_save_amf(aces_amf_examples_path, tmp_path):
    amf_path = aces_amf_examples_path / "example6.amf"
    amf = load_amf(amf_path)

    out_path = tmp_path / "out.amf"
    save_amf(amf, out_path)

    out_data = out_path.read_text()
    assert "<aces:amfInfo>" in out_data
    assert "<aces:uuid>" in out_data


def test_create_minimal(tmp_path):
    amf = minimal_amf()
    out_path = tmp_path / "out.amf"
    save_amf(amf, out_path)

    validation_messages = validate_schema(out_path)
    assert not validation_messages


def test_create_with_cdl(tmp_path):
    amf = minimal_amf()
    amf.pipeline.working_location_or_look_transform.append(
        cdl_look_transform(
            slope=(1.0, 1.0, 1.0),
            offset=(0.0, 0.0, 0.0),
            power=(1.0, 1.0, 1.0),
            saturation=1.0,
        )
    )

    out_path = tmp_path / "out.amf"
    save_amf(amf, out_path)

    validation_messages = validate_schema(out_path)
    assert not validation_messages


def test_housekeeping_updates(tmp_path):
    amf = minimal_amf()
    out_path = tmp_path / "minimal.amf"
    save_amf(amf, out_path)

    time.sleep(1.00)

    amf.pipeline.working_location_or_look_transform.append(
        cdl_look_transform(
            slope=(1.0, 1.0, 1.0),
            offset=(0.0, 0.0, 0.0),
            power=(1.0, 1.0, 1.0),
            saturation=1.0,
        )
    )

    out_path_updated = tmp_path / "updated_with_cdl.amf"
    save_amf(amf, out_path_updated)

    original = load_amf(out_path)
    updated = load_amf(out_path_updated)

    assert original.amf_info.uuid != updated.amf_info.uuid
    assert original.amf_info.date_time.creation_date_time == updated.amf_info.date_time.creation_date_time
    assert original.amf_info.date_time.modification_date_time != updated.amf_info.date_time.modification_date_time
    assert original.pipeline.pipeline_info.uuid != updated.pipeline.pipeline_info.uuid


def test_prepare_for_write():
    """Make sure prepare_for_write updates UUIDs and timestamps."""
    amf = minimal_amf()
    original_uuid = amf.amf_info.uuid
    original_pipeline_uuid = amf.pipeline.pipeline_info.uuid

    prepare_for_write(amf)

    # UUIDs should be regenerated
    assert amf.amf_info.uuid != original_uuid
    assert amf.pipeline.pipeline_info.uuid != original_pipeline_uuid
    # Modification timestamp should be set
    assert amf.amf_info.date_time.modification_date_time is not None
    assert amf.pipeline.pipeline_info.date_time.modification_date_time is not None


def test_roundtrip(aces_amf_examples_path, tmp_path):
    """Test round-trip: load -> write -> validate -> load."""
    amf_path = aces_amf_examples_path / "example6.amf"
    amf = load_amf(amf_path)

    out_path = tmp_path / "roundtrip.amf"
    save_amf(amf, out_path)

    # Validate the output
    validation_messages = validate_schema(out_path)
    assert not validation_messages

    # Load back and verify
    amf2 = load_amf(out_path)
    assert amf2.pipeline is not None
    assert len(amf2.pipeline.look_transforms) == len(amf.pipeline.look_transforms)


def test_set_aces_version():
    amf = minimal_amf()
    amf.pipeline.pipeline_info.system_version = VersionType(
        major_version=2, minor_version=0, patch_version=0
    )
    sv = amf.pipeline.pipeline_info.system_version
    assert (sv.major_version, sv.minor_version, sv.patch_version) == (2, 0, 0)


# --- v1 loading and upgrade tests ---


def test_load_amf_v1(test_data_path):
    """Loading a v1 AMF auto-upgrades to v2 and generates missing UUIDs."""
    amf = load_amf(test_data_path / "v1_example.amf")
    assert isinstance(amf, AcesMetadataFile)
    # UUIDs should be generated (not present in v1 fixture)
    assert amf.amf_info.uuid is not None
    assert amf.amf_info.uuid.startswith("urn:uuid:")
    assert amf.pipeline.pipeline_info.uuid is not None
    assert amf.pipeline.pipeline_info.uuid.startswith("urn:uuid:")


def test_load_amf_v1_output_transform_applied(test_data_path):
    """v1 outputTransform (no applied attr) gets applied=False after upgrade."""
    amf = load_amf(test_data_path / "v1_example.amf")
    assert amf.pipeline.output_transform is not None
    assert amf.pipeline.output_transform.applied is False


def test_load_amf_v1_file_field_preserved(test_data_path):
    """file field stays as str (not converted to list) after v1→v2 upgrade."""
    amf = load_amf(test_data_path / "v1_example.amf")
    look = amf.pipeline.look_transforms[0]
    assert look.file == "showLook.clf"
    assert isinstance(look.file, str)


# --- Auto-validation tests ---


def test_load_validates_by_default(aces_amf_examples_path):
    """Valid AMF files load without raising."""
    amf = load_amf(aces_amf_examples_path / "example6.amf")
    assert amf is not None


def test_load_skip_validation(aces_amf_examples_path):
    """validate=False skips validation entirely."""
    amf = load_amf(aces_amf_examples_path / "example6.amf", validate=False)
    assert amf is not None


def test_save_validates_by_default(tmp_path):
    """Valid AMF saves without raising."""
    amf = minimal_amf()
    out = tmp_path / "valid.amf"
    save_amf(amf, out)
    assert out.exists()


def test_save_raises_on_invalid(tmp_path):
    """save_amf with validate=True raises on ERROR-level issues."""
    from aces_amf_lib.validation.types import AMFValidationError

    amf = minimal_amf()
    amf.pipeline.working_location_or_look_transform.append(
        cdl_look_transform(slope=(-1.0, 1.0, 1.0))
    )
    out = tmp_path / "invalid.amf"
    with pytest.raises(AMFValidationError):
        save_amf(amf, out)


def test_save_skip_validation(tmp_path):
    """validate=False allows saving invalid AMF without error."""
    amf = minimal_amf()
    amf.pipeline.working_location_or_look_transform.append(
        cdl_look_transform(slope=(-1.0, 1.0, 1.0))
    )
    out = tmp_path / "invalid.amf"
    save_amf(amf, out, validate=False)
    assert out.exists()


def test_v1_upgrade_validates(test_data_path):
    """v1→v2 upgrade runs semantic validation on the upgraded model."""
    amf = load_amf(test_data_path / "v1_example.amf")
    assert isinstance(amf, AcesMetadataFile)


def test_roundtrip_file_paths(aces_amf_examples_path):
    """Round-tripping a file with <file> elements produces no percent-encoding."""
    from aces_amf_lib.amf_utilities import dump_amf
    amf_path = aces_amf_examples_path / "example5.amf"
    amf = load_amf(amf_path)
    xml_out = dump_amf(amf)
    # The file element value should be plain text, not percent-encoded
    assert "showLook.clf" in xml_out
    assert "%2F" not in xml_out
    assert "%25" not in xml_out


# --- workingLocation interleaving tests ---


def test_working_location_ordering_preserved(test_data_path):
    """Loading an AMF with interleaved workingLocation/lookTransform preserves order."""
    from aces_amf_lib.amf_v2 import WorkingLocationType, LookTransformType

    amf = load_amf(test_data_path / "interleaved_working_location.amf", validate=False)
    items = amf.pipeline.working_location_or_look_transform

    # Should be: lookTransform, workingLocation, lookTransform
    assert len(items) == 3
    assert isinstance(items[0], LookTransformType)
    assert isinstance(items[1], WorkingLocationType)
    assert isinstance(items[2], LookTransformType)

    # First look is pre-working-location, second is post
    assert items[0].description == "Pre-working-location look"
    assert items[2].description == "Post-working-location look"


def test_working_location_roundtrip(test_data_path, tmp_path):
    """Round-trip preserves workingLocation/lookTransform ordering."""
    from aces_amf_lib.amf_v2 import WorkingLocationType, LookTransformType

    amf = load_amf(test_data_path / "interleaved_working_location.amf", validate=False)
    out_path = tmp_path / "roundtrip.amf"
    save_amf(amf, out_path, validate=False)

    amf2 = load_amf(out_path, validate=False)
    items = amf2.pipeline.working_location_or_look_transform

    assert len(items) == 3
    assert isinstance(items[0], LookTransformType)
    assert isinstance(items[1], WorkingLocationType)
    assert isinstance(items[2], LookTransformType)


def test_look_transforms_property_filters(test_data_path):
    """pipeline.look_transforms returns only LookTransformType items."""
    amf = load_amf(test_data_path / "interleaved_working_location.amf", validate=False)

    # Full list has 3 items (2 looks + 1 working location)
    assert len(amf.pipeline.working_location_or_look_transform) == 3
    # Property filters to just look transforms
    assert len(amf.pipeline.look_transforms) == 2
    assert amf.pipeline.look_transforms[0].description == "Pre-working-location look"
    assert amf.pipeline.look_transforms[1].description == "Post-working-location look"


def test_v1_upgrade_look_transforms_preserved(test_data_path):
    """v1→v2 upgrade preserves lookTransform in the compound field."""
    amf = load_amf(test_data_path / "v1_example.amf")
    # v1 lookTransform should end up in working_location_or_look_transform
    assert len(amf.pipeline.look_transforms) == 1
    assert amf.pipeline.look_transforms[0].file == "showLook.clf"
