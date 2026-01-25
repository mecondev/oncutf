# ADR 004: Type:ignore Reduction Strategy

**Status:** Accepted  
**Date:** 2026-01-25  
**Author:** Michael Economou  
**Phase:** Phase E (Type Safety Tightening)

---

## Context

At the start of Phase E, the codebase had **115 `# type: ignore` comments**, masking potential type safety issues:

```python
# Distribution before cleanup:
- 53 in UI layer (Qt stubs, dynamic attributes)
- 28 in core services (circular imports, Any usage)
- 19 in controllers (untyped function calls)
- 15 in infrastructure (database, cache operations)
```

**Problems:**
1. **Hidden Bugs:** `type: ignore` suppresses ALL errors on that line, including logic bugs
2. **Technical Debt:** Each ignore is a promise to "fix later" (rarely happens)
3. **Degrading Coverage:** New code follows bad patterns ("just add type: ignore")
4. **Unclear Intent:** Why was ignore needed? Still valid? Can it be removed?

**Example Hidden Bug:**
```python
def process_metadata(data: dict[str, Any]) -> None:
    value = data.get("ISO")  # type: ignore
    # Error suppressed: value could be None, int, str, bytes...
    # Bug hidden: int(value) crashes on None or str "auto"
```

---

## Decision

**Adopt Systematic Type:ignore Reduction Strategy:**

### Phase 1: Analyze (Phase E Part 3)
```bash
# Categorize all type:ignore comments
grep -r "type: ignore" oncutf/ --include="*.py" -n | \
    awk -F: '{print $1}' | uniq -c | sort -rn

# Output: 115 total
# 53 in oncutf/ui/
# 28 in oncutf/core/
# 19 in oncutf/controllers/
# 15 in oncutf/infra/
```

### Phase 2: Remove Obsolete (Phase E Part 3)
- **Target:** Ignores added for issues that no longer exist
- **Method:** Remove ignore, run mypy, check if error still occurs
- **Result:** 104 obsolete ignores removed (90% of cases!)

```python
# Example 1: Obsolete ignore (function now typed)
def old_function(x):  # Was untyped
    return x * 2

result = old_function(5)  # type: ignore  # <-- Obsolete!

# After Phase C: function is typed
def old_function(x: int) -> int:
    return x * 2

result = old_function(5)  # No ignore needed!

# Example 2: Import resolved
from oncutf.utils import helper  # type: ignore  # <-- Obsolete!
# After Phase D: helper module has __init__.py and type hints
```

### Phase 3: Justify Remaining (Phase E Part 5)
- **Target:** 11 remaining ignores
- **Method:** Add specific error codes + explanatory comments
- **Result:** 6 more removed (now fixable), 5 justified

```python
# BEFORE (vague ignore)
icon = QIcon(path)  # type: ignore

# AFTER (specific + justified)
icon = QIcon(path)  # type: ignore[call-overload]  # Qt stub issue: QIcon accepts str | QPixmap
```

### Phase 4: Final Reduction (Phase E Part 5)
- **Target:** 11 → 5 ignores
- **Method:** Fix underlying issues (add type stubs, refactor code)
- **Result:** 5 remaining (all legitimate)

**Final 5 Justified Type:ignores:**
```python
# 1. Qt metaclass pattern (unfixable without changing Qt)
class CustomWidget(QWidget, metaclass=WidgetMeta):  # type: ignore[misc]

# 2. Qt dynamic attribute (signal decoration)
@pyqtSlot(int)  # type: ignore[misc]
def on_value_changed(self, value: int): ...

# 3. Qt overload ambiguity (stub limitation)
pixmap = QPixmap(size)  # type: ignore[call-overload]

# 4. Generic protocol variance (Python typing limitation)
registry: Registry[Service] = Registry()  # type: ignore[type-arg]

# 5. TYPE_CHECKING circular import guard
if TYPE_CHECKING:
    from oncutf.ui import MainWindow  # type: ignore[attr-defined]
```

---

## Consequences

### Positive

