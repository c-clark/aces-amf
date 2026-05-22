# SPDX-License-Identifier: Apache-2.0
"""Tests verifying that the builder API rejects misplaced transform URNs."""

import pytest

from aces.amf_utils import AMFBuilder
from aces.amf_lib.amf import InputTransformType, LookTransformType, OutputTransformType

VALID_IDT_URN = "urn:ampas:aces:transformId:v1.5:IDT.ARRI.ARRI-LogC4.a1.v1"
VALID_ODT_URN = "urn:ampas:aces:transformId:v1.5:RRTODT.Academy.Rec709_100nits_dim.a1.0.3"
VALID_LMT_URN = "urn:ampas:aces:transformId:v1.5:LMT.Academy.ACES_1.3_Filmic_Tone_Map.a1.0.3"
VALID_OUTPUT_V2_URN = "urn:ampas:aces:transformId:v2.0:Output.Rec709.a1.v1"
VALID_INPUT_V2_URN = "urn:ampas:aces:transformId:v2.0:Input.ARRI.LogC4.a1.v1"


class TestBuilderRejectsInputMisplacement:
    def test_odt_in_input_raises(self):
        with pytest.raises(ValueError, match="not valid for InputTransform"):
            AMFBuilder().with_input_transform(InputTransformType(transform_id=VALID_ODT_URN, applied=False))

    def test_lmt_in_input_raises(self):
        with pytest.raises(ValueError, match="not valid for InputTransform"):
            AMFBuilder().with_input_transform(InputTransformType(transform_id=VALID_LMT_URN, applied=False))

    def test_v2_output_in_input_raises(self):
        with pytest.raises(ValueError, match="not valid for InputTransform"):
            AMFBuilder().with_input_transform(InputTransformType(transform_id=VALID_OUTPUT_V2_URN, applied=False))

    def test_valid_input_accepted(self):
        builder = AMFBuilder().with_input_transform(InputTransformType(transform_id=VALID_IDT_URN, applied=False))
        assert builder.input_transform.transform_id == VALID_IDT_URN


class TestBuilderRejectsOutputMisplacement:
    def test_idt_in_output_raises(self):
        with pytest.raises(ValueError, match="not valid for OutputTransform"):
            AMFBuilder().with_output_transform(OutputTransformType(transform_id=VALID_IDT_URN, applied=False))

    def test_lmt_in_output_raises(self):
        with pytest.raises(ValueError, match="not valid for OutputTransform"):
            AMFBuilder().with_output_transform(OutputTransformType(transform_id=VALID_LMT_URN, applied=False))

    def test_valid_output_accepted(self):
        builder = AMFBuilder().with_output_transform(OutputTransformType(transform_id=VALID_ODT_URN, applied=False))
        assert builder.output_transform.transform_id == VALID_ODT_URN


class TestBuilderRejectsLookMisplacement:
    def test_idt_in_look_raises(self):
        with pytest.raises(ValueError, match="not valid for LookTransform"):
            AMFBuilder().with_look_transform(LookTransformType(transform_id=VALID_IDT_URN, applied=True))

    def test_odt_in_look_raises(self):
        with pytest.raises(ValueError, match="not valid for LookTransform"):
            AMFBuilder().with_look_transform(LookTransformType(transform_id=VALID_ODT_URN, applied=True))

    def test_valid_look_accepted(self):
        builder = AMFBuilder().with_look_transform(LookTransformType(transform_id=VALID_LMT_URN, applied=True))
        assert len(builder.get_looks()) == 1


class TestBuilderInsertLookMisplacement:
    def test_insert_idt_in_look_raises(self):
        with pytest.raises(ValueError, match="not valid for LookTransform"):
            AMFBuilder().insert_look(0, LookTransformType(transform_id=VALID_IDT_URN, applied=True))

    def test_insert_valid_look_accepted(self):
        builder = AMFBuilder().insert_look(0, LookTransformType(transform_id=VALID_LMT_URN, applied=True))
        assert len(builder.get_looks()) == 1


class TestBuilderPropertySetterMisplacement:
    def test_input_setter_rejects_odt(self):
        builder = AMFBuilder()
        with pytest.raises(ValueError, match="not valid for InputTransform"):
            builder.input_transform = InputTransformType(transform_id=VALID_ODT_URN, applied=False)

    def test_output_setter_rejects_idt(self):
        builder = AMFBuilder()
        with pytest.raises(ValueError, match="not valid for OutputTransform"):
            builder.output_transform = OutputTransformType(transform_id=VALID_IDT_URN, applied=False)

    def test_input_setter_accepts_none(self):
        builder = AMFBuilder()
        builder.input_transform = None
        assert builder.input_transform is None

    def test_output_setter_accepts_none(self):
        builder = AMFBuilder()
        builder.output_transform = None
        assert builder.output_transform is None
