# SPDX-License-Identifier: Apache-2.0
"""Tests for the public AMF API (load, save, render, minimal_amf)."""

import time

import pytest

from aces_amf_lib import (
    load_amf,
    load_amf_data,
    save_amf,
    render_amf,
)
from aces_amf_utils.factories import cdl_look_transform, minimal_amf, prepare_for_write
from aces_amf_lib import amf_v2
from aces_amf_lib.amf_v2 import AcesMetadataFile, VersionType
from aces_amf_lib.validation import validate_schema


def test_load_amf_v2(aces_amf_examples_path):
    """Test loading a v2 AMF file."""
    amf_path = aces_amf_examples_path / "example6.amf"
    amf = load_amf(amf_path, validate=False)
    assert isinstance(amf, AcesMetadataFile)
    assert amf.amf_info.uuid == "urn:uuid:afe122be-59d3-4360-ad69-33c10108fa7a"


def test_load_amf_data(aces_amf_examples_path):
    """Test loading AMF from bytes."""
    amf_path = aces_amf_examples_path / "example6.amf"
    with amf_path.open("rb") as f:
        amf = load_amf_data(f.read(), validate=False)
    assert amf.amf_info.uuid == "urn:uuid:afe122be-59d3-4360-ad69-33c10108fa7a"


def test_render_amf(aces_amf_examples_path):
    amf_path = aces_amf_examples_path / "example6.amf"
    amf = load_amf(amf_path, validate=False)
    dumped = render_amf(amf, validate=False)

    assert isinstance(dumped, str)
    assert "<aces:amfInfo>" in dumped
    assert "<aces:uuid>" in dumped
    # Verify actual data survives the render (not just tags)
    assert amf.pipeline is not None
    assert "urn:ampas:aces:amf:v2.0" in dumped


def test_save_amf(aces_amf_examples_path, tmp_path):
    amf_path = aces_amf_examples_path / "example6.amf"
    amf = load_amf(amf_path, validate=False)

    out_path = tmp_path / "out.amf"
    save_amf(amf, out_path, validate=False)

    out_data = out_path.read_text()
    assert "<aces:amfInfo>" in out_data
    assert "<aces:uuid>" in out_data


def test_create_minimal(tmp_path):
    amf = minimal_amf()
    out_path = tmp_path / "out.amf"
    save_amf(amf, out_path, validate=False)

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
    save_amf(amf, out_path, validate=False)

    validation_messages = validate_schema(out_path)
    assert not validation_messages


def test_housekeeping_updates(tmp_path):
    amf = minimal_amf()
    out_path = tmp_path / "minimal.amf"
    save_amf(amf, out_path, validate=False)

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
    save_amf(amf, out_path_updated, validate=False)

    original = load_amf(out_path, validate=False)
    updated = load_amf(out_path_updated, validate=False)

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
    amf = load_amf(amf_path, validate=False)

    out_path = tmp_path / "roundtrip.amf"
    save_amf(amf, out_path, validate=False)

    # Validate the output
    validation_messages = validate_schema(out_path)
    assert not validation_messages

    # Load back and verify
    amf2 = load_amf(out_path, validate=False)
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
    amf = load_amf(test_data_path / "v1_example.amf", validate=False)
    assert isinstance(amf, AcesMetadataFile)
    # UUIDs should be generated (not present in v1 fixture)
    assert amf.amf_info.uuid is not None
    assert amf.amf_info.uuid.startswith("urn:uuid:")
    assert amf.pipeline.pipeline_info.uuid is not None
    assert amf.pipeline.pipeline_info.uuid.startswith("urn:uuid:")


def test_load_amf_v1_output_transform_applied(test_data_path):
    """v1 outputTransform (no applied attr) gets applied=False after upgrade."""
    amf = load_amf(test_data_path / "v1_example.amf", validate=False)
    assert amf.pipeline.output_transform is not None
    assert amf.pipeline.output_transform.applied is False


def test_load_amf_v1_file_field_preserved(test_data_path):
    """file field stays as str (not converted to list) after v1→v2 upgrade."""
    amf = load_amf(test_data_path / "v1_example.amf", validate=False)
    look = amf.pipeline.look_transforms[0]
    assert look.file == "showLook.clf"
    assert isinstance(look.file, str)


# --- Auto-validation tests ---