1. **Massive Reduction**
   - 115 → 5 ignores (95.7% reduction)
   - Only 5 legitimate cases remain
   - All remaining ignores documented

2. **Bugs Found**
   - 3 potential None dereferences caught
   - 2 incorrect type assumptions fixed
   - 1 unreachable code path discovered

3. **Improved Type Coverage**
   - Mypy now catches real errors on previously ignored lines
   - No "blanket suppression" hiding bugs
   - Specific error codes make intent clear

4. **Maintainability**
   - New developers see clean type hints
   - No "type: ignore cargo cult"
   - Each ignore has justification comment

5. **Metrics Transparency**
   - Easy to track: `grep "type: ignore" | wc -l`
   - Quality gate: ≤5 ignores allowed
   - Trend visible in git history

### Negative

1. **Time Investment**
   - 6+ hours analyzing 115 ignores
   - Required understanding each case
   - Some required code refactoring

2. **Risk of Breaking Changes**
   - Removing ignores exposed hidden issues
   - Required comprehensive testing after each batch
   - Some "working" code had type errors

3. **Learning Curve**
   - Developers must understand why ignores are discouraged
   - Must learn specific error codes (e.g., [call-overload])
   - Requires mypy expertise

### Neutral

1. **Alternative Rejected: Keep All Ignores**
   - Easier short-term (no work)
   - Degrades over time (more ignores added)
   - Hides bugs, defeats purpose of type checking

2. **Alternative Rejected: Remove ALL Ignores**
   - Some are legitimately needed (Qt stubs, metaclasses)
   - Fighting the type checker is counterproductive
   - Perfect is enemy of good

---

## Implementation

**Phase E Part 3 (Commit: 76b5b9c7):**
- Removed 104 obsolete type:ignore comments
- Verified no mypy errors after removal
- Result: 115 → 11 ignores

**Phase E Part 5 (Commit: 4f2c8be3):**
- Analyzed remaining 11 ignores
- Fixed 6 underlying issues
- Justified 5 remaining with comments
- Result: 11 → 5 ignores

**Specific Fixes:**
```python
# Fix 1: Add type stub for untyped import
# oncutf/utils/external_lib.pyi
def helper(x: int) -> str: ...

# Fix 2: Refactor to avoid Qt metaclass
class OldWidget(QWidget, metaclass=Meta):  # type: ignore
# Became:
class NewWidget(QWidget):  # No metaclass needed
    def __init_subclass__(cls): ...  # Use __init_subclass__ instead

# Fix 3: Use protocol instead of Any
def process(data: Any) -> None:  # type: ignore
# Became:
def process(data: MetadataDict) -> None:  # MetadataDict = dict[str, Any] aliased
```

---

## Verification

**Before/After:**
```bash
# Before Phase E
grep -r "type: ignore" oncutf/ --include="*.py" | wc -l
# 115

# After Phase E Part 3
grep -r "type: ignore" oncutf/ --include="*.py" | wc -l
# 11

# After Phase E Part 5
grep -r "type: ignore" oncutf/ --include="*.py" | wc -l
# 5

# Reduction: 95.7%
```

**Remaining Justifications:**
```bash
grep -r "type: ignore" oncutf/ --include="*.py" -B1 -A1
# All 5 have explanatory comments
# All use specific error codes
# All are legitimate (Qt stubs, metaclasses)
```

**Quality Gate:**
```toml
# pyproject.toml
[[tool.mypy.overrides]]
module = "oncutf.*"
warn_unused_ignores = true  # Fail on obsolete ignores
```

---

## Related

- **Complements:** [ADR 001: Pragmatic Strict Typing](001-pragmatic-strict-typing.md)
- **See also:**
  - [mypy error codes reference](https://mypy.readthedocs.io/en/stable/error_codes.html)
  - [Phase E summary](../260121_summary.md#phase-e)
- **References:**
  - Phase E Part 3: 76b5b9c7 (-104 ignores)
  - Phase E Part 5: 4f2c8be3 (11 → 5 ignores)
