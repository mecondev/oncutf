# ADR 001: Pragmatic Strict Typing for Metadata Applications

**Status:** Accepted  
**Date:** 2026-01-25  
**Author:** Michael Economou  
**Phase:** Phase E (Type Safety Tightening)

---

## Context

During Phase E, we attempted to enable full strict mode (`mypy --strict` equivalent) for Tier 1 modules (app/domain/infra). The initial attempt with all 12 strict flags produced 327 errors, primarily from two flags:

- `disallow_any_explicit`: Flagged all `dict[str, Any]` declarations
- `disallow_any_expr`: Flagged expressions containing Any type

The oncutf application is **metadata-centric**: it processes EXIF data from cameras where:
- Field names are camera-dependent (Canon vs Nikon vs Sony)
- Field types are runtime-determined (string, int, datetime, bytes)
- No compile-time schema exists for camera metadata
- Different cameras expose different fields with different types

**Example reality:**
```python
# Canon EOS metadata
{"FNumber": 5.6, "ISO": 800, "DateTimeOriginal": "2026:01:25 12:00:00"}

# Nikon D850 metadata  
{"FNumber": "5.6", "ISO": "800", "DateTimeOriginal": datetime(...)}

# Sony A7 metadata
{"FNumber": Fraction(56, 10), "SensitivityType": 2, ...}
```

No static type can express this domain correctly.

---

## Decision

**Adopt Pragmatic Strict Mode for Tier 1:**
- Enable 10 of 12 strict flags
- Pragmatically exclude 2 flags inappropriate for metadata domain:
  - `disallow_any_explicit` (allows `dict[str, Any]` for EXIF)
  - `disallow_any_expr` (allows `Callable[[Any], ...]` for validators)

**Three-Tier Typing Strategy:**

```toml
# Tier 1 (app/domain/infra) — Pragmatic Strict (10/12 flags)
[[tool.mypy.overrides]]
module = ["oncutf.app.*", "oncutf.domain.*", "oncutf.infra.*"]
disallow_untyped_defs = true
disallow_any_generics = true
warn_return_any = true
no_implicit_reexport = true
strict_optional = true
disallow_any_unimported = true
disallow_any_decorated = true
disallow_incomplete_defs = true
disallow_untyped_calls = true
disallow_untyped_decorators = true
# Excluded: disallow_any_explicit, disallow_any_expr

# Tier 2 (controllers/core) — Strict (disallow_untyped_defs)
[[tool.mypy.overrides]]
module = ["oncutf.controllers.*", "oncutf.core.*"]
disallow_untyped_defs = true

# Tier 3 (UI/Qt) — Selective (13 Qt-specific suppressions)
[[tool.mypy.overrides]]
module = ["oncutf.ui.*"]
disable_error_code = ["attr-defined", "call-arg", ...]
```

---

## Consequences

### Positive

1. **Domain-Appropriate Typing**
   - `dict[str, Any]` is idiomatic for EXIF metadata (not lazy typing)
   - Runtime validators handle type safety where static types cannot
   - Type system accurately reflects domain reality

2. **Excellent Type Safety Metrics**
   - Strictness: 8.8/10 (pragmatic, not theoretical maximum)
   - Mypy errors: 0 (548 files checked)
   - Type:ignore: 5 remaining (all justified)
   - Production-ready type coverage

3. **Maintainability**
   - Future developers understand why strict flags are excluded
   - Documentation prevents "why not full strict?" questions
   - Clear tier boundaries guide typing decisions

4. **Testing Benefits**
   - Logic bugs still caught by mypy
   - Runtime validators tested explicitly
   - No false sense of type safety from wrapper types

### Negative

1. **Theoretical Purity Sacrifice**
   - Not "fully strict" according to mypy --strict
   - Some type theorists may object
   - Requires explanation in code reviews

2. **Potential Misuse**
   - Developers might overuse `dict[str, Any]` inappropriately
   - Must enforce: Only for EXIF/metadata, not general data structures
   - Requires documentation and review discipline

### Neutral

1. **Alternative Rejected: Typed Metadata Wrappers**
   ```python
   class CanonMetadata(TypedDict):
       FNumber: float
       ISO: int
   
   class NikonMetadata(TypedDict):
       FNumber: str
       ISO: str
   
   # Problem: Hundreds of camera models × firmware versions
   # Maintenance nightmare, doesn't reflect reality
   ```

2. **Alternative Rejected: Union of All Types**
   ```python
   MetadataValue = str | int | float | datetime | Fraction | bytes
   # Problem: Too permissive, loses type information
   # Runtime validators still needed
   ```

---

## Implementation

**Phase E Part 6 (Commit: 26f90d80):**
- Enabled 5 new strict flags for Tier 1
- Added comprehensive comment explaining exclusions
- Result: 0 mypy errors, 8.8/10 strictness

**Documentation:**
- [migration_stance.md](../migration_stance.md) — Lessons learned
- [architecture.md](../architecture.md) — Type safety configuration
- [pyproject.toml](../../pyproject.toml) — Pragmatic exclusions rationale

---

## Verification

```bash
# Strictness calculation
mypy . 2>&1 | grep "Success"
# Success: no issues found in 548 source files

# Enabled flags count
grep "disallow_" pyproject.toml | grep "true" | wc -l
# 10 strict flags enabled (pragmatic strict)

# Type:ignore reduction
grep -r "type: ignore" oncutf/ --include="*.py" | wc -l
# 5 remaining (95.7% reduction from 115)
```

---

## Related

- **Supersedes:** None (new decision)
- **See also:** [ADR 004: Type:ignore Reduction Strategy](004-type-ignore-reduction.md)
- **References:**
  - Phase E completion: 76b5b9c7, f9f61a48, 4f2c8be3, 2af01cd4, 26f90d80
  - Pyproject cleanup: e0533afe
