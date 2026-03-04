# SPDX-License-Identifier: Apache-2.0
"""Tests for semantic validation module."""

import pytest
from pathlib import Path

from aces_amf_lib import minimal_amf, save_amf, load_amf, cdl_look_transform
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
    amf = minimal_amf()
    amf.amf_info.description = "Test AMF"
    amf.pipeline.pipeline_info.description = "Test Pipeline"
    amf.amf_info.author.append(amf_v2.AuthorType(name="Test Author", email_address="test@example.com"))

    amf_path = tmp_path / "test.amf"
    save_amf(amf, amf_path)
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
        amf1 = minimal_amf()
        amf1_path = tmp_path / "test1.amf"
        save_amf(amf1, amf1_path)

        amf2 = minimal_amf()
        amf2_path = tmp_path / "test2.amf"
        save_amf(amf2, amf2_path)

        uuid_pool = set()
        messages1 = validate_semantic(amf1_path, validators=["uuid"], uuid_pool=uuid_pool)
        messages2 = validate_semantic(amf2_path, validators=["uuid"], uuid_pool=uuid_pool)

        uuid_errors = [m for m in messages1 + messages2 if m.validation_type == ValidationType.DUPLICATE_UUID]
        assert len(uuid_errors) == 0


class TestCDLValidation:
    def test_valid_cdl(self, tmp_path):
        amf = minimal_amf()
        amf.pipeline.working_location_or_look_transform.append(cdl_look_transform(
            slope=(1.2, 1.0, 0.8), offset=(0.0, 0.0, 0.0), power=(1.0, 1.0, 1.0), saturation=1.05
        ))
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path)

        messages = validate_semantic(amf_path, validators=["cdl"])
        cdl_errors = [m for m in messages if m.validation_type == ValidationType.CDL_INVALID_VALUES]
        assert len(cdl_errors) == 0

    def test_identity_cdl_info(self, tmp_path):
        amf = minimal_amf()
        amf.pipeline.working_location_or_look_transform.append(cdl_look_transform(
            slope=(1.0, 1.0, 1.0), offset=(0.0, 0.0, 0.0), power=(1.0, 1.0, 1.0), saturation=1.0
        ))
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path)

        messages = validate_semantic(amf_path, validators=["cdl"])
        identity_info = [m for m in messages if m.validation_type == ValidationType.CDL_IDENTITY]
        assert len(identity_info) >= 1
        assert identity_info[0].level == ValidationLevel.INFO

    def test_negative_slope_error(self, tmp_path):
        amf = minimal_amf()
        amf.pipeline.working_location_or_look_transform.append(cdl_look_transform(
            slope=(-1.0, 1.0, 1.0), offset=(0.0, 0.0, 0.0), power=(1.0, 1.0, 1.0), saturation=1.0
        ))
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path, validate=False)

        messages = validate_semantic(amf_path, validators=["cdl"])
        slope_errors = [m for m in messages if m.validation_type == ValidationType.CDL_INVALID_VALUES and "slope" in m.message]
        assert len(slope_errors) >= 1
        assert slope_errors[0].level == ValidationLevel.ERROR

    def test_extreme_slope_warning(self, tmp_path):
        amf = minimal_amf()
        amf.pipeline.working_location_or_look_transform.append(cdl_look_transform(
            slope=(10.0, 1.0, 1.0), offset=(0.0, 0.0, 0.0), power=(1.0, 1.0, 1.0), saturation=1.0
        ))
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path)

        messages = validate_semantic(amf_path, validators=["cdl"])
        extreme_warnings = [m for m in messages if m.validation_type == ValidationType.CDL_EXTREME_VALUES and "slope" in m.message]
        assert len(extreme_warnings) >= 1
        assert extreme_warnings[0].level == ValidationLevel.WARNING

    def test_negative_saturation_error(self, tmp_path):
        amf = minimal_amf()
        amf.pipeline.working_location_or_look_transform.append(cdl_look_transform(
            slope=(1.0, 1.0, 1.0), offset=(0.0, 0.0, 0.0), power=(1.0, 1.0, 1.0), saturation=-0.5
        ))
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path, validate=False)

        messages = validate_semantic(amf_path, validators=["cdl"])
        sat_errors = [m for m in messages if m.validation_type == ValidationType.CDL_INVALID_VALUES and "saturation" in m.message]
        assert len(sat_errors) >= 1
        assert sat_errors[0].level == ValidationLevel.ERROR


