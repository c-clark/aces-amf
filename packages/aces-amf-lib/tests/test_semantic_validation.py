# SPDX-License-Identifier: Apache-2.0
"""Tests for semantic validation module."""

import pytest
from pathlib import Path

from aces_amf_lib import ACESAMF
from aces_amf_lib.validation import (
    validate_semantic,
    get_default_registry,
    ValidationContext,
    ValidationLevel,
    ValidationMessage,
    ValidationType,
)
from aces_amf_lib import amf_v2


@pytest.fixture
def temp_amf_file(tmp_path):
    """Create a temporary AMF file for testing."""
    amf = ACESAMF()
    amf.amf_description = "Test AMF"
    amf.pipeline_description = "Test Pipeline"

    author = amf_v2.AuthorType(name="Test Author", email_address="test@example.com")
    amf.add_amf_author(author)

    amf_path = tmp_path / "test.amf"
    amf.write(amf_path)
    return amf_path


class TestValidatorRegistry:
    def test_default_registry_has_core_validators(self):
        registry = get_default_registry()
        names = registry.validator_names
        assert "temporal" in names
        assert "uuid" in names
        assert "cdl" in names
        assert "metadata" in names
        assert "applied_order" in names
        assert "file_paths" in names
        assert "working_space" in names
        assert "transform_ids" in names
        assert "file_hashes" in names

    def test_validate_minimal_amf(self, temp_amf_file):
        messages = validate_semantic(temp_amf_file)
        errors = [m for m in messages if m.level == ValidationLevel.ERROR]
        assert len(errors) == 0

    def test_validate_with_specific_validators(self, temp_amf_file):
        messages = validate_semantic(temp_amf_file, validators=["temporal", "uuid"])
        # Only temporal and uuid validators should have run
        for msg in messages:
            assert msg.validator_name in ("temporal", "uuid")

    def test_validate_with_exclude(self, temp_amf_file):
        messages = validate_semantic(temp_amf_file, exclude=["metadata"])
        for msg in messages:
            assert msg.validator_name != "metadata"

    def test_validate_with_no_validators(self, temp_amf_file):
        messages = validate_semantic(temp_amf_file, validators=[])
        assert len(messages) == 0


class TestDateLogicValidation:
    def test_valid_dates(self, temp_amf_file):
        messages = validate_semantic(temp_amf_file, validators=["temporal"])
        date_errors = [m for m in messages if m.validation_type == ValidationType.INVALID_DATE_LOGIC]
        assert len(date_errors) == 0


class TestUUIDValidation:
    def test_unique_uuids(self, temp_amf_file):
        messages = validate_semantic(temp_amf_file, validators=["uuid"])
        uuid_errors = [m for m in messages if m.validation_type == ValidationType.DUPLICATE_UUID]
        assert len(uuid_errors) == 0

    def test_uuid_pool_tracking(self, tmp_path):
        amf1 = ACESAMF()
        amf1_path = tmp_path / "test1.amf"
        amf1.write(amf1_path)

        amf2 = ACESAMF()
        amf2_path = tmp_path / "test2.amf"
        amf2.write(amf2_path)

        uuid_pool = set()
        messages1 = validate_semantic(amf1_path, validators=["uuid"], uuid_pool=uuid_pool)
        messages2 = validate_semantic(amf2_path, validators=["uuid"], uuid_pool=uuid_pool)

        uuid_errors = [m for m in messages1 + messages2 if m.validation_type == ValidationType.DUPLICATE_UUID]
        assert len(uuid_errors) == 0


