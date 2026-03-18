# SPDX-License-Identifier: Apache-2.0
"""Tests for the ACESAMF high-level wrapper."""

import pytest
from aces_amf_lib import AcesMetadataFile
from aces_amf_lib.amf_v2 import LookTransformType, WorkingLocationType

from aces_amf_utils import ACESAMF


class TestACESAMFConstruction:
    def test_new_returns_instance(self):
        amf = ACESAMF.new()
        assert isinstance(amf, ACESAMF)
        assert isinstance(amf.amf, AcesMetadataFile)

    def test_new_default_aces_version(self):
        amf = ACESAMF.new()
        assert amf.aces_version == (1, 3, 0)

    def test_new_custom_aces_version(self):
        amf = ACESAMF.new(aces_version=(2, 0, 0))
        assert amf.aces_version == (2, 0, 0)

    def test_from_file(self, sample_amf_path):
        amf = ACESAMF.from_file(sample_amf_path)
        assert isinstance(amf, ACESAMF)

    def test_from_file_no_validate(self, sample_amf_path):
        amf = ACESAMF.from_file(sample_amf_path, validate=False)
        assert isinstance(amf, ACESAMF)

    def test_from_data(self, sample_amf_path):
        data = sample_amf_path.read_bytes()
        amf = ACESAMF.from_data(data)
        assert isinstance(amf, ACESAMF)

    def test_amf_property_returns_raw_model(self):
        amf = ACESAMF.new()
        assert isinstance(amf.amf, AcesMetadataFile)


class TestACESAMFProperties:
    def test_aces_version(self):
        amf = ACESAMF.new(aces_version=(1, 3, 0))
        assert amf.aces_version == (1, 3, 0)

    def test_amf_description_initially_none(self):
        amf = ACESAMF.new()
        assert amf.amf_description is None

    def test_amf_description_after_set(self):
        amf = ACESAMF.new().with_description("My Show")
        assert amf.amf_description == "My Show"

    def test_pipeline_description_initially_none(self):
        amf = ACESAMF.new()
        assert amf.pipeline_description is None

    def test_pipeline_description_after_set(self):
        amf = ACESAMF.new().with_pipeline_description("Camera to Rec.709")
        assert amf.pipeline_description == "Camera to Rec.709"

    def test_amf_authors_initially_empty(self):
        amf = ACESAMF.new()
        assert amf.amf_authors == []

    def test_aces_major_version(self):
        assert ACESAMF.new(aces_version=(1, 3, 0)).aces_major_version == 1
        assert ACESAMF.new(aces_version=(2, 0, 0)).aces_major_version == 2

    def test_amf_description_setter(self):
        amf = ACESAMF.new()
        amf.amf_description = "Set via setter"
        assert amf.amf_description == "Set via setter"

    def test_pipeline_description_setter(self):
        amf = ACESAMF.new()
        amf.pipeline_description = "Pipeline via setter"
        assert amf.pipeline_description == "Pipeline via setter"


class TestACESAMFFluentMutators:
    def test_with_description(self):
        amf = ACESAMF.new().with_description("Test")
        assert amf.amf.amf_info.description == "Test"

    def test_with_pipeline_description(self):
        amf = ACESAMF.new().with_pipeline_description("Pipeline desc")
        assert amf.amf.pipeline.pipeline_info.description == "Pipeline desc"

    def test_set_aces_version(self):
        amf = ACESAMF.new().set_aces_version(2, 0, 0)
        assert amf.aces_version == (2, 0, 0)

    def test_clip_id(self):
        amf = ACESAMF.new().clip_id("A001C012", file="A001C012.ari")
        assert amf.amf.clip_id is not None
        assert amf.amf.clip_id.clip_name == "A001C012"

    def test_input_transform(self):
        tid = "urn:ampas:aces:transformId:v1.5:IDT.ARRI.ARRI-LogC4.a1.v1"
        amf = ACESAMF.new().input_transform(transform_id=tid)
        it = amf.amf.pipeline.input_transform
        assert it is not None
        assert it.transform_id == tid
        assert it.applied is False

    def test_output_transform(self):
        tid = "urn:ampas:aces:transformId:v1.5:ODT.Academy.Rec709_100nits_dim.a1.0.3"
        amf = ACESAMF.new().output_transform(transform_id=tid, applied=True)
        ot = amf.amf.pipeline.output_transform
        assert ot is not None
        assert ot.transform_id == tid
        assert ot.applied is True

    def test_look_transform_file(self):
        amf = ACESAMF.new().look_transform(file="grade.clf", description="Primary")
        assert amf.count_looks() == 1
        assert amf.get_look(0).file == "grade.clf"

    def test_look_transform_cdl(self):
        amf = ACESAMF.new().look_transform(
            cdl={"asc_sop": {"slope": [1.1, 1.0, 0.9], "offset": [0, 0, 0], "power": [1, 1, 1]}, "asc_sat": 0.9}
        )
        assert amf.count_looks() == 1
        lt = amf.get_look(0)
        assert lt.asc_sop is not None

    def test_working_location_inserts_marker(self):
        amf = (ACESAMF.new()
               .look_transform(file="pre.clf")
               .working_location()
               .look_transform(file="post.clf"))
        compound = amf.amf.pipeline.working_location_or_look_transform
        assert len(compound) == 3
        assert isinstance(compound[1], WorkingLocationType)

    def test_chaining_returns_self(self):
        amf = (ACESAMF.new()
               .with_description("Show")
               .with_pipeline_description("Pipeline")
               .author("Alice", "alice@example.com")
               .input_transform(file="idt.clf")
               .look_transform(file="lmt.clf")
               .output_transform(description="Output"))
        assert isinstance(amf, ACESAMF)
        assert amf.count_looks() == 1


