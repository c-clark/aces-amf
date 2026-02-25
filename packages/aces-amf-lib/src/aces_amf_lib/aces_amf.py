# SPDX-License-Identifier: Apache-2.0
"""
High-level interface for working with ACES AMF files.
"""

import copy

from pathlib import Path
from uuid import uuid4

from . import amf_utilities
from . import amf_v2
from .amf_v2 import AuthorType, InputTransformType, LookTransformType, OutputTransformType


class ACESAMF:
    """
    Provides a high-level interface for working with ACES AMF files.
    """

    def __init__(self, aces_version: tuple[int, int, int] = (1, 3, 0)):
        """
        Initialize an ACESAMF object.

        Args:
            aces_version: ACES system version as (major, minor, patch).
                         Defaults to (1, 3, 0).
        """
        self.amf = amf_utilities.minimal_amf(aces_version=aces_version)
        self.ns_map = copy.deepcopy(amf_utilities.DEFAULT_NS_MAP)

        # Track if the AMF has been modified since last read/write
        self._has_modifications = False

    @classmethod
    def from_file(cls, amf_path: Path | str) -> "ACESAMF":
        """
        Read the provided AMF file and return the parsed data.
        """
        amf, ns_map = amf_utilities.from_amf_file(Path(amf_path))
        obj = cls()
        obj.amf = amf
        obj.ns_map = ns_map
        return obj

    @classmethod
    def from_data(cls, amf_data: bytes) -> "ACESAMF":
        """
        Read the provided AMF data and return the parsed data.
        """
        amf, ns_map = amf_utilities.from_amf_data(amf_data)
        obj = cls()
        obj.amf = amf
        obj.ns_map = ns_map
        return obj

    def dump(self) -> str:
        """
        Write the AMF data to a string.
        """
        self.rev_up()
        return amf_utilities.dump_amf(self.amf, self.ns_map)

    def write(self, out: Path | str) -> None:
        """
        Write the AMF data to a file.
        """
        self.rev_up()
        with open(Path(out), "w") as file:
            amf_utilities.write_amf(file, self.amf, self.ns_map)

    def _ensure_minimal_amf_structure(self):
        """
        Ensures that the minimal AMF structure is in place.
        """
        if self.amf.pipeline is None or self.amf.pipeline.pipeline_info is None:
            default_version = amf_v2.VersionType(major_version=1, minor_version=3, patch_version=0)
            pipeline_info = amf_v2.PipelineInfoType(
                date_time=amf_utilities.amf_date_time_now(),
                uuid=uuid4().urn,
                system_version=default_version,
            )
            if self.amf.pipeline is None:
                self.amf.pipeline = amf_v2.PipelineType(pipeline_info=pipeline_info)
            else:
                self.amf.pipeline.pipeline_info = pipeline_info
            self._has_modifications = True

        if self.amf.amf_info is None:
            self.amf.amf_info = amf_v2.InfoType(date_time=amf_utilities.amf_date_time_now(), uuid=uuid4().urn)
            self._has_modifications = True

    @property
    def aces_version(self) -> tuple[int, int, int]:
        """Get the ACES system version as (major, minor, patch)."""
        if self.amf.pipeline and self.amf.pipeline.pipeline_info and self.amf.pipeline.pipeline_info.system_version:
            sv = self.amf.pipeline.pipeline_info.system_version
            return (sv.major_version, sv.minor_version, sv.patch_version)
        return (1, 3, 0)  # Default

    def set_aces_version(self, major: int, minor: int, patch: int) -> None:
        """
        Set the ACES system version.

        Args:
            major: Major version number
            minor: Minor version number
            patch: Patch version number
        """
        self._ensure_minimal_amf_structure()
        self.amf.pipeline.pipeline_info.system_version = amf_v2.VersionType(
            major_version=major,
            minor_version=minor,
            patch_version=patch
        )
        self._has_modifications = True

    @property
    def aces_major_version(self) -> int | None:
        """
        The major version of the ACES system.
        """
        if self.amf.pipeline is not None and self.amf.pipeline.pipeline_info is not None:
            if self.amf.pipeline.pipeline_info.system_version is not None:
                return self.amf.pipeline.pipeline_info.system_version.major_version

        return None

    @property
    def amf_description(self) -> str | None:
        """
        A description of the AMF, often a show name.
        """
        if self.amf.amf_info is not None:
            return self.amf.amf_info.description

        return None

    @amf_description.setter
    def amf_description(self, value: str):
        self._ensure_minimal_amf_structure()
        self.amf.amf_info.description = value
        self._has_modifications = True

    @property
    def pipeline_description(self) -> str | None:
        """
        A description of the pipeline.
        """
        if self.amf.pipeline is not None and self.amf.pipeline.pipeline_info is not None:
            return self.amf.pipeline.pipeline_info.description

        return None

    @pipeline_description.setter
    def pipeline_description(self, value: str):
        self._ensure_minimal_amf_structure()
        self.amf.pipeline.pipeline_info.description = value
        self._has_modifications = True

    @property
    def amf_authors(self) -> list[AuthorType]:
        """
        The authors of the AMF.
        """
        if self.amf.amf_info is not None:
            return self.amf.amf_info.author

        return []

    def add_amf_author(self, author: AuthorType):
        """
        Add an author to the AMF.
        """
        self._ensure_minimal_amf_structure()
        self.amf.amf_info.author.append(author)
        self._has_modifications = True

    def clear_amf_authors(self):
        """
        Clear all authors from the AMF.
        """
        if not self.amf.amf_info:
            return

        self.amf.amf_info.author = []
        self._has_modifications = True

    def rev_up(self, force: bool = False):
        """
        If there are modifications, update housekeeping fields to update the modification date and unique identifiers.

        If ``force`` is ``True``, update the housekeeping fields even if there haven't been any modifications since the last load or save.

        Also clears the has_modifications flag.

        This is called automatically by the ``dump`` and ``write`` methods - users usually should not need to call this method directly.
        """
        if not force and not self._has_modifications:
            return

        self._ensure_minimal_amf_structure()

        self.amf.amf_info.date_time.modification_date_time = amf_utilities.amf_xml_date_time()
        self.amf.amf_info.uuid = uuid4().urn

        self.amf.pipeline.pipeline_info.date_time.modification_date_time = amf_utilities.amf_xml_date_time()
        self.amf.pipeline.pipeline_info.uuid = uuid4().urn

        self._has_modifications = False

    def set_input_transform(self, input_transform: InputTransformType):
        """
        Set the input transform for the AMF.
        """
        self._ensure_minimal_amf_structure()
        self.amf.pipeline.input_transform = input_transform

        self._has_modifications = True

    def set_output_transform(self, output_transform: OutputTransformType):
        """
        Set the output transform for the AMF.
        """
        self._ensure_minimal_amf_structure()
        self.amf.pipeline.output_transform = output_transform

        self._has_modifications = True

    def add_cdl_look_transform(self, cdl_dict: dict):
        """
        Add a CDL look transform to the AMF.
        """
        self._ensure_minimal_amf_structure()
        sop_dict = cdl_dict.get("asc_sop", {})
        slope = sop_dict.get("slope", [1.0, 1.0, 1.0])
        offset = sop_dict.get("offset", [0.0, 0.0, 0.0])
        power = sop_dict.get("power", [1.0, 1.0, 1.0])
        saturation = cdl_dict.get("asc_sat", 1.0)
        if len(slope) != 3 or len(offset) != 3 or len(power) != 3:
            raise ValueError("Invalid CDL SOP node values")
        look_transform = amf_utilities.cdl_look_transform(
            slope=tuple(slope), offset=tuple(offset), power=tuple(power), saturation=saturation
        )
        self.amf.pipeline.look_transform.append(look_transform)

        self._has_modifications = True

    def add_look_transform(self, look_transform: LookTransformType):
        self._ensure_minimal_amf_structure()
        self.amf.pipeline.look_transform.append(look_transform)

        self._has_modifications = True
