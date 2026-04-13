# SPDX-License-Identifier: Apache-2.0
"""
Tests verifying that misplaced transform URNs are caught.

Enforcement layers:
1. Pydantic construction — ValueError raised immediately when creating an object
   with a wrong URN prefix (e.g., ODT URN in InputTransformType).
2. XSD schema validation — pattern facets on transformId catch misplacement
   when saving/loading XML.
"""

import pytest

from aces_amf_lib import amf


# -- Valid URNs for each container type --
VALID_IDT_URN = "urn:ampas:aces:transformId:v1.5:IDT.ARRI.ARRI-LogC4.a1.v1"
VALID_ODT_URN = "urn:ampas:aces:transformId:v1.5:RRTODT.Academy.Rec709_100nits_dim.a1.0.3"
VALID_LMT_URN = "urn:ampas:aces:transformId:v1.5:LMT.Academy.ACES_1.3_Filmic_Tone_Map.a1.0.3"
VALID_INPUT_V2_URN = "urn:ampas:aces:transformId:v2.0:Input.ARRI.LogC4.a1.v1"
VALID_OUTPUT_V2_URN = "urn:ampas:aces:transformId:v2.0:Output.Rec709.a1.v1"
VALID_LOOK_V2_URN = "urn:ampas:aces:transformId:v2.0:Look.ACME.FilmGrade.a1.v1"
VALID_CSC_V1_URN = "urn:ampas:aces:transformId:v1.5:ACEScsc.Academy.ACES_to_ACEScct.a1.0.3"
VALID_CSC_V2_URN = "urn:ampas:aces:transformId:v2.0:CSC.Academy.ACES_to_ACEScct.a2.v1"


class TestCorrectPlacements:
    """Correct URN placements should not raise."""

    def test_idt_in_input(self):
        it = amf.InputTransformType(transform_id=VALID_IDT_URN, applied=False)
        assert it.transform_id == VALID_IDT_URN

    def test_acescsc_in_input(self):
        it = amf.InputTransformType(transform_id=VALID_CSC_V1_URN, applied=False)
        assert it.transform_id == VALID_CSC_V1_URN

    def test_v2_input_in_input(self):
        it = amf.InputTransformType(transform_id=VALID_INPUT_V2_URN, applied=False)
        assert it.transform_id == VALID_INPUT_V2_URN

    def test_v2_csc_in_input(self):
        it = amf.InputTransformType(
            transform_id="urn:ampas:aces:transformId:v2.0:CSC.Academy.ACES_to_ACEScct.a2.v1",
            applied=False,
        )
        assert it.transform_id is not None

    def test_rrtodt_in_output(self):
        ot = amf.OutputTransformType(transform_id=VALID_ODT_URN, applied=False)
        assert ot.transform_id == VALID_ODT_URN

    def test_v2_output_in_output(self):
        ot = amf.OutputTransformType(transform_id=VALID_OUTPUT_V2_URN, applied=False)
        assert ot.transform_id == VALID_OUTPUT_V2_URN

    def test_lmt_in_look(self):
        lt = amf.LookTransformType(transform_id=VALID_LMT_URN, applied=True)
        assert lt.transform_id == VALID_LMT_URN

    def test_v2_look_in_look(self):
        lt = amf.LookTransformType(transform_id=VALID_LOOK_V2_URN, applied=True)
        assert lt.transform_id == VALID_LOOK_V2_URN

    def test_csc_in_working_space(self):
        ws = amf.WorkingSpaceTransformType(transform_id=VALID_CSC_V1_URN)
        assert ws.transform_id == VALID_CSC_V1_URN

    def test_v2_csc_in_working_space(self):
        ws = amf.WorkingSpaceTransformType(transform_id=VALID_CSC_V2_URN)
        assert ws.transform_id == VALID_CSC_V2_URN

    def test_none_transform_id_accepted(self):
        it = amf.InputTransformType(transform_id=None, applied=False)
        assert it.transform_id is None


class TestPydanticCatchesMisplacement:
    """Pydantic raises ValueError when constructing with wrong URN prefix."""

    # -- Input transform misplacements --

    def test_odt_in_input_raises(self):
        with pytest.raises(ValueError, match="not valid for InputTransform"):
            amf.InputTransformType(transform_id=VALID_ODT_URN, applied=False)

    def test_lmt_in_input_raises(self):
        with pytest.raises(ValueError, match="not valid for InputTransform"):
            amf.InputTransformType(transform_id=VALID_LMT_URN, applied=False)

    def test_v2_output_in_input_raises(self):
        with pytest.raises(ValueError, match="not valid for InputTransform"):
            amf.InputTransformType(transform_id=VALID_OUTPUT_V2_URN, applied=False)

    def test_v2_look_in_input_raises(self):
        with pytest.raises(ValueError, match="not valid for InputTransform"):
            amf.InputTransformType(transform_id=VALID_LOOK_V2_URN, applied=False)

    # -- Output transform misplacements --

    def test_idt_in_output_raises(self):
        with pytest.raises(ValueError, match="not valid for OutputTransform"):
            amf.OutputTransformType(transform_id=VALID_IDT_URN, applied=False)

    def test_lmt_in_output_raises(self):
        with pytest.raises(ValueError, match="not valid for OutputTransform"):
            amf.OutputTransformType(transform_id=VALID_LMT_URN, applied=False)

    def test_v2_input_in_output_raises(self):
        with pytest.raises(ValueError, match="not valid for OutputTransform"):
            amf.OutputTransformType(transform_id=VALID_INPUT_V2_URN, applied=False)

    # -- Look transform misplacements --

    def test_idt_in_look_raises(self):
        with pytest.raises(ValueError, match="not valid for LookTransform"):
            amf.LookTransformType(transform_id=VALID_IDT_URN, applied=True)

    def test_odt_in_look_raises(self):
        with pytest.raises(ValueError, match="not valid for LookTransform"):
            amf.LookTransformType(transform_id=VALID_ODT_URN, applied=True)

    def test_v2_output_in_look_raises(self):
        with pytest.raises(ValueError, match="not valid for LookTransform"):
            amf.LookTransformType(transform_id=VALID_OUTPUT_V2_URN, applied=True)

    def test_v2_input_in_look_raises(self):
        with pytest.raises(ValueError, match="not valid for LookTransform"):
            amf.LookTransformType(transform_id=VALID_INPUT_V2_URN, applied=True)

    # -- WorkingSpace transform misplacements --

    def test_idt_in_working_space_raises(self):
        with pytest.raises(ValueError, match="not valid for WorkingSpaceTransform"):
            amf.WorkingSpaceTransformType(transform_id=VALID_IDT_URN)

    def test_odt_in_working_space_raises(self):
        with pytest.raises(ValueError, match="not valid for WorkingSpaceTransform"):
            amf.WorkingSpaceTransformType(transform_id=VALID_ODT_URN)

    def test_lmt_in_working_space_raises(self):
        with pytest.raises(ValueError, match="not valid for WorkingSpaceTransform"):
            amf.WorkingSpaceTransformType(transform_id=VALID_LMT_URN)