def test_load_validates_by_default(aces_amf_examples_path, transform_registry):
    """Valid AMF files load without raising when registry provided."""
    amf = load_amf(aces_amf_examples_path / "example6.amf", transform_registry=transform_registry)
    assert amf is not None


def test_load_no_registry_raises(aces_amf_examples_path):
    """load_amf with validate=True and no registry raises RegistryNotConfiguredError."""
    from aces_amf_lib.validation.types import RegistryNotConfiguredError
    with pytest.raises(RegistryNotConfiguredError):
        load_amf(aces_amf_examples_path / "example6.amf")


def test_load_skip_validation(aces_amf_examples_path):
    """validate=False skips validation entirely."""
    amf = load_amf(aces_amf_examples_path / "example6.amf", validate=False)
    assert amf is not None


def test_save_validates_by_default(tmp_path, transform_registry):
    """Valid AMF saves without raising when registry provided."""
    amf = minimal_amf()
    out = tmp_path / "valid.amf"
    save_amf(amf, out, transform_registry=transform_registry)
    assert out.exists()


def test_save_raises_on_invalid(tmp_path, transform_registry):
    """save_amf with validate=True raises on ERROR-level issues."""
    from aces_amf_lib.validation.types import AMFValidationError

    amf = minimal_amf()
    amf.pipeline.working_location_or_look_transform.append(
        cdl_look_transform(slope=(-1.0, 1.0, 1.0))
    )
    out = tmp_path / "invalid.amf"
    with pytest.raises(AMFValidationError):
        save_amf(amf, out, transform_registry=transform_registry)


def test_save_skip_validation(tmp_path):
    """validate=False allows saving invalid AMF without error."""
    amf = minimal_amf()
    amf.pipeline.working_location_or_look_transform.append(
        cdl_look_transform(slope=(-1.0, 1.0, 1.0))
    )
    out = tmp_path / "invalid.amf"
    save_amf(amf, out, validate=False)
    assert out.exists()


def test_v1_upgrade_validates(test_data_path, transform_registry):
    """v1→v2 upgrade runs semantic validation on the upgraded model."""
    amf = load_amf(test_data_path / "v1_example.amf", transform_registry=transform_registry)
    assert isinstance(amf, AcesMetadataFile)


def test_roundtrip_file_paths(aces_amf_examples_path):
    """Round-tripping a file with <file> elements produces no percent-encoding."""
    from aces_amf_lib.amf_helpers import dump_amf
    amf_path = aces_amf_examples_path / "example5.amf"
    amf = load_amf(amf_path, validate=False)
    xml_out = dump_amf(amf)
    # The file element value should be plain text, not percent-encoded
    assert "showLook.clf" in xml_out
    assert "%2F" not in xml_out
    assert "%25" not in xml_out


# --- URI encoding/decoding tests ---


_AMF_WITH_ENCODED_PATH = """\
<?xml version="1.0" encoding="UTF-8"?>
<acesMetadataFile xmlns="urn:ampas:aces:amf:v2.0" version="2.0"
  xmlns:cdl="urn:ASC:CDL:v1.01">
  <amfInfo>
    <dateTime>
      <creationDateTime>2024-01-01T00:00:00Z</creationDateTime>
      <modificationDateTime>2024-01-01T00:00:00Z</modificationDateTime>
    </dateTime>
    <uuid>urn:uuid:11111111-1111-1111-1111-111111111111</uuid>
  </amfInfo>
  <pipeline>
    <pipelineInfo>
      <dateTime>
        <creationDateTime>2024-01-01T00:00:00Z</creationDateTime>
        <modificationDateTime>2024-01-01T00:00:00Z</modificationDateTime>
      </dateTime>
      <uuid>urn:uuid:22222222-2222-2222-2222-222222222222</uuid>
      <systemVersion>
        <majorVersion>1</majorVersion>
        <minorVersion>3</minorVersion>
        <patchVersion>0</patchVersion>
      </systemVersion>
    </pipelineInfo>
    <inputTransform applied="false">
      <file>my%20show/Camera%20Files/A001.clf</file>
    </inputTransform>
  </pipeline>
</acesMetadataFile>"""


def test_load_decodes_percent_encoded_file_paths():
    """Percent-encoded file paths are decoded to human-readable form on load."""
    amf = load_amf_data(_AMF_WITH_ENCODED_PATH.encode(), validate=False)
    assert amf.pipeline.input_transform.file == "my show/Camera Files/A001.clf"


