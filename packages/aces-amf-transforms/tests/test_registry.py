# SPDX-License-Identifier: Apache-2.0
"""Tests for the ACES transform registry."""

import pytest

from aces_amf_transforms import ACESTransformRegistry, TransformInfo


@pytest.fixture
def registry():
    return ACESTransformRegistry()


class TestACESTransformRegistry:
    def test_loads_transforms(self, registry):
        assert registry.transform_count > 0
        assert registry.schema_version == "1.0.0"

    def test_is_valid_transform_id_known(self, registry):
        # v2 CSC transform
        assert registry.is_valid_transform_id(
            "urn:ampas:aces:transformId:v2.0:CSC.Academy.ACES_to_ACEScc.a2.v1"
        )

    def test_is_valid_transform_id_v1(self, registry):
        # v1 transform
        assert registry.is_valid_transform_id(
            "urn:ampas:aces:transformId:v1.5:ACEScsc.Academy.ACES_to_ACEScc.a1.0.3"
        )

    def test_is_valid_transform_id_unknown(self, registry):
        assert not registry.is_valid_transform_id("urn:ampas:aces:transformId:v99.0:FAKE.Transform")

    def test_is_valid_transform_id_previous_equivalent(self, registry):
        # Previous equivalent IDs should resolve
        assert registry.is_valid_transform_id("ACEScsc.ACES_to_ACEScc.a1.0.3")

    def test_get_transform_info(self, registry):
        info = registry.get_transform_info(
            "urn:ampas:aces:transformId:v2.0:CSC.Academy.ACES_to_ACEScc.a2.v1"
        )
        assert info is not None
        assert info["user_name"] == "ACES2065-1 to ACEScc"
        assert info["transform_type"] == "CSC"
        assert info["inverse_transform_id"] is not None

    def test_get_transform_info_not_found(self, registry):
        info = registry.get_transform_info("urn:ampas:aces:transformId:v99.0:FAKE")
        assert info is None

    def test_get_transform_info_via_previous_id(self, registry):
        info = registry.get_transform_info("ACEScsc.ACES_to_ACEScc.a1.0.3")
        assert info is not None
        # Should resolve to the current version
        assert "ACES" in info["user_name"]

    def test_list_transforms(self, registry):
        transforms = registry.list_transforms()
        assert len(transforms) > 0
        assert all("transform_id" in t for t in transforms)

    def test_list_transforms_by_category(self, registry):
        csc_transforms = registry.list_transforms(category="CSC")
        assert len(csc_transforms) > 0
        assert all(t["transform_type"] == "CSC" for t in csc_transforms)

    def test_get_transform_categories(self, registry):
        categories = registry.get_transform_categories()
        assert len(categories) > 0
        assert "CSC" in categories

    def test_are_transforms_inverses(self, registry):
        assert registry.are_transforms_inverses(
            "urn:ampas:aces:transformId:v2.0:CSC.Academy.ACES_to_ACEScc.a2.v1",
            "urn:ampas:aces:transformId:v2.0:CSC.Academy.ACEScc_to_ACES.a2.v1",
        )

    def test_are_transforms_not_inverses(self, registry):
        assert not registry.are_transforms_inverses(
            "urn:ampas:aces:transformId:v2.0:CSC.Academy.ACES_to_ACEScc.a2.v1",
            "urn:ampas:aces:transformId:v2.0:CSC.Academy.ACES_to_ACEScct.a2.v1",
        )


class TestTransformIdValidator:
    def test_validator_with_known_transform(self, tmp_path):
        from aces_amf_lib import ACESAMF, amf_v2
        from aces_amf_transforms import TransformIdValidator
        from aces_amf_lib.validation.types import ValidationContext, ValidationType

        amf = ACESAMF()
        amf.amf.pipeline.input_transform = amf_v2.InputTransformType(
            applied=True,
            transform_id="urn:ampas:aces:transformId:v1.5:ACEScsc.Academy.ACES_to_ACEScc.a1.0.3",
        )
        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        loaded = ACESAMF.from_file(amf_path)
        validator = TransformIdValidator()
        context = ValidationContext(amf_path=amf_path)
        messages = validator.validate(loaded, context)

        id_warnings = [m for m in messages if m.validation_type == ValidationType.INVALID_TRANSFORM_ID]
        assert len(id_warnings) == 0

    def test_validator_with_unknown_transform(self, tmp_path):
        from aces_amf_lib import ACESAMF, amf_v2
        from aces_amf_transforms import TransformIdValidator
        from aces_amf_lib.validation.types import ValidationContext, ValidationType

        amf = ACESAMF()
        amf.amf.pipeline.input_transform = amf_v2.InputTransformType(
            applied=True,
            transform_id="urn:ampas:aces:transformId:v99.0:FAKE.Transform.a99.v1",
        )
        amf_path = tmp_path / "test.amf"
        amf.write(amf_path)

        loaded = ACESAMF.from_file(amf_path)
        validator = TransformIdValidator()
        context = ValidationContext(amf_path=amf_path)
        messages = validator.validate(loaded, context)

        id_warnings = [m for m in messages if m.validation_type == ValidationType.INVALID_TRANSFORM_ID]
        assert len(id_warnings) == 1
        assert "unknown transform id" in id_warnings[0].message.lower()
