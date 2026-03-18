# Binding Patches

These patch files are applied to the xsdata-generated Python bindings immediately after generation. Each patch is a standard unified diff and is applied with `patch -p0 --fuzz=2`.

## Patches

### `v1_system_version_optional.patch`
**Target:** `amf_v1/aces_metadata_file.py`

Makes `PipelineInfoType.system_version` optional (`None | VersionType`). Legacy v1 AMF files often omit `<systemVersion>`, which causes parse failures when the field is required. The v1→v2 upgrade function in `amf_helpers.py` injects a default value before conversion.

### `v2_compound_fields.patch`
**Target:** `amf_v2/aces_metadata_file.py`

Replaces the two separate `working_location` and `look_transform` fields on `PipelineType` with a single compound field:

```python
working_location_or_look_transform: list[EmptyType | LookTransformType]
```

Also appends the `look_transforms` convenience property and `WorkingLocationType = EmptyType` alias.

**Why the compound field:** The AMF v2 XSD uses `xs:choice maxOccurs="unbounded"` to allow `workingLocation` and `lookTransform` elements to be freely interleaved. xsdata generates these as two separate lists, which destroys element ordering. The compound field (xsdata `"Elements"` type with `"choices"`) preserves the original interleaved document order, which is required for correct workingLocation positional semantics.

### `v2_init_exports.patch`
**Target:** `amf_v2/__init__.py`

Adds `WorkingLocationType` to the module's imports and `__all__` so that consumers can import it from `aces_amf_lib.amf_v2` directly.

---

## Regenerating Patches

If xsdata, the XSD schemas, or the manually-applied changes evolve, regenerate the patches:

```bash
# 1. Make your edits to the generated files under src/aces_amf_lib/amf_v1/ or amf_v2/
# 2. Regenerate patch files from the current committed state
./generate_bindings.sh --gen-patches
# 3. Restore the header comments that document what/why (they are not preserved by --gen-patches)
# 4. Verify: wipe generated files and regenerate from scratch
rm -rf packages/aces-amf-lib/src/aces_amf_lib/amf_v{1,2}
./generate_bindings.sh
uv run pytest packages/ -q
```
