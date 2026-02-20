# SPDX-License-Identifier: Apache-2.0
"""Tests for semantic validation module."""

import pytest
from pathlib import Path

from aces_amf_lib import ACESAMF
from aces_amf_lib.semantic_validation import (
    SemanticValidator,
    ValidationLevel,
    SemanticValidationType,
    SemanticValidationMessage,
    validate_semantic,
)
from aces_amf_lib import amf_v2


@pytest.fixture
def temp_amf_file(tmp_path):
    """Create a temporary AMF file for testing."""
    amf = ACESAMF()
    amf.amf_description = "Test AMF"
    amf.pipeline_description = "Test Pipeline"

    author = amf_v2.AuthorType()
    author.name = "Test Author"
    author.email_address = "test@example.com"
    amf.add_amf_author(author)

    amf_path = tmp_path / "test.amf"
    amf.write(amf_path)
    return amf_path


class TestSemanticValidator:
    def test_validator_initialization(self):
        validator = SemanticValidator()
        assert validator.base_path is None

        base_path = Path("/tmp")
        validator = SemanticValidator(base_path=base_path)
        assert validator.base_path == base_path

    def test_validate_minimal_amf(self, temp_amf_file):
        validator = SemanticValidator()
        messages = validator.validate(temp_amf_file)

        errors = [m for m in messages if m.level == ValidationLevel.ERROR]
        assert len(errors) == 0

    def test_validate_with_all_checks_disabled(self, temp_amf_file):
        validator = SemanticValidator()
        messages = validator.validate(
            temp_amf_file,
            check_dates=False,
            check_uuids=False,
            check_cdl=False,
            check_working_space=False,
            check_transform_ids=False,
            check_metadata=False,
            check_file_paths=False,
        )
        assert len(messages) == 0


class TestDateLogicValidation:
    def test_valid_dates(self, temp_amf_file):
        validator = SemanticValidator()
        messages = validator.validate(temp_amf_file, check_dates=True)
        date_errors = [m for m in messages if m.validation_type == SemanticValidationType.INVALID_DATE_LOGIC]
        assert len(date_errors) == 0


class TestUUIDValidation:
    def test_unique_uuids(self, temp_amf_file):
        validator = SemanticValidator()
        messages = validator.validate(temp_amf_file, check_uuids=True)
        uuid_errors = [m for m in messages if m.validation_type == SemanticValidationType.DUPLICATE_UUID]
        assert len(uuid_errors) == 0

    def test_uuid_pool_tracking(self, tmp_path):
        amf1 = ACESAMF()
        amf1_path = tmp_path / "test1.amf"
        amf1.write(amf1_path)

        amf2 = ACESAMF()
        amf2_path = tmp_path / "test2.amf"
        amf2.write(amf2_path)

        validator = SemanticValidator()
        uuid_pool = set()
        messages1 = validator.validate(amf1_path, check_uuids=True, uuid_pool=uuid_pool)
        messages2 = validator.validate(amf2_path, check_uuids=True, uuid_pool=uuid_pool)

        uuid_errors = [m for m in messages1 + messages2 if m.validation_type == SemanticValidationType.DUPLICATE_UUID]
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

        validator = SemanticValidator()
        messages = validator.validate(amf_path, check_cdl=True)
        cdl_errors = [m for m in messages if m.validation_type == SemanticValidationType.CDL_INVALID_VALUES]
        assert len(cdl_errors) == 0

    def test_identity_cdl_info(self, tmp_path):
        amf = ACESAMF()
        amf.add_cdl_look_transform({
            'asc_sop': {'slope': [1.0, 1.0, 1.0], 'offset': [0.0, 0.0, 0.0], 'power': [1.0, 1.0, 1.0]},
            'asc_sat': 1.0
        })
        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        validator = SemanticValidator()
        messages = validator.validate(amf_path, check_cdl=True)
        identity_info = [m for m in messages if m.validation_type == SemanticValidationType.CDL_IDENTITY]
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

        validator = SemanticValidator()
        messages = validator.validate(amf_path, check_cdl=True)
        slope_errors = [m for m in messages if m.validation_type == SemanticValidationType.CDL_INVALID_VALUES and "slope" in m.message]
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

        validator = SemanticValidator()
        messages = validator.validate(amf_path, check_cdl=True)
        extreme_warnings = [m for m in messages if m.validation_type == SemanticValidationType.CDL_EXTREME_VALUES and "slope" in m.message]
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

        validator = SemanticValidator()
        messages = validator.validate(amf_path, check_cdl=True)
        sat_errors = [m for m in messages if m.validation_type == SemanticValidationType.CDL_INVALID_VALUES and "saturation" in m.message]
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

        validator = SemanticValidator()
        messages = validator.validate(amf_path, check_applied_order=True)
        order_errors = [m for m in messages if m.validation_type == SemanticValidationType.INVALID_APPLIED_ORDER]
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

        validator = SemanticValidator()
        messages = validator.validate(amf_path, check_applied_order=True)
        order_errors = [m for m in messages if m.validation_type == SemanticValidationType.INVALID_APPLIED_ORDER]
        assert len(order_errors) == 1
        assert order_errors[0].level == ValidationLevel.ERROR
        assert "Applied Second" in order_errors[0].message