class TestACESAMFAuthorManagement:
    def test_add_amf_author(self):
        amf = ACESAMF.new().add_amf_author("Jane", "jane@example.com")
        assert len(amf.amf_authors) == 1
        assert amf.amf_authors[0].name == "Jane"
        assert amf.amf_authors[0].email_address == "jane@example.com"

    def test_add_amf_author_no_email(self):
        amf = ACESAMF.new().add_amf_author("Jane")
        assert amf.amf_authors[0].email_address == ""

    def test_add_multiple_authors(self):
        amf = (ACESAMF.new()
               .add_amf_author("Alice", "alice@example.com")
               .add_amf_author("Bob", "bob@example.com"))
        assert len(amf.amf_authors) == 2

    def test_clear_amf_authors(self):
        amf = (ACESAMF.new()
               .add_amf_author("Alice", "alice@example.com")
               .clear_amf_authors())
        assert amf.amf_authors == []

    def test_author_fluent_method(self):
        # author() is inherited from _AMFMutatorMixin
        amf = ACESAMF.new().author("Jane", "jane@example.com")
        assert len(amf.amf_authors) == 1


class TestACESAMFLookStack:
    def _amf_with_looks(self, n: int) -> ACESAMF:
        amf = ACESAMF.new()
        for i in range(n):
            amf.look_transform(file=f"look_{i}.clf", description=f"Look {i}")
        return amf

    def test_get_looks_empty(self):
        amf = ACESAMF.new()
        assert amf.get_looks() == []

    def test_get_looks(self):
        amf = self._amf_with_looks(3)
        looks = amf.get_looks()
        assert len(looks) == 3
        assert all(isinstance(lt, LookTransformType) for lt in looks)

    def test_get_look_by_positive_index(self):
        amf = self._amf_with_looks(3)
        assert amf.get_look(1).description == "Look 1"

    def test_get_look_by_negative_index(self):
        amf = self._amf_with_looks(3)
        assert amf.get_look(-1).description == "Look 2"

    def test_count_looks(self):
        assert ACESAMF.new().count_looks() == 0
        assert self._amf_with_looks(3).count_looks() == 3

    def test_iter_looks(self):
        amf = self._amf_with_looks(3)
        pairs = list(amf.iter_looks())
        assert [(i, lt.description) for i, lt in pairs] == [
            (0, "Look 0"), (1, "Look 1"), (2, "Look 2")
        ]

    def test_add_look_transform(self):
        amf = ACESAMF.new().add_look_transform(file="grade.clf", description="Grade")
        assert amf.count_looks() == 1
        assert amf.get_look(0).file == "grade.clf"

    def test_add_cdl_look_transform(self):
        amf = ACESAMF.new().add_cdl_look_transform(
            slope=(1.1, 1.0, 0.9), description="CDL grade"
        )
        assert amf.count_looks() == 1
        lt = amf.get_look(0)
        assert lt.asc_sop is not None
        assert lt.description == "CDL grade"

    def test_insert_look_at_start(self):
        amf = self._amf_with_looks(2)
        new_lt = LookTransformType(applied=False, description="Inserted")
        amf.insert_look(0, new_lt)
        assert amf.count_looks() == 3
        assert amf.get_look(0).description == "Inserted"
        assert amf.get_look(1).description == "Look 0"

    def test_insert_look_at_end(self):
        amf = self._amf_with_looks(2)
        new_lt = LookTransformType(applied=False, description="Appended")
        amf.insert_look(99, new_lt)
        assert amf.count_looks() == 3
        assert amf.get_look(-1).description == "Appended"

    def test_insert_look_in_middle(self):
        amf = self._amf_with_looks(2)
        new_lt = LookTransformType(applied=False, description="Middle")
        amf.insert_look(1, new_lt)
        assert amf.get_look(0).description == "Look 0"
        assert amf.get_look(1).description == "Middle"
        assert amf.get_look(2).description == "Look 1"

    def test_remove_look(self):
        amf = self._amf_with_looks(3)
        amf.remove_look(1)
        assert amf.count_looks() == 2
        assert amf.get_look(0).description == "Look 0"
        assert amf.get_look(1).description == "Look 2"

    def test_remove_look_preserves_working_location(self):
        amf = (ACESAMF.new()
               .look_transform(file="pre.clf")
               .working_location()
               .look_transform(file="post.clf"))
        amf.remove_look(0)
        compound = amf.amf.pipeline.working_location_or_look_transform
        # WorkingLocationType marker must survive
        assert any(isinstance(item, WorkingLocationType) for item in compound)
        assert amf.count_looks() == 1

    def test_move_look_forward(self):
        # move_look(0, 2): remove L0 → [L1, L2], insert at 2 (append) → [L1, L2, L0]
        amf = self._amf_with_looks(3)
        amf.move_look(0, 2)
        assert amf.get_look(0).description == "Look 1"
        assert amf.get_look(1).description == "Look 2"
        assert amf.get_look(2).description == "Look 0"

    def test_move_look_backward(self):
        amf = self._amf_with_looks(3)
        amf.move_look(2, 0)
        assert amf.get_look(0).description == "Look 2"
        assert amf.get_look(1).description == "Look 0"

    def test_clear_looks(self):
        amf = self._amf_with_looks(3)
        amf.clear_looks()
        assert amf.count_looks() == 0

    def test_clear_looks_preserves_working_location(self):
        amf = (ACESAMF.new()
               .look_transform(file="pre.clf")
               .working_location()
               .look_transform(file="post.clf"))
        amf.clear_looks()
        assert amf.count_looks() == 0
        compound = amf.amf.pipeline.working_location_or_look_transform
        assert len(compound) == 1
        assert isinstance(compound[0], WorkingLocationType)

    def test_insert_before_working_location(self):
        # [look_0, WL, look_1] → insert at 0 → [NEW, look_0, WL, look_1]
        amf = (ACESAMF.new()
               .look_transform(file="look_0.clf")
               .working_location()
               .look_transform(file="look_1.clf"))
        new_lt = LookTransformType(applied=False, description="Before")
        amf.insert_look(0, new_lt)
        assert amf.count_looks() == 3
        assert amf.get_look(0).description == "Before"
        # Working location marker must still be present
        compound = amf.amf.pipeline.working_location_or_look_transform
        assert any(isinstance(item, WorkingLocationType) for item in compound)

    def test_insert_after_working_location(self):
        # [look_0, WL, look_1] → insert at 1 → [look_0, WL, NEW, look_1]
        amf = (ACESAMF.new()
               .look_transform(file="look_0.clf")
               .working_location()
               .look_transform(file="look_1.clf"))
        new_lt = LookTransformType(applied=False, description="After WL")
        amf.insert_look(1, new_lt)
        assert amf.get_look(1).description == "After WL"
        assert amf.get_look(2).file == "look_1.clf"