class TestAppliedOrderValidation:
    def test_valid_all_applied(self, tmp_path):
        amf = minimal_amf()
        for _ in range(3):
            amf.pipeline.working_location_or_look_transform.append(cdl_look_transform(
                slope=(1.0, 1.0, 1.0), offset=(0.0, 0.0, 0.0), power=(1.0, 1.0, 1.0), saturation=1.0
            ))
            amf.pipeline.working_location_or_look_transform[-1].applied = True

        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path)

        messages = validate_semantic(amf_path, validators=["applied_order"])
        order_errors = [m for m in messages if m.validation_type == ValidationType.INVALID_APPLIED_ORDER]
        assert len(order_errors) == 0

    def test_invalid_non_applied_then_applied(self, tmp_path):
        amf = minimal_amf()
        amf.pipeline.working_location_or_look_transform.append(cdl_look_transform(
            slope=(1.0, 1.0, 1.0), offset=(0.0, 0.0, 0.0), power=(1.0, 1.0, 1.0), saturation=1.0
        ))
        amf.pipeline.working_location_or_look_transform[-1].applied = False
        amf.pipeline.working_location_or_look_transform[-1].description = "Non-applied First"

        amf.pipeline.working_location_or_look_transform.append(cdl_look_transform(
            slope=(1.2, 1.0, 0.8), offset=(0.0, 0.0, 0.0), power=(1.0, 1.0, 1.0), saturation=1.05
        ))
        amf.pipeline.working_location_or_look_transform[-1].applied = True
        amf.pipeline.working_location_or_look_transform[-1].description = "Applied Second"

        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path, validate=False)

        messages = validate_semantic(amf_path, validators=["applied_order"])
        order_errors = [m for m in messages if m.validation_type == ValidationType.INVALID_APPLIED_ORDER]
        assert len(order_errors) == 1
        assert order_errors[0].level == ValidationLevel.ERROR
        assert "Applied Second" in order_errors[0].message


class TestMetadataValidation:
    def test_missing_description_warning(self, tmp_path):
        amf = minimal_amf()
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path)

        messages = validate_semantic(amf_path, validators=["metadata"])
        desc_warnings = [m for m in messages if m.validation_type == ValidationType.MISSING_DESCRIPTION]
        assert len(desc_warnings) >= 1
        assert desc_warnings[0].level == ValidationLevel.WARNING

    def test_missing_author_warning(self, tmp_path):
        amf = minimal_amf()
        amf.amf_info.description = "Test"
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path)

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
        amf = minimal_amf()
        amf.pipeline.input_transform = amf_v2.InputTransformType(applied=True, file="/absolute/path/to/file.clf")

        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path)

        messages = validate_semantic(amf_path, validators=["file_paths"])
        path_warnings = [m for m in messages if m.validation_type == ValidationType.NON_PORTABLE_PATH]
        assert len(path_warnings) >= 1
        assert "absolute path" in path_warnings[0].message.lower()

    def test_parent_directory_warning(self, tmp_path):
        amf = minimal_amf()
        amf.pipeline.input_transform = amf_v2.InputTransformType(applied=True, file="../parent/file.clf")

        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path)

        messages = validate_semantic(amf_path, validators=["file_paths"])
        path_warnings = [m for m in messages if m.validation_type == ValidationType.UNSAFE_FILE_PATH]
        assert len(path_warnings) >= 1
        assert ".." in path_warnings[0].message

    def test_relative_path_valid(self, tmp_path):
        amf = minimal_amf()
        amf.pipeline.input_transform = amf_v2.InputTransformType(applied=True, file="relative/path/to/file.clf")

        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path)

        messages = validate_semantic(amf_path, validators=["file_paths"])
        path_warnings = [m for m in messages if m.validation_type in [
            ValidationType.UNSAFE_FILE_PATH,
            ValidationType.NON_PORTABLE_PATH,
        ]]
        assert len(path_warnings) == 0


