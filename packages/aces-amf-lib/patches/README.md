# Binding Patches

These patch files are applied to the xsdata-generated Python bindings immediately after generation. Each patch is a standard unified diff and is applied with `patch -p0 --fuzz=2`.

Patches are applied in alphabetical order with `v2_*` prefix.

## Patches

### `v2_compound_fields.patch`
**Target:** `amf/aces_metadata_file.py`

Replaces the two separate `working_location` and `look_transform` fields on `PipelineType` with a single compound field:

```python
working_location_or_look_transform: list[EmptyType | LookTransformType]
```

Also appends the `look_transforms` convenience property and `WorkingLocationType = EmptyType` alias.

**Why the compound field:** The AMF v2 XSD uses `xs:choice maxOccurs="unbounded"` to allow `workingLocation` and `lookTransform` elements to be freely interleaved. xsdata generates these as two separate lists, which destroys element ordering. The compound field (xsdata `"Elements"` type with `"choices"`) preserves the original interleaved document order, which is required for correct workingLocation positional semantics.

### `v2_init_exports.patch`
**Target:** `amf/__init__.py`

Adds `WorkingLocationType` to the module's imports and `__all__` so that consumers can import it from `aces.amf_lib.amf` directly.

### `v2_transform_type_validators.patch`
**Target:** `amf/aces_metadata_file.py`
**Depends on:** `v2_compound_fields.patch` (must be applied first for correct line offsets)

Adds `__init__` wrappers on `InputTransformType`, `OutputTransformType`, `LookTransformType`, and `WorkingSpaceTransformType` that validate transform ID URN prefixes match the container type. Uses `V2_*` prefix constants (accepts both v1.5 and v2.0 URNs).

---

## Regenerating Patches

If xsdata, the XSD schemas, or the manually-applied changes evolve, regenerate the patches:

```bash
# 1. Make your edits to the generated files under src/aces.amf_lib/amf/
# 2. Regenerate patch files from the current committed state
./generate_bindings.sh --gen-patches
# 3. Verify: wipe generated files and regenerate from scratch
rm -rf packages/aces-amf-lib/src/aces.amf_lib/amf
./generate_bindings.sh
uv run pytest packages/ -q
```