class TestCDLValidation:
    def test_valid_cdl(self, tmp_path):
        amf = ACESAMF()
        amf.add_cdl_look_transform({
            'asc_sop': {'slope': [1.2, 1.0, 0.8], 'offset': [0.0, 0.0, 0.0], 'power': [1.0, 1.0, 1.0]},
            'asc_sat': 1.05
        })
        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        messages = validate_semantic(amf_path, validators=["cdl"])
        cdl_errors = [m for m in messages if m.validation_type == ValidationType.CDL_INVALID_VALUES]
        assert len(cdl_errors) == 0

    def test_identity_cdl_info(self, tmp_path):
        amf = ACESAMF()
        amf.add_cdl_look_transform({
            'asc_sop': {'slope': [1.0, 1.0, 1.0], 'offset': [0.0, 0.0, 0.0], 'power': [1.0, 1.0, 1.0]},
            'asc_sat': 1.0
        })
        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        messages = validate_semantic(amf_path, validators=["cdl"])
        identity_info = [m for m in messages if m.validation_type == ValidationType.CDL_IDENTITY]
        assert len(identity_info) >= 1
        assert identity_info[0].level == ValidationLevel.INFO

    def test_negative_slope_error(self, tmp_path):
        amf = ACESAMF()
        amf.add_cdl_look_transform({
            'asc_sop': {'slope': [-1.0, 1.0, 1.0], 'offset': [0.0, 0.0, 0.0], 'power': [1.0, 1.0, 1.0]},
            'asc_sat': 1.0
        })
        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        messages = validate_semantic(amf_path, validators=["cdl"])
        slope_errors = [m for m in messages if m.validation_type == ValidationType.CDL_INVALID_VALUES and "slope" in m.message]
        assert len(slope_errors) >= 1
        assert slope_errors[0].level == ValidationLevel.ERROR

    def test_extreme_slope_warning(self, tmp_path):
        amf = ACESAMF()
        amf.add_cdl_look_transform({
            'asc_sop': {'slope': [10.0, 1.0, 1.0], 'offset': [0.0, 0.0, 0.0], 'power': [1.0, 1.0, 1.0]},
            'asc_sat': 1.0
        })
        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        messages = validate_semantic(amf_path, validators=["cdl"])
        extreme_warnings = [m for m in messages if m.validation_type == ValidationType.CDL_EXTREME_VALUES and "slope" in m.message]
        assert len(extreme_warnings) >= 1
        assert extreme_warnings[0].level == ValidationLevel.WARNING

    def test_negative_saturation_error(self, tmp_path):
        amf = ACESAMF()
        amf.add_cdl_look_transform({
            'asc_sop': {'slope': [1.0, 1.0, 1.0], 'offset': [0.0, 0.0, 0.0], 'power': [1.0, 1.0, 1.0]},
            'asc_sat': -0.5
        })
        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        messages = validate_semantic(amf_path, validators=["cdl"])
        sat_errors = [m for m in messages if m.validation_type == ValidationType.CDL_INVALID_VALUES and "saturation" in m.message]
        assert len(sat_errors) >= 1
        assert sat_errors[0].level == ValidationLevel.ERROR


class TestAppliedOrderValidation:
    def test_valid_all_applied(self, tmp_path):
        amf = ACESAMF()
        for _ in range(3):
            amf.add_cdl_look_transform({
                'asc_sop': {'slope': [1.0, 1.0, 1.0], 'offset': [0.0, 0.0, 0.0], 'power': [1.0, 1.0, 1.0]},
                'asc_sat': 1.0
            })
            amf.amf.pipeline.look_transform[-1].applied = True

        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        messages = validate_semantic(amf_path, validators=["applied_order"])
        order_errors = [m for m in messages if m.validation_type == ValidationType.INVALID_APPLIED_ORDER]
        assert len(order_errors) == 0

    def test_invalid_non_applied_then_applied(self, tmp_path):
        amf = ACESAMF()
        amf.add_cdl_look_transform({
            'asc_sop': {'slope': [1.0, 1.0, 1.0], 'offset': [0.0, 0.0, 0.0], 'power': [1.0, 1.0, 1.0]},
            'asc_sat': 1.0
        })
        amf.amf.pipeline.look_transform[-1].applied = False
        amf.amf.pipeline.look_transform[-1].description = "Non-applied First"

        amf.add_cdl_look_transform({
            'asc_sop': {'slope': [1.2, 1.0, 0.8], 'offset': [0.0, 0.0, 0.0], 'power': [1.0, 1.0, 1.0]},
            'asc_sat': 1.05
        })
        amf.amf.pipeline.look_transform[-1].applied = True
        amf.amf.pipeline.look_transform[-1].description = "Applied Second"

        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        messages = validate_semantic(amf_path, validators=["applied_order"])
        order_errors = [m for m in messages if m.validation_type == ValidationType.INVALID_APPLIED_ORDER]
        assert len(order_errors) == 1
        assert order_errors[0].level == ValidationLevel.ERROR
        assert "Applied Second" in order_errors[0].message


