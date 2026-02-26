# SPDX-License-Identifier: Apache-2.0
"""
Fluent builder for constructing AMF files.

Usage:
    from aces_amf_utils import AMFBuilder

    amf = (AMFBuilder()
        .with_description("My Show - Ep 1")
        .author("Jane Doe", "jane@example.com")
        .input_transform(transform_id="urn:ampas:aces:transformId:v1.5:IDT.ARRI...")
        .look_transform(file="grade.clf", description="Primary grade")
        .output_transform(transform_id="urn:ampas:aces:transformId:v1.5:ODT.Academy...")
        .build())
"""

from __future__ import annotations


from aces_amf_lib import AcesMetadataFile, amf_v2, cdl_look_transform, minimal_amf


class AMFBuilder:
    """Fluent builder for ACES Metadata Files.

    Each method returns ``self`` for chaining. Call ``.build()``
    to get the final ``AcesMetadataFile`` instance.
    """

    def __init__(self, aces_version: tuple[int, int, int] = (1, 3, 0)):
        self._amf = minimal_amf(aces_version=aces_version)

    def with_description(self, text: str) -> AMFBuilder:
        """Set the top-level AMF description."""
        self._amf.amf_info.description = text
        return self

    def with_pipeline_description(self, text: str) -> AMFBuilder:
        """Set the pipeline description."""
        self._amf.pipeline.pipeline_info.description = text
        return self

    def author(self, name: str, email: str = "") -> AMFBuilder:
        """Add an author."""
        self._amf.amf_info.author.append(amf_v2.AuthorType(name=name, email_address=email))
        return self

    def clip_id(
        self,
        clip_name: str,
        *,
        file: str | None = None,
        uuid: str | None = None,
        sequence: dict | None = None,
    ) -> AMFBuilder:
        """Set clip identification.

        Only one of ``file``, ``uuid``, or ``sequence`` should be specified
        (per XSD choice constraint).

        Args:
            clip_name: The clip name.
            file: File reference for the clip.
            uuid: UUID for the clip.
            sequence: Sequence info dict with keys: idx, min, max.
        """
        clip_id_obj = amf_v2.ClipIdType(clip_name=clip_name)

        if file:
            clip_id_obj.file = file
        elif uuid:
            clip_id_obj.uuid = uuid
        elif sequence:
            seq = amf_v2.SequenceType(
                idx=str(sequence.get("idx", "#")),
                value=str(sequence.get("min", "")),
            )
            if "min" in sequence:
                seq.min_value = str(sequence["min"])
            if "max" in sequence:
                seq.max_value = str(sequence["max"])
            clip_id_obj.sequence = seq

        self._amf.clip_id = clip_id_obj
        return self

    def input_transform(
        self,
        *,
        transform_id: str | None = None,
        file: str | None = None,
        description: str | None = None,
        applied: bool = False,
    ) -> AMFBuilder:
        """Set the input transform."""
        it = amf_v2.InputTransformType(applied=applied)
        if transform_id:
            it.transform_id = transform_id
        if file:
            it.file = file
        if description:
            it.description = description
        self._amf.pipeline.input_transform = it
        return self

    def look_transform(
        self,
        *,
        description: str | None = None,
        transform_id: str | None = None,
        file: str | None = None,
        applied: bool = False,
        cdl: dict | None = None,
    ) -> AMFBuilder:
        """Add a look transform.

        If ``cdl`` is provided, creates a CDL look transform.
        Otherwise creates a file/transform_id reference look transform.

        Args:
            description: Description of the look.
            transform_id: Transform URN.
            file: File reference.
            applied: Whether this transform has been applied.
            cdl: CDL dict with keys: asc_sop (slope/offset/power), asc_sat.
        """
        if cdl:
            sop = cdl.get("asc_sop", {})
            lt = cdl_look_transform(
                slope=sop.get("slope"),
                offset=sop.get("offset"),
                power=sop.get("power"),
                saturation=cdl.get("asc_sat"),
            )
            if description:
                lt.description = description
            lt.applied = applied
            self._amf.pipeline.look_transform.append(lt)
        else:
            lt = amf_v2.LookTransformType(applied=applied)
            if description:
                lt.description = description
            if transform_id:
                lt.transform_id = transform_id
            if file:
                lt.file = file
            self._amf.pipeline.look_transform.append(lt)
        return self

    def output_transform(
        self,
        *,
        transform_id: str | None = None,
        description: str | None = None,
        applied: bool = False,
    ) -> AMFBuilder:
        """Set the output transform."""
        ot = amf_v2.OutputTransformType(applied=applied)
        if transform_id:
            ot.transform_id = transform_id
        if description:
            ot.description = description
        self._amf.pipeline.output_transform = ot
        return self

    def set_aces_version(self, major: int, minor: int, patch: int) -> AMFBuilder:
        """Set the ACES system version."""
        self._amf.pipeline.pipeline_info.system_version = amf_v2.VersionType(
            major_version=str(major),
            minor_version=str(minor),
            patch_version=str(patch),
        )
        return self

    def build(self) -> AcesMetadataFile:
        """Return the constructed AcesMetadataFile instance."""
        return self._amf
