# SPDX-License-Identifier: Apache-2.0
"""Tests for CLI commands."""

import pytest
from click.testing import CliRunner
from pathlib import Path

from aces_amf_lib import load_amf, save_amf
from aces_amf_utils.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def sample_amf(tmp_path):
    """Create a sample AMF file for testing."""
    from aces_amf_utils import AMFBuilder

    path = tmp_path / "sample.amf"
    amf = (
        AMFBuilder()
        .with_description("CLI Test")
        .author("Tester", "test@example.com")
        .input_transform(
            transform_id="urn:ampas:aces:transformId:v1.5:IDT.ARRI.ARRI-LogC4.a1.v1"
        )
        .output_transform(
            transform_id="urn:ampas:aces:transformId:v1.5:ODT.Academy.Rec709_100nits_dim.a1.0.3"
        )
        .build()
    )
    save_amf(amf, path)
    return path


class TestMainGroup:
    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "AMF" in result.output

    def test_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0


class TestInfoCommand:
    def test_info(self, runner, sample_amf):
        result = runner.invoke(main, ["info", str(sample_amf)])
        assert result.exit_code == 0
        assert "CLI Test" in result.output
        assert "Tester" in result.output

    def test_info_verbose(self, runner, sample_amf):
        result = runner.invoke(main, ["info", "-v", str(sample_amf)])
        assert result.exit_code == 0
        assert "CLI Test" in result.output
        assert "Input Transform" in result.output


class TestValidateCommand:
    def test_validate_valid_file(self, runner, sample_amf):
        result = runner.invoke(main, ["validate", str(sample_amf)])
        # Should either pass or only have warnings (not errors from schema)
        assert "sample.amf" in result.output

    def test_validate_schema_only(self, runner, sample_amf):
        result = runner.invoke(main, ["validate", "--schema-only", str(sample_amf)])
        assert "sample.amf" in result.output

    def test_validate_nonexistent(self, runner):
        result = runner.invoke(main, ["validate", "/nonexistent.amf"])
        assert result.exit_code != 0


class TestCreateCommand:
    def test_create_basic(self, runner, tmp_path):
        out = tmp_path / "new.amf"
        result = runner.invoke(main, [
            "create", str(out),
            "-d", "New AMF",
            "--author", "Creator",
        ])
        assert result.exit_code == 0
        assert out.exists()

        amf = load_amf(out)
        assert amf.amf_info.description == "New AMF"

    def test_create_with_transforms(self, runner, tmp_path):
        out = tmp_path / "with_transforms.amf"
        result = runner.invoke(main, [
            "create", str(out),
            "--idt", "urn:ampas:aces:transformId:v1.5:IDT.ARRI.ARRI-LogC4.a1.v1",
            "--odt", "urn:ampas:aces:transformId:v1.5:ODT.Academy.Rec709_100nits_dim.a1.0.3",
        ])
        assert result.exit_code == 0
        assert out.exists()

    def test_create_no_overwrite(self, runner, tmp_path):
        out = tmp_path / "existing.amf"
        out.write_text("placeholder")
        result = runner.invoke(main, ["create", str(out)])
        assert result.exit_code != 0
        assert "exists" in result.output.lower()

    def test_create_force_overwrite(self, runner, tmp_path):
        out = tmp_path / "existing.amf"
        out.write_text("placeholder")
        result = runner.invoke(main, ["create", str(out), "--force"])
        assert result.exit_code == 0


class TestConvertCommand:
    def test_convert(self, runner, sample_amf, tmp_path):
        out = tmp_path / "converted.amf"
        result = runner.invoke(main, ["convert", str(sample_amf), "-o", str(out)])
        assert result.exit_code == 0
        assert out.exists()

    def test_convert_default_output(self, runner, sample_amf):
        result = runner.invoke(main, ["convert", str(sample_amf)])
        assert result.exit_code == 0
        expected = sample_amf.with_stem(sample_amf.stem + "_v2")
        assert expected.exists()


class TestDiffCommand:
    def test_diff_identical(self, runner, sample_amf, tmp_path):
        copy = tmp_path / "copy.amf"
        amf = load_amf(sample_amf)
        save_amf(amf, copy)
        result = runner.invoke(main, ["diff", str(sample_amf), str(copy)])
        assert result.exit_code == 0
        assert "identical" in result.output.lower()

    def test_diff_different(self, runner, tmp_path):
        from aces_amf_utils import AMFBuilder

        f1 = tmp_path / "a.amf"
        f2 = tmp_path / "b.amf"
        save_amf(AMFBuilder().with_description("A").build(), f1)
        save_amf(AMFBuilder().with_description("B").build(), f2)

        result = runner.invoke(main, ["diff", str(f1), str(f2)])
        assert result.exit_code == 1
        assert "difference" in result.output.lower()


class TestAddCdlCommand:
    def test_add_cdl(self, runner, sample_amf, tmp_path):
        out = tmp_path / "with_cdl.amf"
        result = runner.invoke(main, [
            "add-cdl", str(sample_amf),
            "--slope", "1.2", "1.0", "0.8",
            "--saturation", "0.95",
            "-d", "Primary grade",
            "-o", str(out),
        ])
        assert result.exit_code == 0
        assert out.exists()

        amf = load_amf(out)
        assert len(amf.pipeline.look_transforms) >= 1


class TestComputeHashesCommand:
    def test_compute_hash(self, runner, sample_amf):
        result = runner.invoke(main, ["compute-hashes", str(sample_amf)])
        assert result.exit_code == 0
        assert "SHA256" in result.output

    def test_compute_hash_md5(self, runner, sample_amf):
        result = runner.invoke(main, ["compute-hashes", str(sample_amf), "--algorithm", "md5"])
        assert result.exit_code == 0
        assert "MD5" in result.output


class TestTransformsCommand:
    def test_transforms_list(self, runner):
        result = runner.invoke(main, ["transforms", "list", "-n", "5"])
        assert result.exit_code == 0
        assert "transform(s)" in result.output

    def test_transforms_categories(self, runner):
        result = runner.invoke(main, ["transforms", "categories"])
        assert result.exit_code == 0

    def test_transforms_info(self, runner):
        result = runner.invoke(main, [
            "transforms", "info",
            "urn:ampas:aces:transformId:v2.0:CSC.Academy.ACES_to_ACEScc.a2.v1",
        ])
        assert result.exit_code == 0
        assert "ACES" in result.output