def test_save_encodes_file_paths_to_valid_uris(tmp_path):
    """File paths with spaces are percent-encoded in serialized XML."""
    from aces_amf_lib.amf_helpers import dump_amf
    amf = load_amf_data(_AMF_WITH_ENCODED_PATH.encode(), validate=False)
    # In-memory should be decoded
    assert amf.pipeline.input_transform.file == "my show/Camera Files/A001.clf"
    # Serialized should be re-encoded
    xml_out = dump_amf(amf)
    assert "my%20show/Camera%20Files/A001.clf" in xml_out


def test_roundtrip_preserves_plain_paths(aces_amf_examples_path):
    """Plain paths with no special characters survive round-trip unchanged."""
    from aces_amf_lib.amf_helpers import dump_amf
    amf = load_amf(aces_amf_examples_path / "example5.amf", validate=False)
    # Second look is file-based (first is CDL)
    assert amf.pipeline.look_transforms[1].file == "showLook.clf"
    xml_out = dump_amf(amf)
    assert "showLook.clf" in xml_out


def test_roundtrip_encoded_paths():
    """Encoded input -> decoded in memory -> re-encoded on save."""
    from aces_amf_lib.amf_helpers import dump_amf
    amf = load_amf_data(_AMF_WITH_ENCODED_PATH.encode(), validate=False)
    xml_out = dump_amf(amf)
    assert "my%20show/Camera%20Files/A001.clf" in xml_out
    # Forward slashes must NOT be encoded
    assert "%2F" not in xml_out


def test_decode_does_not_double_decode():
    """Already-decoded paths (no percent chars) pass through unchanged."""
    amf = load_amf_data(_AMF_WITH_ENCODED_PATH.encode(), validate=False)
    # After decode, path should be clean
    assert amf.pipeline.input_transform.file == "my show/Camera Files/A001.clf"
    # Loading again from XML that has no encoding should also work fine
    amf2 = minimal_amf()
    amf2.pipeline.input_transform = amf_v2.InputTransformType(
        file="plain_file.clf", applied=False,
    )
    from aces_amf_lib.amf_helpers import dump_amf
    xml_out = dump_amf(amf2)
    assert "plain_file.clf" in xml_out


def test_encode_does_not_mutate_original():
    """dump_amf does not alter the in-memory model's file paths."""
    from aces_amf_lib.amf_helpers import dump_amf
    amf = load_amf_data(_AMF_WITH_ENCODED_PATH.encode(), validate=False)
    original_path = amf.pipeline.input_transform.file
    dump_amf(amf)  # should deep-copy internally
    assert amf.pipeline.input_transform.file == original_path
    assert amf.pipeline.input_transform.file == "my show/Camera Files/A001.clf"


def test_clip_id_file_uri_roundtrip(tmp_path):
    """ClipIdType.file is decoded on load and encoded on save."""
    from aces_amf_lib.amf_helpers import dump_amf
    amf = minimal_amf()
    amf.clip_id = amf_v2.ClipIdType(clip_name="A001", file="my show/A001.ari")
    xml_out = dump_amf(amf)
    assert "my%20show/A001.ari" in xml_out
    # Round-trip: save then reload
    out = tmp_path / "clip_uri.amf"
    save_amf(amf, out, validate=False)
    loaded = load_amf(out, validate=False)
    assert loaded.clip_id.file == "my show/A001.ari"


def test_nested_output_transform_file_uri():
    """File fields nested inside OutputTransformType are encoded/decoded."""
    from aces_amf_lib.amf_helpers import dump_amf
    amf = minimal_amf()
    amf.pipeline.output_transform = amf_v2.OutputTransformType(
        applied=False,
        reference_rendering_transform=amf_v2.ReferenceRenderingTransformType(
            file="path with spaces/rrt.clf",
        ),
        output_device_transform=amf_v2.OutputDeviceTransformType(
            file="path with spaces/odt.clf",
        ),
    )
    xml_out = dump_amf(amf)
    assert "path%20with%20spaces/rrt.clf" in xml_out
    assert "path%20with%20spaces/odt.clf" in xml_out


