#!/usr/bin/env bash
# Regenerate xsdata-pydantic bindings from XSD schemas.
#
# Usage:
#   ./generate_bindings.sh          # regenerate both v1 and v2
#   ./generate_bindings.sh v1       # regenerate v1 only
#   ./generate_bindings.sh v2       # regenerate v2 only

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
LIB_SRC="$REPO_ROOT/packages/aces-amf-lib/src"
SCHEMA_DIR="$LIB_SRC/aces_amf_lib/data/amf-schema"

# Resolve xsdata to an absolute path so subshells can find it
XSDATA="$(command -v xsdata 2>/dev/null || echo "$REPO_ROOT/.venv/bin/xsdata")"
XSDATA="$(realpath "$XSDATA")"
if [[ ! -x "$XSDATA" ]]; then
    echo "ERROR: xsdata not found. Install with: uv pip install 'xsdata[cli]'" >&2
    exit 1
fi

generate() {
    local version="$1"
    local schema="$SCHEMA_DIR/$version/acesMetadataFile.xsd"
    local outdir="$LIB_SRC/aces_amf_lib/amf_$version"
    local package="aces_amf_lib.amf_$version"

    if [[ ! -f "$schema" ]]; then
        echo "ERROR: Schema not found: $schema" >&2
        exit 1
    fi

    echo "Generating $package from $schema ..."

    # Generate into a temp directory to avoid import side-effects.
    # xsdata validate_imports tries to import the parent package which
    # can fail if other subpackages are mid-generation.
    local tmpdir
    tmpdir="$(mktemp -d)"
    trap "rm -rf '$tmpdir'" RETURN

    (cd "$tmpdir" && "$XSDATA" generate \
        --output pydantic \
        --package "$package" \
        --include-header \
        "$schema") || true

    # Replace only the versioned subpackage, never the parent __init__.py
    if [[ -d "$tmpdir/aces_amf_lib/amf_$version" ]]; then
        rm -rf "$outdir"
        mv "$tmpdir/aces_amf_lib/amf_$version" "$outdir"
    else
        echo "ERROR: Expected output not found in temp dir" >&2
        exit 1
    fi

    rm -rf "$tmpdir"
    # Clear the RETURN trap since we cleaned up manually
    trap - RETURN

    # Post-generation patches (v2 only)
    if [[ "$version" == "v2" ]]; then
        _patch_v2_bindings "$outdir"
    fi

    echo "  -> $outdir"
}

_patch_v2_bindings() {
    local outdir="$1"
    local target="$outdir/aces_metadata_file.py"

    if [[ ! -f "$target" ]]; then
        echo "WARNING: Cannot patch — $target not found" >&2
        return
    fi

    echo "  Patching $target: merging working_location + look_transform into compound field ..."

    # Use Python for reliable AST-safe patching of the generated bindings.
    # This replaces the separate working_location and look_transform fields
    # on PipelineType with a single compound field that preserves element
    # ordering (required for workingLocation positional semantics).
    python3 - "$target" << 'PYSCRIPT'
import re, sys

target = sys.argv[1]
with open(target, "r") as f:
    content = f.read()

# --- 1. Replace the two separate fields with one compound field ---
# Match the working_location field definition (multiline)
wl_pattern = re.compile(
    r'    working_location: list\[EmptyType\] = field\(\n'
    r'        default_factory=list,\n'
    r'        metadata=\{[^}]+\},?\n'
    r'    \)\n',
    re.DOTALL,
)
# Match the look_transform field definition (multiline)
lt_pattern = re.compile(
    r'    look_transform: list\[LookTransformType\] = field\(\n'
    r'        default_factory=list,\n'
    r'        metadata=\{[^}]+\},?\n'
    r'    \)\n',
    re.DOTALL,
)

compound_field = '''\
    working_location_or_look_transform: list[EmptyType | LookTransformType] = (
        field(
            default_factory=list,
            metadata={
                "type": "Elements",
                "choices": (
                    {
                        "name": "workingLocation",
                        "type": EmptyType,
                        "namespace": "urn:ampas:aces:amf:v2.0",
                    },
                    {
                        "name": "lookTransform",
                        "type": LookTransformType,
                        "namespace": "urn:ampas:aces:amf:v2.0",
                    },
                ),
            },
        )
    )
'''

# Replace working_location with the compound field, remove look_transform
if not wl_pattern.search(content):
    print("WARNING: Could not find working_location field to patch", file=sys.stderr)
    sys.exit(1)
if not lt_pattern.search(content):
    print("WARNING: Could not find look_transform field to patch", file=sys.stderr)
    sys.exit(1)

content = wl_pattern.sub(compound_field, content, count=1)
content = lt_pattern.sub("", content, count=1)

# --- 2. Append the look_transforms convenience property ---
content += '''

# --- Post-generation additions (applied by generate_bindings.sh) ---


def _pipeline_get_look_transforms(self) -> list["LookTransformType"]:
    """Read-only filtered view: only LookTransformType items from the
    compound working_location_or_look_transform field."""
    return [
        x
        for x in self.working_location_or_look_transform
        if isinstance(x, LookTransformType)
    ]


PipelineType.look_transforms = property(_pipeline_get_look_transforms)

WorkingLocationType = EmptyType
'''

with open(target, "w") as f:
    f.write(content)

print(f"  Patched {target} successfully")
PYSCRIPT

    # Patch __init__.py to import and export WorkingLocationType
    local initpy="$outdir/__init__.py"
    if [[ -f "$initpy" ]]; then
        echo "  Patching $initpy with WorkingLocationType import ..."
        sed -i '' '/^    EmptyType,$/a\
    WorkingLocationType,' "$initpy"
        sed -i '' 's/^    "EmptyType",$/    "WorkingLocationType",/' "$initpy"
    fi
}

targets=("${@:-v1 v2}")
[[ $# -eq 0 ]] && targets=(v1 v2)

for target in "${targets[@]}"; do
    case "$target" in
        v1|v2) generate "$target" ;;
        *) echo "Unknown target: $target (expected v1 or v2)" >&2; exit 1 ;;
    esac
done

echo "Done."
