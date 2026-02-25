# SPDX-License-Identifier: Apache-2.0
"""Tests for XSD schema validation."""

from pathlib import Path

import pytest

from aces_amf_lib import validation


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
    assert isinstance(validation.validate_amf(amf_path), list)
    assert len(validation.validate_amf(amf_path)) == 0


def test_amf_validation_neg_syntax(tmp_path):
    """Test validation rejects non-XML file."""
    bad_file = tmp_path / "bad.amf"
    bad_file.write_text("this is not xml")
    result = validation.validate_amf(bad_file)
    assert len(result) == 1
    assert result[0].validation_type == validation.ValidationType.SCHEMA_VIOLATION