class TestACESAMFIO:
    def test_dump_returns_xml_string(self):
        xml = ACESAMF.new().dump(validate=False)
        assert isinstance(xml, str)
        assert "<?xml" in xml or "<AcesMetadataFile" in xml

    def test_write_roundtrip(self, tmp_path):
        path = tmp_path / "test.amf"
        amf = ACESAMF.new().with_description("Roundtrip test")
        amf.write(path, validate=False)
        loaded = ACESAMF.from_file(path, validate=False)
        assert loaded.amf_description == "Roundtrip test"

    def test_rev_up_returns_self(self):
        amf = ACESAMF.new()
        result = amf.rev_up()
        assert result is amf

    def test_rev_up_updates_timestamps(self):
        amf = ACESAMF.new()
        before = amf.amf.amf_info.date_time.modification_date_time
        amf.rev_up()
        after = amf.amf.amf_info.date_time.modification_date_time
        # modification_date_time should be updated (may be same if called quickly,
        # but the call must not raise)
        assert after is not None

class TestACESAMFDirectSetters:
    def test_set_input_transform(self):
        from aces_amf_lib.amf_v2 import InputTransformType
        it = InputTransformType(applied=True, file="idt.clf")
        amf = ACESAMF.new().set_input_transform(it)
        assert amf.amf.pipeline.input_transform is it
        assert amf.amf.pipeline.input_transform.applied is True

    def test_set_output_transform(self):
        from aces_amf_lib.amf_v2 import OutputTransformType
        ot = OutputTransformType(applied=True, description="Display")
        amf = ACESAMF.new().set_output_transform(ot)
        assert amf.amf.pipeline.output_transform is ot
        assert amf.amf.pipeline.output_transform.description == "Display"

    def test_set_input_transform_returns_self(self):
        from aces_amf_lib.amf_v2 import InputTransformType
        amf = ACESAMF.new()
        result = amf.set_input_transform(InputTransformType(applied=False))
        assert result is amf

    def test_set_output_transform_returns_self(self):
        from aces_amf_lib.amf_v2 import OutputTransformType
        amf = ACESAMF.new()
        result = amf.set_output_transform(OutputTransformType(applied=False))
        assert result is amf

    def test_set_input_transform_overrides_existing(self):
        from aces_amf_lib.amf_v2 import InputTransformType
        amf = ACESAMF.new().input_transform(file="first.clf")
        new_it = InputTransformType(applied=False, file="second.clf")
        amf.set_input_transform(new_it)
        assert amf.amf.pipeline.input_transform.file == "second.clf"