class TestMetadataValidation:
    def test_missing_description_warning(self, tmp_path):
        amf = ACESAMF()
        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        validator = SemanticValidator()
        messages = validator.validate(amf_path, check_metadata=True)
        desc_warnings = [m for m in messages if m.validation_type == SemanticValidationType.MISSING_DESCRIPTION]
        assert len(desc_warnings) >= 1
        assert desc_warnings[0].level == ValidationLevel.WARNING

    def test_missing_author_warning(self, tmp_path):
        amf = ACESAMF()
        amf.amf_description = "Test"
        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        validator = SemanticValidator()
        messages = validator.validate(amf_path, check_metadata=True)
        author_warnings = [m for m in messages if m.validation_type == SemanticValidationType.MISSING_AUTHOR]
        assert len(author_warnings) >= 1
        assert author_warnings[0].level == ValidationLevel.WARNING

    def test_complete_metadata(self, temp_amf_file):
        validator = SemanticValidator()
        messages = validator.validate(temp_amf_file, check_metadata=True)
        author_warnings = [m for m in messages if m.validation_type == SemanticValidationType.MISSING_AUTHOR]
        assert len(author_warnings) == 0


class TestFilePathValidation:
    def test_absolute_path_warning(self, tmp_path):
        amf = ACESAMF()
        amf.amf.pipeline.input_transform = amf_v2.InputTransformType()
        amf.amf.pipeline.input_transform.file = ["/absolute/path/to/file.clf"]

        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        validator = SemanticValidator()
        messages = validator.validate(amf_path, check_file_paths=True)
        path_warnings = [m for m in messages if m.validation_type == SemanticValidationType.NON_PORTABLE_PATH]
        assert len(path_warnings) >= 1
        assert "absolute path" in path_warnings[0].message.lower()

    def test_parent_directory_warning(self, tmp_path):
        amf = ACESAMF()
        amf.amf.pipeline.input_transform = amf_v2.InputTransformType()
        amf.amf.pipeline.input_transform.file = ["../parent/file.clf"]

        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        validator = SemanticValidator()
        messages = validator.validate(amf_path, check_file_paths=True)
        path_warnings = [m for m in messages if m.validation_type == SemanticValidationType.UNSAFE_FILE_PATH]
        assert len(path_warnings) >= 1
        assert ".." in path_warnings[0].message

    def test_relative_path_valid(self, tmp_path):
        amf = ACESAMF()
        amf.amf.pipeline.input_transform = amf_v2.InputTransformType()
        amf.amf.pipeline.input_transform.file = ["relative/path/to/file.clf"]

        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        validator = SemanticValidator()
        messages = validator.validate(amf_path, check_file_paths=True)
        path_warnings = [m for m in messages if m.validation_type in [
            SemanticValidationType.UNSAFE_FILE_PATH,
            SemanticValidationType.NON_PORTABLE_PATH,
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
        msg = SemanticValidationMessage(
            level=ValidationLevel.ERROR,
            validation_type=SemanticValidationType.DUPLICATE_UUID,
            message="Test error message"
        )
        msg_str = str(msg)
        assert "ERROR" in msg_str
        assert "Test error message" in msg_str

    def test_validation_message_with_file_path(self):
        msg = SemanticValidationMessage(
            level=ValidationLevel.WARNING,
            validation_type=SemanticValidationType.MISSING_DESCRIPTION,
            message="Missing description",
            file_path=Path("/tmp/test.amf")
        )
        msg_str = str(msg)
        assert "WARNING" in msg_str
        assert "test.amf" in msg_str