class TestCDLBoundaryFixes:
    """Tests for CDL boundary check fixes (slope=0 and sat=0 are valid per XSD)."""

    def test_cdl_slope_zero_valid(self, tmp_path):
        """Slope=0 is valid per XSD (nonNegativeFloatType) — should be WARNING, not ERROR."""
        amf = minimal_amf()
        amf.pipeline.working_location_or_look_transform.append(cdl_look_transform(
            slope=(0.0, 1.0, 1.0), offset=(0.0, 0.0, 0.0), power=(1.0, 1.0, 1.0), saturation=1.0
        ))
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path)

        messages = validate_semantic(amf_path, validators=["cdl"])
        slope_errors = [m for m in messages if m.validation_type == ValidationType.CDL_INVALID_VALUES and "slope" in m.message]
        assert len(slope_errors) == 0, "slope=0 should not be an ERROR (valid per XSD)"

        slope_warnings = [m for m in messages if m.validation_type == ValidationType.CDL_EXTREME_VALUES and "slope" in m.message]
        assert len(slope_warnings) >= 1, "slope=0 should produce a WARNING"
        assert slope_warnings[0].level == ValidationLevel.WARNING

    def test_cdl_saturation_zero_valid(self, tmp_path):
        """Saturation=0 is valid per XSD (nonNegativeFloatType) — should be WARNING, not ERROR."""
        amf = minimal_amf()
        amf.pipeline.working_location_or_look_transform.append(cdl_look_transform(
            slope=(1.0, 1.0, 1.0), offset=(0.0, 0.0, 0.0), power=(1.0, 1.0, 1.0), saturation=0.0
        ))
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path)

        messages = validate_semantic(amf_path, validators=["cdl"])
        sat_errors = [m for m in messages if m.validation_type == ValidationType.CDL_INVALID_VALUES and "saturation" in m.message]
        assert len(sat_errors) == 0, "saturation=0 should not be an ERROR (valid per XSD)"

        sat_warnings = [m for m in messages if m.validation_type == ValidationType.CDL_EXTREME_VALUES and "saturation" in m.message]
        assert len(sat_warnings) >= 1, "saturation=0 should produce a WARNING"
        assert sat_warnings[0].level == ValidationLevel.WARNING

    def test_cdl_power_zero_error(self, tmp_path):
        """Power=0 is invalid per XSD (positiveFloatType, minExclusive=0) — should be ERROR."""
        amf = minimal_amf()
        amf.pipeline.working_location_or_look_transform.append(cdl_look_transform(
            slope=(1.0, 1.0, 1.0), offset=(0.0, 0.0, 0.0), power=(0.0, 1.0, 1.0), saturation=1.0
        ))
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path, validate=False)

        messages = validate_semantic(amf_path, validators=["cdl"])
        power_errors = [m for m in messages if m.validation_type == ValidationType.CDL_INVALID_VALUES and "power" in m.message]
        assert len(power_errors) >= 1, "power=0 should be an ERROR"
        assert power_errors[0].level == ValidationLevel.ERROR


