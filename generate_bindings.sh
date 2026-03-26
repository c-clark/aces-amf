#!/usr/bin/env bash
# Regenerate xsdata-pydantic bindings from XSD schemas.
#
# Usage:
#   ./generate_bindings.sh          # regenerate both v1 and v2
#   ./generate_bindings.sh v1       # regenerate v1 only
#   ./generate_bindings.sh v2       # regenerate v2 only
#   ./generate_bindings.sh --gen-patches  # regenerate patch files from current committed bindings
#
# Post-generation patches live in packages/aces-amf-lib/patches/.
# Each patch is a standard unified diff applied with `patch --fuzz=2`.
# See patches/README.md for details on what each patch does and why.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
LIB_SRC="$REPO_ROOT/packages/aces-amf-lib/src"
SCHEMA_DIR="$LIB_SRC/aces_amf_lib/data/amf-schema"
PATCHES_DIR="$REPO_ROOT/packages/aces-amf-lib/patches"

# Prefer the project venv xsdata (has cli extras) over any system-level install
if [[ -x "$REPO_ROOT/.venv/bin/xsdata" ]]; then
    XSDATA="$(realpath "$REPO_ROOT/.venv/bin/xsdata")"
elif command -v xsdata &>/dev/null; then
    XSDATA="$(realpath "$(command -v xsdata)")"
else
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

    _apply_patches "$version" "$outdir"

    echo "  -> $outdir"
}

_apply_patches() {
    local version="$1"
    local target_dir="$2"

    for patch_file in "$PATCHES_DIR"/${version}_*.patch; do
        [[ -f "$patch_file" ]] || continue
        echo "  Applying $(basename "$patch_file") ..."
        patch -d "$target_dir" -p0 --fuzz=2 < "$patch_file" || {
            echo "ERROR: $(basename "$patch_file") failed to apply." >&2
            echo "  The xsdata output may have changed. Regenerate patches with:" >&2
            echo "    ./generate_bindings.sh --gen-patches" >&2
            exit 1
        }
    done
}

# --gen-patches: regenerate patch files incrementally from current bindings.
# Applies existing patches one at a time, diffing between each step to
# produce isolated per-patch diffs. Header comments are preserved.
# Run this after manually editing the generated files to capture the changes.
gen_patches() {
    local tmpdir
    tmpdir="$(mktemp -d)"
    trap "rm -rf '$tmpdir'" RETURN

    echo "Generating raw (unpatched) bindings for diffing ..."
    for version in v1 v2; do
        local schema="$SCHEMA_DIR/$version/acesMetadataFile.xsd"
        (cd "$tmpdir" && "$XSDATA" generate \
            --output pydantic \
            --package "aces_amf_lib.amf_${version}" \
            --include-header \
            "$schema") || true
    done

    mkdir -p "$PATCHES_DIR"

    for version in v1 v2; do
        local target_dir="$LIB_SRC/aces_amf_lib/amf_$version"
        local raw_dir="$tmpdir/aces_amf_lib/amf_$version"

        # Working copy starts as raw (unpatched) bindings
        local work_dir="$tmpdir/work_${version}"
        cp -r "$raw_dir" "$work_dir"

        for patch_file in "$PATCHES_DIR"/${version}_*.patch; do
            [[ -f "$patch_file" ]] || continue

            # Extract target filename from the patch (first --- line, skipping comments)
            local fname
            fname=$(grep -m1 '^--- ' "$patch_file" | sed 's/^--- //')

            # Save "before" state
            local before="$tmpdir/before_$(basename "$patch_file" .patch)"
            cp "$work_dir/$fname" "$before"

            # Get "after" state: the current repo file with all prior patches
            # already baked in. We use the actual repo file as ground truth.
            # Apply the patch to work_dir to advance it; if it fails (stale
            # patch), fall back to copying the repo file.
            local after_dir="$tmpdir/after_${version}"
            cp -r "$work_dir" "$after_dir"
            if ! patch -d "$after_dir" -p0 --fuzz=2 < "$patch_file" >/dev/null 2>&1; then
                # Patch is stale — use repo file as the target
                cp "$target_dir/$fname" "$after_dir/$fname"
            fi

            # Extract header comment block (lines starting with #)
            local header
            header=$(sed -n '/^#/p; /^[^#]/q' "$patch_file")

            # Generate incremental diff, strip timestamp-only hunks
            _write_incremental_patch "$before" "$after_dir/$fname" "$fname" "$header" "$patch_file"

            # Advance working copy to post-patch state
            cp "$after_dir/$fname" "$work_dir/$fname"
            rm -rf "$after_dir"
        done
    done

    echo "Patches written to $PATCHES_DIR"
}

_write_incremental_patch() {
    local before="$1"
    local after="$2"
    local fname="$3"
    local header="$4"
    local output="$5"

    # Generate diff with basename-only paths, strip timestamp-only hunks
    local diff_body
    diff_body=$(diff -u "$before" "$after" | \
        sed "1s|.*|--- ${fname}|; 2s|.*|+++ ${fname}|" | \
        python3 -c "
import re, sys
text = sys.stdin.read()
m = re.search(r'^@@', text, re.MULTILINE)
if not m:
    sys.stdout.write(text)
    sys.exit(0)
hdr = text[:m.start()]
body = text[m.start():]
hunks = re.split(r'(?=^@@ )', body, flags=re.MULTILINE)
ts_re = re.compile(r'\"\"\"This file was generated by xsdata')
def keep(h):
    changed = [l for l in h.splitlines() if l.startswith('+') or l.startswith('-')]
    return any(not ts_re.search(l) for l in changed)
sys.stdout.write(hdr + ''.join(h for h in hunks if not h or keep(h)))
") || true

    # Write: preserved header + blank line + diff body
    {
        if [[ -n "$header" ]]; then
            printf '%s\n\n' "$header"
        fi
        printf '%s\n' "$diff_body"
    } > "$output"

    echo "  Written $(basename "$output")"
}

# --- Main ---

if [[ "${1:-}" == "--gen-patches" ]]; then
    gen_patches
    exit 0
fi

targets=("${@:-v1 v2}")
[[ $# -eq 0 ]] && targets=(v1 v2)

for target in "${targets[@]}"; do
    case "$target" in
        v1|v2) generate "$target" ;;
        *) echo "Unknown target: $target (expected v1 or v2)" >&2; exit 1 ;;
    esac
done

echo "Done."
