# SPDX-License-Identifier: Apache-2.0
"""Create command."""

from pathlib import Path

import click

from aces_amf_lib import save_amf

from ..builder import AMFBuilder


@click.command()
@click.argument("output", type=click.Path())
@click.option("--description", "-d", help="AMF description.")
@click.option("--author", help="Author name.")
@click.option("--author-email", help="Author email.")
@click.option("--idt", "idt_id", help="Input transform ID (URN).")
@click.option("--odt", "odt_id", help="Output transform ID (URN).")
@click.option(
    "--aces-version",
    default="1.3.0",
    help="ACES version (major.minor.patch). Default: 1.3.0",
)
@click.option("--force", "-f", is_flag=True, help="Overwrite output if it exists.")
def create(output, description, author, author_email, idt_id, odt_id, aces_version, force):
    """Create a new AMF file."""
    out_path = Path(output)

    if out_path.exists() and not force:
        raise click.ClickException(f"Output file exists: {out_path}. Use --force to overwrite.")

    parts = aces_version.split(".")
    if len(parts) != 3:
        raise click.ClickException("ACES version must be major.minor.patch (e.g. 1.3.0)")
    version = tuple(int(p) for p in parts)

    builder = AMFBuilder(aces_version=version)

    if description:
        builder.with_description(description)
    if author:
        builder.author(author, author_email or "")
    if idt_id:
        builder.input_transform(transform_id=idt_id)
    if odt_id:
        builder.output_transform(transform_id=odt_id)

    amf = builder.build()
    save_amf(amf, out_path)
    click.echo(f"Created {out_path}")
