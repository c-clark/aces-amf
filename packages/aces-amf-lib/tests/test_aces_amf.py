# SPDX-License-Identifier: Apache-2.0
"""Tests for the ACESAMF high-level class."""

import time

import pytest

from aces_amf_lib import ACESAMF
from aces_amf_lib.validation import validate_schema

from conftest import TEST_DATA_DIR


def test_amf_from_file_v2(aces_amf_examples_path):
    """Test loading a v2 AMF file."""
    amf_path = aces_amf_examples_path / "example6.amf"
    amf_obj = ACESAMF.from_file(amf_path)
    assert amf_obj.amf.amf_info.uuid == "urn:uuid:afe122be-59d3-4360-ad69-33c10108fa7a"
    assert len(amf_obj.ns_map) == 3


def test_amf_from_data(aces_amf_examples_path):
    """Test loading AMF from bytes."""
    amf_path = aces_amf_examples_path / "example6.amf"
    with amf_path.open("rb") as amf_file:
        amf_obj = ACESAMF.from_data(amf_file.read())
    assert amf_obj.amf.amf_info.uuid == "urn:uuid:afe122be-59d3-4360-ad69-33c10108fa7a"
    assert len(amf_obj.ns_map) == 3


def test_dump(aces_amf_examples_path):
    amf_path = aces_amf_examples_path / "example6.amf"
    amf_obj = ACESAMF.from_file(amf_path)
    dumped = amf_obj.dump()

    original_uuid = amf_obj.amf.amf_info.uuid
    assert "<aces:amfInfo>" in dumped
    assert f"<aces:uuid>{original_uuid}" in dumped


def test_write(aces_amf_examples_path, tmp_path):
    amf_path = aces_amf_examples_path / "example6.amf"
    amf_obj = ACESAMF.from_file(amf_path)
    original_uuid = amf_obj.amf.amf_info.uuid

    out_path = tmp_path / "out.amf"
    amf_obj.write(out_path)

    with open(out_path, "r") as out_file:
        out_data = out_file.read()

    assert "<aces:amfInfo>" in out_data
    assert f"<aces:uuid>{original_uuid}" in out_data


def test_create_minimal(tmp_path):
    amf = ACESAMF()
    out_path = tmp_path / "out.amf"
    amf.write(out_path)

    validation_messages = validate_schema(out_path)
    assert not validation_messages


def test_create_with_cdl(tmp_path):
    amf = ACESAMF()
    amf.add_cdl_look_transform(
        {
            "asc_sop": {
                "slope": [1.0, 1.0, 1.0],
                "offset": [0.0, 0.0, 0.0],
                "power": [1.0, 1.0, 1.0],
            },
            "asc_sat": 1.0,
        }
    )

    out_path = tmp_path / "out.amf"
    amf.write(out_path)

    validation_messages = validate_schema(out_path)
    assert not validation_messages


def test_dirty_flag_housekeeping(tmp_path):
    amf = ACESAMF()
    out_path = tmp_path / "minimal.amf"
    amf.write(out_path)

    time.sleep(1.00)

    amf.add_cdl_look_transform(
        {
            "asc_sop": {
                "slope": [1.0, 1.0, 1.0],
                "offset": [0.0, 0.0, 0.0],
                "power": [1.0, 1.0, 1.0],
            },
            "asc_sat": 1.0,
        }
    )

    out_path_updated = tmp_path / "updated_with_cdl.amf"
    amf.write(out_path_updated)

    original_amf = ACESAMF.from_file(out_path)
    updated_amf = ACESAMF.from_file(out_path_updated)

    assert original_amf.amf.amf_info.uuid != updated_amf.amf.amf_info.uuid
    assert original_amf.amf.amf_info.date_time.creation_date_time == updated_amf.amf.amf_info.date_time.creation_date_time
    assert original_amf.amf.amf_info.date_time.modification_date_time != updated_amf.amf.amf_info.date_time.modification_date_time

    assert original_amf.amf.pipeline.pipeline_info.uuid != updated_amf.amf.pipeline.pipeline_info.uuid


def test_amf_housekeeping_updates_with_fresh_amf():
    """Make sure the rev_up method works on a freshly created AMF"""
    amf = ACESAMF()
    amf.rev_up(force=True)
    amf_data = amf.dump()
    assert amf_data
    assert "<aces:amfInfo>" in amf_data
    assert "<aces:pipeline>" in amf_data


def test_roundtrip(aces_amf_examples_path, tmp_path):
    """Test round-trip: load -> write -> validate -> load."""
    amf_path = aces_amf_examples_path / "example6.amf"
    amf_obj = ACESAMF.from_file(amf_path)

    out_path = tmp_path / "roundtrip.amf"
    amf_obj.write(out_path)

    # Validate the output
    validation_messages = validate_schema(out_path)
    assert not validation_messages

    # Load back and verify
    amf_obj2 = ACESAMF.from_file(out_path)
    assert amf_obj2.amf.pipeline is not None
    assert len(amf_obj2.amf.pipeline.look_transform) == len(amf_obj.amf.pipeline.look_transform)


def test_set_aces_version():
    amf = ACESAMF()
    amf.set_aces_version(2, 0, 0)
    assert amf.aces_version == (2, 0, 0)
    assert amf.aces_major_version == 2
