# SPDX-License-Identifier: Apache-2.0
"""AMF CLI tools."""

import importlib

import click

from .validate import validate
from .info import info
from .convert import convert
from .create import create
from .edit import add_cdl, compute_hashes
from .diff_cmd import diff
from .transforms import transforms
from .templates import template


def _load_registry(dotted_path: str):
    """Load a TransformRegistry from a 'module:ClassName' dotted path."""
    if ":" not in dotted_path:
        raise click.ClickException(
            f"Invalid registry path {dotted_path!r}. Expected 'module:ClassName'."
        )
    module_path, class_name = dotted_path.rsplit(":", 1)
    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        raise click.ClickException(f"Cannot import registry module {module_path!r}: {e}")
    cls = getattr(module, class_name, None)
    if cls is None:
        raise click.ClickException(f"Class {class_name!r} not found in module {module_path!r}")
    return cls()


@click.group()
@click.version_option(package_name="aces-amf-utils")
@click.option(
    "--registry",
    default="aces_transforms:ACESTransformRegistry",
    show_default=True,
    help="Transform registry as 'module:ClassName'. Used for transform ID validation.",
    metavar="MODULE:CLASS",
)
@click.pass_context
def main(ctx, registry):
    """ACES Metadata File (AMF) utilities."""
    ctx.ensure_object(dict)
    ctx.obj["transform_registry"] = _load_registry(registry)


main.add_command(validate)
main.add_command(info)
main.add_command(convert)
main.add_command(create)
main.add_command(add_cdl)
main.add_command(compute_hashes)
main.add_command(diff)
main.add_command(transforms)
main.add_command(template)