_V1_AMF_WITH_ENCODED_PATH = """\
<?xml version="1.0" encoding="UTF-8"?>
<aces:acesMetadataFile xmlns:aces="urn:ampas:aces:amf:v1.0"
  xmlns:cdl="urn:ASC:CDL:v1.01" version="1.0">
  <aces:amfInfo>
    <aces:dateTime>
      <aces:creationDateTime>2024-01-01T00:00:00Z</aces:creationDateTime>
      <aces:modificationDateTime>2024-01-01T00:00:00Z</aces:modificationDateTime>
    </aces:dateTime>
  </aces:amfInfo>
  <aces:pipeline>
    <aces:pipelineInfo>
      <aces:dateTime>
        <aces:creationDateTime>2024-01-01T00:00:00Z</aces:creationDateTime>
        <aces:modificationDateTime>2024-01-01T00:00:00Z</aces:modificationDateTime>
      </aces:dateTime>
      <aces:systemVersion>
        <aces:majorVersion>1</aces:majorVersion>
        <aces:minorVersion>3</aces:minorVersion>
        <aces:patchVersion>0</aces:patchVersion>
      </aces:systemVersion>
    </aces:pipelineInfo>
    <aces:lookTransform applied="true">
      <aces:file>my%20show/look%20grade.clf</aces:file>
    </aces:lookTransform>
    <aces:outputTransform>
      <aces:referenceRenderingTransform>
        <aces:transformId>urn:ampas:aces:transformId:v1.5:RRTODT.Academy.P3D65_108nits_7.2nits_ST2084.a1.1.0</aces:transformId>
      </aces:referenceRenderingTransform>
    </aces:outputTransform>
  </aces:pipeline>
</aces:acesMetadataFile>"""


def test_v1_with_encoded_file_paths():
    """V1→V2 upgrade decodes percent-encoded file paths."""
    amf = load_amf_data(_V1_AMF_WITH_ENCODED_PATH.encode(), validate=False)
    assert amf.pipeline.look_transforms[0].file == "my show/look grade.clf"


def test_render_amf_encodes_file_paths():
    """render_amf() encodes file paths just like dump_amf()."""
    amf = load_amf_data(_AMF_WITH_ENCODED_PATH.encode(), validate=False)
    xml_out = render_amf(amf, validate=False)
    assert "my%20show/Camera%20Files/A001.clf" in xml_out


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
    amf = load_amf(test_data_path / "v1_example.amf", validate=False)
    # v1 lookTransform should end up in working_location_or_look_transform
    assert len(amf.pipeline.look_transforms) == 1
    assert amf.pipeline.look_transforms[0].file == "showLook.clf"


_V1_AMF_NO_SYSTEM_VERSION = """\
<?xml version="1.0" encoding="UTF-8"?>
<aces:acesMetadataFile xmlns:aces="urn:ampas:aces:amf:v1.0"
  xmlns:cdl="urn:ASC:CDL:v1.01" version="1.0">
  <aces:amfInfo>
    <aces:dateTime>
      <aces:creationDateTime>2024-01-01T00:00:00Z</aces:creationDateTime>
      <aces:modificationDateTime>2024-01-01T00:00:00Z</aces:modificationDateTime>
    </aces:dateTime>
  </aces:amfInfo>
  <aces:pipeline>
    <aces:pipelineInfo>
      <aces:dateTime>
        <aces:creationDateTime>2024-01-01T00:00:00Z</aces:creationDateTime>
        <aces:modificationDateTime>2024-01-01T00:00:00Z</aces:modificationDateTime>
      </aces:dateTime>
    </aces:pipelineInfo>
    <aces:outputTransform>
      <aces:referenceRenderingTransform>
        <aces:transformId>urn:ampas:aces:transformId:v1.5:RRTODT.Academy.P3D65_108nits_7.2nits_ST2084.a1.1.0</aces:transformId>
      </aces:referenceRenderingTransform>
    </aces:outputTransform>
  </aces:pipeline>
</aces:acesMetadataFile>"""


def test_v1_missing_system_version():
    """Legacy v1 files without systemVersion get a default during upgrade."""
    amf = load_amf_data(_V1_AMF_NO_SYSTEM_VERSION.encode(), validate=False)
    assert isinstance(amf, AcesMetadataFile)
    sv = amf.pipeline.pipeline_info.system_version
    assert sv is not None
    assert (int(sv.major_version), int(sv.minor_version), int(sv.patch_version)) == (1, 3, 0)