class TestMetadataValidation:
    def test_missing_description_warning(self, tmp_path):
        amf = ACESAMF()
        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        messages = validate_semantic(amf_path, validators=["metadata"])
        desc_warnings = [m for m in messages if m.validation_type == ValidationType.MISSING_DESCRIPTION]
        assert len(desc_warnings) >= 1
        assert desc_warnings[0].level == ValidationLevel.WARNING

    def test_missing_author_warning(self, tmp_path):
        amf = ACESAMF()
        amf.amf_description = "Test"
        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        messages = validate_semantic(amf_path, validators=["metadata"])
        author_warnings = [m for m in messages if m.validation_type == ValidationType.MISSING_AUTHOR]
        assert len(author_warnings) >= 1
        assert author_warnings[0].level == ValidationLevel.WARNING

    def test_complete_metadata(self, temp_amf_file):
        messages = validate_semantic(temp_amf_file, validators=["metadata"])
        author_warnings = [m for m in messages if m.validation_type == ValidationType.MISSING_AUTHOR]
        assert len(author_warnings) == 0


class TestFilePathValidation:
    def test_absolute_path_warning(self, tmp_path):
        amf = ACESAMF()
        amf.amf.pipeline.input_transform = amf_v2.InputTransformType(applied=True, file="/absolute/path/to/file.clf")

        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        messages = validate_semantic(amf_path, validators=["file_paths"])
        path_warnings = [m for m in messages if m.validation_type == ValidationType.NON_PORTABLE_PATH]
        assert len(path_warnings) >= 1
        assert "absolute path" in path_warnings[0].message.lower()

    def test_parent_directory_warning(self, tmp_path):
        amf = ACESAMF()
        amf.amf.pipeline.input_transform = amf_v2.InputTransformType(applied=True, file="../parent/file.clf")

        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        messages = validate_semantic(amf_path, validators=["file_paths"])
        path_warnings = [m for m in messages if m.validation_type == ValidationType.UNSAFE_FILE_PATH]
        assert len(path_warnings) >= 1
        assert ".." in path_warnings[0].message

    def test_relative_path_valid(self, tmp_path):
        amf = ACESAMF()
        amf.amf.pipeline.input_transform = amf_v2.InputTransformType(applied=True, file="relative/path/to/file.clf")

        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        messages = validate_semantic(amf_path, validators=["file_paths"])
        path_warnings = [m for m in messages if m.validation_type in [
            ValidationType.UNSAFE_FILE_PATH,
            ValidationType.NON_PORTABLE_PATH,
        ]]
        assert len(path_warnings) == 0


class TestConvenienceFunction:
    def test_convenience_function(self, temp_amf_file):
        messages = validate_semantic(temp_amf_file)
        assert isinstance(messages, list)
        errors = [m for m in messages if m.level == ValidationLevel.ERROR]
        assert len(errors) == 0


class TestValidationMessage:
    def test_validation_message_string(self):
        msg = ValidationMessage(
            level=ValidationLevel.ERROR,
            validation_type=ValidationType.DUPLICATE_UUID,
            message="Test error message"
        )
        msg_str = str(msg)
        assert "ERROR" in msg_str
        assert "Test error message" in msg_str

    def test_validation_message_with_file_path(self):
        msg = ValidationMessage(
            level=ValidationLevel.WARNING,
            validation_type=ValidationType.MISSING_DESCRIPTION,
            message="Missing description",
            file_path=Path("/tmp/test.amf")
        )
        msg_str = str(msg)
        assert "WARNING" in msg_str
        assert "test.amf" in msg_str
