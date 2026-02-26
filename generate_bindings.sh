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

    echo "  -> $outdir"
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