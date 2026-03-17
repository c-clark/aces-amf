# SPDX-License-Identifier: Apache-2.0
"""Tests for the AMFBuilder fluent API."""

import pytest
from aces_amf_utils import AMFBuilder
from aces_amf_lib import AcesMetadataFile, load_amf, save_amf
from aces_amf_lib.amf_v2 import LookTransformType, WorkingLocationType


class TestAMFBuilder:
    def test_basic_build(self):
        amf = AMFBuilder().build()
        assert isinstance(amf, AcesMetadataFile)

    def test_with_description(self):
        amf = AMFBuilder().with_description("Test show").build()
        assert amf.amf_info.description == "Test show"

    def test_with_pipeline_description(self):
        amf = AMFBuilder().with_pipeline_description("Camera to Rec.709").build()
        assert amf.pipeline.pipeline_info.description == "Camera to Rec.709"

    def test_author(self):
        amf = AMFBuilder().author("Jane Doe", "jane@example.com").build()
        assert len(amf.amf_info.author) == 1
        assert amf.amf_info.author[0].name == "Jane Doe"
        assert amf.amf_info.author[0].email_address == "jane@example.com"

    def test_multiple_authors(self):
        amf = (
            AMFBuilder()
            .author("Alice", "alice@example.com")
            .author("Bob", "bob@example.com")
            .build()
        )
        assert len(amf.amf_info.author) == 2

    def test_input_transform(self):
        tid = "urn:ampas:aces:transformId:v1.5:IDT.ARRI.ARRI-LogC4.a1.v1"
        amf = AMFBuilder().input_transform(transform_id=tid).build()
        it = amf.pipeline.input_transform
        assert it is not None
        assert it.transform_id == tid
        assert it.applied is False

    def test_output_transform(self):
        tid = "urn:ampas:aces:transformId:v1.5:ODT.Academy.Rec709_100nits_dim.a1.0.3"
        amf = AMFBuilder().output_transform(transform_id=tid, applied=True).build()
        ot = amf.pipeline.output_transform
        assert ot is not None
        assert ot.transform_id == tid
        assert ot.applied is True

    def test_look_transform_with_file(self):
        amf = (
            AMFBuilder()
            .look_transform(file="grade.clf", description="Primary grade")
            .build()
        )
        lts = amf.pipeline.look_transforms
        assert len(lts) == 1
        assert lts[0].description == "Primary grade"

    def test_look_transform_with_cdl(self):
        cdl = {
            "asc_sop": {
                "slope": [1.2, 1.0, 0.8],
                "offset": [0.01, 0.0, -0.01],
                "power": [1.0, 1.0, 1.0],
            },
            "asc_sat": 0.9,
        }
        amf = AMFBuilder().look_transform(cdl=cdl, description="CDL grade").build()
        lts = amf.pipeline.look_transforms
        assert len(lts) == 1
        assert lts[0].asc_sop is not None

    def test_chaining(self):
        """Verify full builder chain returns a valid AMF."""
        amf = (
            AMFBuilder(aces_version=(2, 0, 0))
            .with_description("Full pipeline test")
            .with_pipeline_description("Camera to Display")
            .author("Test User")
            .input_transform(
                transform_id="urn:ampas:aces:transformId:v1.5:IDT.ARRI.ARRI-LogC4.a1.v1"
            )
            .look_transform(
                cdl={
                    "asc_sop": {
                        "slope": [1.1, 1.0, 0.9],
                        "offset": [0.0, 0.0, 0.0],
                        "power": [1.0, 1.0, 1.0],
                    },
                    "asc_sat": 1.0,
                }
            )
            .output_transform(
                transform_id="urn:ampas:aces:transformId:v1.5:ODT.Academy.Rec709_100nits_dim.a1.0.3"
            )
            .build()
        )
        assert amf.amf_info.description == "Full pipeline test"
        sv = amf.pipeline.pipeline_info.system_version
        assert (int(sv.major_version), int(sv.minor_version), int(sv.patch_version)) == (2, 0, 0)
        assert amf.pipeline.input_transform is not None
        assert len(amf.pipeline.look_transforms) == 1
        assert amf.pipeline.output_transform is not None

    def test_set_aces_version(self):
        amf = AMFBuilder().set_aces_version(2, 0, 0).build()
        sv = amf.pipeline.pipeline_info.system_version
        assert (int(sv.major_version), int(sv.minor_version), int(sv.patch_version)) == (2, 0, 0)

    def test_write_roundtrip(self, tmp_path):
        """Build, write, re-read, verify."""
        out = tmp_path / "test.amf"
        amf = (
            AMFBuilder()
            .with_description("Roundtrip test")
            .author("Tester")
            .build()
        )
        save_amf(amf, out, validate=False)

        loaded = load_amf(out, validate=False)
        assert loaded.amf_info.description == "Roundtrip test"
        assert len(loaded.amf_info.author) == 1
        assert loaded.amf_info.author[0].name == "Tester"

    def test_clip_id(self):
        amf = AMFBuilder().clip_id("A001C012", file="A001C012.ari").build()
        assert amf.clip_id is not None
        assert amf.clip_id.clip_name == "A001C012"

    def test_working_location(self):
        """Builder inserts a working location delimiter."""
        amf = AMFBuilder().working_location().build()
        items = amf.pipeline.working_location_or_look_transform
        assert len(items) == 1
        assert isinstance(items[0], WorkingLocationType)

    def test_looks_around_working_location(self):
        """Looks added before/after working_location() are ordered correctly."""
        amf = (
            AMFBuilder()
            .look_transform(file="pre_grade.clf", description="Pre")
            .working_location()
            .look_transform(file="post_grade.clf", description="Post")
            .build()
        )
        items = amf.pipeline.working_location_or_look_transform
        assert len(items) == 3
        assert isinstance(items[0], LookTransformType)
        assert isinstance(items[1], WorkingLocationType)
        assert isinstance(items[2], LookTransformType)
        assert items[0].description == "Pre"
        assert items[2].description == "Post"

    def test_working_location_roundtrip(self, tmp_path):
        """Working location ordering survives save/reload."""
        amf = (
            AMFBuilder()
            .look_transform(file="pre.clf")
            .working_location()
            .look_transform(file="post.clf")
            .build()
        )
        out = tmp_path / "wl_test.amf"
        save_amf(amf, out, validate=False)

        loaded = load_amf(out, validate=False)
        items = loaded.pipeline.working_location_or_look_transform
        assert len(items) == 3
        assert isinstance(items[0], LookTransformType)
        assert isinstance(items[1], WorkingLocationType)
        assert isinstance(items[2], LookTransformType)