class TestArchivedPipelineValidation:
    """Tests that all validators cover archived pipelines."""

    def _make_amf_with_archived(self, tmp_path, **overrides):
        """Create AMF with an archived pipeline containing a CDL look."""
        import uuid as uuid_mod
        amf = minimal_amf()
        amf.amf_info.description = "Test AMF"
        amf.amf_info.author.append(amf_v2.AuthorType(name="Test Author", email_address="test@example.com"))
        amf.pipeline.pipeline_info.description = "Active pipeline"

        archived_info = amf_v2.PipelineInfoType(
            date_time=amf.pipeline.pipeline_info.date_time,
            uuid=uuid_mod.uuid4().urn,
            system_version=amf_v2.VersionType(major_version=1, minor_version=3, patch_version=0),
            description="Archived pipeline",
        )
        archived = amf_v2.PipelineType(pipeline_info=archived_info, **overrides)
        amf.archived_pipeline.append(archived)

        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path)
        return amf_path

    def test_archived_cdl_validation(self, tmp_path):
        """CDL validator should catch errors in archived pipelines."""
        look = cdl_look_transform(
            slope=(-1.0, 1.0, 1.0), offset=(0.0, 0.0, 0.0), power=(1.0, 1.0, 1.0), saturation=1.0
        )
        look.description = "Bad CDL"
        amf_path = self._make_amf_with_archived(tmp_path)
        # Load, add look to archived, save
        amf = load_amf(amf_path)
        amf.archived_pipeline[0].working_location_or_look_transform.append(look)
        save_amf(amf, amf_path, validate=False)

        messages = validate_semantic(amf_path, validators=["cdl"])
        archived_errors = [m for m in messages if "Archived" in m.message and m.validation_type == ValidationType.CDL_INVALID_VALUES]
        assert len(archived_errors) >= 1

    def test_archived_applied_order_validation(self, tmp_path):
        """Applied order validator should catch errors in archived pipelines."""
        amf_path = self._make_amf_with_archived(tmp_path)
        amf = load_amf(amf_path)

        lt1 = cdl_look_transform()
        lt1.applied = False
        lt1.description = "Non-applied"
        lt2 = cdl_look_transform()
        lt2.applied = True
        lt2.description = "Applied after non-applied"
        amf.archived_pipeline[0].working_location_or_look_transform.extend([lt1, lt2])
        save_amf(amf, amf_path, validate=False)

        messages = validate_semantic(amf_path, validators=["applied_order"])
        archived_errors = [m for m in messages if "Archived" in m.message and m.validation_type == ValidationType.INVALID_APPLIED_ORDER]
        assert len(archived_errors) >= 1

    def test_archived_file_path_validation(self, tmp_path):
        """File path validator should catch issues in archived pipelines."""
        amf_path = self._make_amf_with_archived(tmp_path)
        amf = load_amf(amf_path)

        amf.archived_pipeline[0].input_transform = amf_v2.InputTransformType(
            applied=True, file="/absolute/bad.clf"
        )
        save_amf(amf, amf_path)

        messages = validate_semantic(amf_path, validators=["file_paths"])
        archived_warnings = [m for m in messages if "Archived" in m.message and m.validation_type == ValidationType.NON_PORTABLE_PATH]
        assert len(archived_warnings) >= 1

    def test_archived_metadata_validation(self, tmp_path):
        """Metadata validator should check archived pipeline descriptions."""
        import uuid as uuid_mod
        amf = minimal_amf()
        amf.amf_info.description = "Test AMF"
        amf.amf_info.author.append(amf_v2.AuthorType(name="Test Author", email_address="test@example.com"))
        amf.pipeline.pipeline_info.description = "Active pipeline"

        # Archived pipeline with no description
        archived_info = amf_v2.PipelineInfoType(
            date_time=amf.pipeline.pipeline_info.date_time,
            uuid=uuid_mod.uuid4().urn,
            system_version=amf_v2.VersionType(major_version=1, minor_version=3, patch_version=0),
        )
        archived = amf_v2.PipelineType(pipeline_info=archived_info)
        amf.archived_pipeline.append(archived)

        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path)

        messages = validate_semantic(amf_path, validators=["metadata"])
        archived_warnings = [m for m in messages if "Archived" in m.message and m.validation_type == ValidationType.MISSING_DESCRIPTION]
        assert len(archived_warnings) >= 1

    def test_archived_transform_ids_validation(self, tmp_path):
        """Transform ID validator should check archived pipeline transforms."""
        amf_path = self._make_amf_with_archived(tmp_path)
        amf = load_amf(amf_path)

        amf.archived_pipeline[0].input_transform = amf_v2.InputTransformType(
            applied=True, transform_id="bad-format-id"
        )
        save_amf(amf, amf_path, validate=False)

        messages = validate_semantic(amf_path, validators=["transform_ids"])
        archived_warnings = [m for m in messages if "Archived" in m.message and m.validation_type == ValidationType.INVALID_TRANSFORM_ID]
        assert len(archived_warnings) >= 1


