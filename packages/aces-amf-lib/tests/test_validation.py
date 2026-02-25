# SPDX-License-Identifier: Apache-2.0
"""Tests for XSD schema validation."""

from pathlib import Path

import pytest

from aces_amf_lib.validation import validate_schema, ValidationType


@pytest.mark.parametrize(
    "amf_subpath",
    [
        Path("aces-examples") / "example1.amf",
        Path("aces-examples") / "example6.amf",
        Path("aces-examples") / "exampleMinimum.amf",
    ],
)
def test_amf_validation_pos(amf_subpath, test_data_path):
    amf_path = test_data_path / amf_subpath
    assert isinstance(validate_schema(amf_path), list)
    assert len(validate_schema(amf_path)) == 0


def test_amf_validation_neg_syntax(tmp_path):
    """Test validation rejects non-XML file."""
    bad_file = tmp_path / "bad.amf"
    bad_file.write_text("this is not xml")
    result = validate_schema(bad_file)
    assert len(result) == 1
    assert result[0].validation_type == ValidationType.SCHEMA_VIOLATION


def test_backward_compat_validate_amf():
    """Test that the old validate_amf import still works."""
    from aces_amf_lib import validate_amf
    assert validate_amf is validate_schema
