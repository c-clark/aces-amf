# SPDX-License-Identifier: Apache-2.0
"""AMF CLI tools."""

import click

from .validate import validate
from .info import info
from .convert import convert
from .create import create
from .edit import add_cdl, compute_hashes
from .diff_cmd import diff
from .transforms import transforms


@click.group()
@click.version_option(package_name="aces-amf-utils")
def main():
    """ACES Metadata File (AMF) utilities."""


main.add_command(validate)
main.add_command(info)
main.add_command(convert)
main.add_command(create)
main.add_command(add_cdl)
main.add_command(compute_hashes)
main.add_command(diff)
main.add_command(transforms)