class TestCDLAlternateFields:
    """Tests for CDL SOPNode/SatNode alternate element names."""

    def test_cdl_sopnode_alternate(self, tmp_path):
        """CDL validation should work with SOPNode/SatNode fields (not just ASC_SOP/ASC_SAT)."""
        amf = minimal_amf()
        lt = amf_v2.LookTransformType(
            sopnode=amf_v2.Sopnode(slope=[-1.0, 1.0, 1.0], offset=[0.0, 0.0, 0.0], power=[1.0, 1.0, 1.0]),
            sat_node=amf_v2.SatNode(saturation=1.0),
            cdl_working_space=amf_v2.CdlWorkingSpaceType(
                from_cdl_working_space=amf_v2.WorkingSpaceTransformType(
                    transform_id="urn:ampas:aces:transformId:v1.5:ACEScsc.Academy.ACEScct_to_ACES.a1.0.3"
                ),
            ),
            applied=False,
        )
        amf.pipeline.working_location_or_look_transform.append(lt)
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path, validate=False)

        messages = validate_semantic(amf_path, validators=["cdl"])
        slope_errors = [m for m in messages if m.validation_type == ValidationType.CDL_INVALID_VALUES and "slope" in m.message]
        assert len(slope_errors) >= 1, "CDL validator should catch invalid slope via SOPNode alternate"

    def test_cdl_identity_sopnode(self, tmp_path):
        """Identity detection should work with SOPNode/SatNode fields."""
        amf = minimal_amf()
        lt = amf_v2.LookTransformType(
            sopnode=amf_v2.Sopnode(slope=[1.0, 1.0, 1.0], offset=[0.0, 0.0, 0.0], power=[1.0, 1.0, 1.0]),
            sat_node=amf_v2.SatNode(saturation=1.0),
            cdl_working_space=amf_v2.CdlWorkingSpaceType(
                from_cdl_working_space=amf_v2.WorkingSpaceTransformType(
                    transform_id="urn:ampas:aces:transformId:v1.5:ACEScsc.Academy.ACEScct_to_ACES.a1.0.3"
                ),
            ),
            applied=False,
        )
        amf.pipeline.working_location_or_look_transform.append(lt)
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path)

        messages = validate_semantic(amf_path, validators=["cdl"])
        identity_msgs = [m for m in messages if m.validation_type == ValidationType.CDL_IDENTITY]
        assert len(identity_msgs) >= 1, "Identity detection should work via SOPNode/SatNode alternate"

    def test_color_correction_ref_without_file(self, tmp_path):
        """ColorCorrectionRef without a file element should produce a warning."""
        amf = minimal_amf()
        lt = amf_v2.LookTransformType(
            color_correction_ref=amf_v2.ColorCorrectionRef(ref="cc-001"),
            applied=False,
        )
        amf.pipeline.working_location_or_look_transform.append(lt)
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path, validate=False)

        messages = validate_semantic(amf_path, validators=["cdl"])
        ccr_msgs = [m for m in messages if m.validation_type == ValidationType.CDL_MISSING_CCR_FILE]
        assert len(ccr_msgs) == 1
        assert "ColorCorrectionRef" in ccr_msgs[0].message

    def test_color_correction_ref_with_file_no_warning(self, tmp_path):
        """ColorCorrectionRef WITH a file element should not produce a warning."""
        amf = minimal_amf()
        lt = amf_v2.LookTransformType(
            color_correction_ref=amf_v2.ColorCorrectionRef(ref="cc-001"),
            file="grades.ccc",
            applied=False,
        )
        amf.pipeline.working_location_or_look_transform.append(lt)
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path, validate=False)

        messages = validate_semantic(amf_path, validators=["cdl"])
        ccr_msgs = [m for m in messages if m.validation_type == ValidationType.CDL_MISSING_CCR_FILE]
        assert len(ccr_msgs) == 0


