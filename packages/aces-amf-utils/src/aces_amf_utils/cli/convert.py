# SPDX-License-Identifier: Apache-2.0
"""Convert command (v1 to v2)."""

from pathlib import Path

import click

from aces_amf_lib import load_amf, save_amf


@click.command()
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Output path. Defaults to <original>_v2.amf.",
)
@click.option("--force", "-f", is_flag=True, help="Overwrite output if it exists.")
def convert(file, output, force):
    """Convert an AMF v1 file to v2 format.

    The file is loaded (v1 is auto-upgraded on read) and re-written as v2.
    """
    path = Path(file)
    amf = load_amf(path)

    if output:
        out_path = Path(output)
    else:
        out_path = path.with_stem(path.stem + "_v2")

    if out_path.exists() and not force:
        raise click.ClickException(f"Output file exists: {out_path}. Use --force to overwrite.")

    save_amf(amf, out_path)
    click.echo(f"Converted {path.name} -> {out_path.name}")