class TestNestedSubTransforms:
    """Tests for validation of nested sub-transforms (RRT, ODT, inverse transforms)."""

    def test_nested_transform_id_validation(self, tmp_path):
        """Malformed transform ID in referenceRenderingTransform should be detected."""
        amf = minimal_amf()
        amf.pipeline.output_transform = amf_v2.OutputTransformType(
            applied=True,
            reference_rendering_transform=amf_v2.ReferenceRenderingTransformType(
                transform_id="bad-rrt-format"
            ),
            output_device_transform=amf_v2.OutputDeviceTransformType(
                transform_id="urn:ampas:aces:transformId:v1.5:ODT.Academy.Rec709_100nits_dim.a1.0.3"
            ),
        )
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path, validate=False)

        messages = validate_semantic(amf_path, validators=["transform_ids"])
        rrt_warnings = [m for m in messages if "referenceRenderingTransform" in m.message]
        assert len(rrt_warnings) >= 1, "Malformed RRT transform ID should be detected"

    def test_nested_file_path_validation(self, tmp_path):
        """Absolute path in nested outputDeviceTransform.file should be detected."""
        amf = minimal_amf()
        amf.pipeline.output_transform = amf_v2.OutputTransformType(
            applied=True,
            output_device_transform=amf_v2.OutputDeviceTransformType(
                file="/absolute/path/odt.clf"
            ),
        )
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path, validate=False)

        messages = validate_semantic(amf_path, validators=["file_paths"])
        nested_warnings = [m for m in messages if "outputDeviceTransform" in m.message]
        assert len(nested_warnings) >= 1, "Absolute path in nested transform should be detected"

    def test_nested_uuid_duplicate(self, tmp_path):
        """Duplicate UUID in nested sub-transform should be detected."""
        shared_uuid = "urn:uuid:12345678-1234-1234-1234-123456789abc"
        amf = minimal_amf()
        amf.pipeline.output_transform = amf_v2.OutputTransformType(
            applied=True,
            uuid=shared_uuid,
            reference_rendering_transform=amf_v2.ReferenceRenderingTransformType(
                uuid=shared_uuid,  # duplicate!
            ),
        )
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path, validate=False)

        messages = validate_semantic(amf_path, validators=["uuid"])
        dup_errors = [m for m in messages if m.validation_type == ValidationType.DUPLICATE_UUID]
        assert len(dup_errors) >= 1, "Duplicate UUID in nested sub-transform should be detected"

    def test_input_inverse_transform_id_validation(self, tmp_path):
        """Malformed transform ID in input's inverseOutputDeviceTransform should be detected."""
        amf = minimal_amf()
        amf.pipeline.input_transform = amf_v2.InputTransformType(
            applied=True,
            inverse_output_device_transform=amf_v2.InverseOutputDeviceTransformType(
                transform_id="bad-inv-odt-format"
            ),
        )
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path, validate=False)

        messages = validate_semantic(amf_path, validators=["transform_ids"])
        inv_warnings = [m for m in messages if "inverseOutputDeviceTransform" in m.message]
        assert len(inv_warnings) >= 1, "Malformed inverse ODT transform ID should be detected"


class TestPrepareForWriteArchived:
    """Tests for prepare_for_write archived pipeline handling."""

    def test_archived_mod_timestamp_updated(self, tmp_path):
        """prepare_for_write should update archived pipeline modification timestamps."""
        import uuid as uuid_mod
        from aces_amf_lib.amf_utilities import amf_date_time_now

        amf = minimal_amf()
        archived_info = amf_v2.PipelineInfoType(
            date_time=amf_date_time_now(),
            uuid=uuid_mod.uuid4().urn,
            system_version=amf_v2.VersionType(major_version=1, minor_version=3, patch_version=0),
        )
        original_uuid = archived_info.uuid
        amf.archived_pipeline.append(amf_v2.PipelineType(pipeline_info=archived_info))

        # Save triggers prepare_for_write
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path)

        # UUID should be preserved (archived = historical identity)
        assert amf.archived_pipeline[0].pipeline_info.uuid == original_uuid
        # Modification timestamp should have been updated (same as amf_info)
        assert (amf.archived_pipeline[0].pipeline_info.date_time.modification_date_time
                == amf.amf_info.date_time.modification_date_time)


class TestFilePathNoUnquote:
    """Regression: file paths with % should not be URL-decoded."""

    def test_file_path_percent_preserved(self, tmp_path):
        """A file path containing %20 should be validated as-is, not decoded."""
        amf = minimal_amf()
        amf.pipeline.input_transform = amf_v2.InputTransformType(
            applied=True, file="path/with%20space/file.clf"
        )
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path)

        messages = validate_semantic(amf_path, validators=["file_paths"])
        # Should not produce security warnings — %20 is just a literal character sequence
        security_warnings = [m for m in messages if m.validation_type in [
            ValidationType.UNSAFE_FILE_PATH,
            ValidationType.NON_PORTABLE_PATH,
        ]]
        assert len(security_warnings) == 0


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


class TestMultipleWorkingLocations:
    """Validate that at most one workingLocation is allowed per pipeline."""

    def test_zero_working_locations_valid(self, tmp_path):
        """A pipeline with no workingLocation is valid."""
        amf = minimal_amf()
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path, validate=False)
        msgs = validate_semantic(amf_path, validators=["working_space"])
        wl_msgs = [m for m in msgs if m.validation_type == ValidationType.MULTIPLE_WORKING_LOCATIONS]
        assert len(wl_msgs) == 0

    def test_one_working_location_valid(self, tmp_path):
        """A pipeline with exactly one workingLocation is valid."""
        amf = minimal_amf()
        amf.pipeline.working_location_or_look_transform.append(amf_v2.WorkingLocationType())
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path, validate=False)
        msgs = validate_semantic(amf_path, validators=["working_space"])
        wl_msgs = [m for m in msgs if m.validation_type == ValidationType.MULTIPLE_WORKING_LOCATIONS]
        assert len(wl_msgs) == 0

    def test_multiple_working_locations_error(self, tmp_path):
        """A pipeline with 2+ workingLocations produces an ERROR."""
        amf = minimal_amf()
        amf.pipeline.working_location_or_look_transform.append(amf_v2.WorkingLocationType())
        amf.pipeline.working_location_or_look_transform.append(amf_v2.WorkingLocationType())
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path, validate=False)
        msgs = validate_semantic(amf_path, validators=["working_space"])
        wl_msgs = [m for m in msgs if m.validation_type == ValidationType.MULTIPLE_WORKING_LOCATIONS]
        assert len(wl_msgs) == 1
        assert wl_msgs[0].level == ValidationLevel.ERROR
        assert "2 workingLocation" in wl_msgs[0].message

    def test_archived_multiple_working_locations_error(self, tmp_path):
        """Archived pipelines with 2+ workingLocations also produce an ERROR."""
        from aces_amf_lib.amf_utilities import amf_xml_date_time

        amf = minimal_amf()
        now = amf_xml_date_time()
        archived = amf_v2.PipelineType(pipeline_info=amf_v2.PipelineInfoType(
            uuid="urn:uuid:00000000-0000-0000-0000-000000000099",
            date_time=amf_v2.DateTimeType(
                creation_date_time=now,
                modification_date_time=now,
            ),
            system_version=amf_v2.VersionType(major_version=1, minor_version=3, patch_version=0),
        ))
        archived.working_location_or_look_transform.append(amf_v2.WorkingLocationType())
        archived.working_location_or_look_transform.append(amf_v2.WorkingLocationType())
        amf.archived_pipeline.append(archived)
        amf_path = tmp_path / "test.amf"
        save_amf(amf, amf_path, validate=False)
        msgs = validate_semantic(amf_path, validators=["working_space"])
        wl_msgs = [m for m in msgs if m.validation_type == ValidationType.MULTIPLE_WORKING_LOCATIONS]
        assert len(wl_msgs) == 1
        assert "Archived pipeline #1" in wl_msgs[0].message
