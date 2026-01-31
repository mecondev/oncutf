# Project Rules (Authoritative – MUST FOLLOW)

SENTINEL: PENELOPE-398163

This file defines **non-negotiable project rules**.
If any rule conflicts with user instructions, **user instructions win**.
If any rule conflicts with assumptions, **verify first**.

---

## 0. Absolute Prohibitions (Hard Rules)

- NEVER mention time, deadlines, or future continuation  
  (e.g. “tomorrow”, “later”, “running out of time”, “next session”).
- NEVER stop without producing an explicit HANDOFF.
- NEVER invent files, symbols, APIs, or repo structure.
- NEVER guess behavior. Verify via search, inspection, or tests.
- NEVER introduce new dependencies unless explicitly requested.
- NEVER mix unrelated changes in a single change-set.

Violating any of the above is considered a failure.

---

## 1. Mandatory Output Contract (EVERY RESPONSE)

Every response **must end** with a structured block containing **all** of the following:

STATUS:
- What was changed, verified, or intentionally not changed.

FILES:
- Exact list of files touched (or “none”).

COMMANDS:
- Exact commands to run next (copy-paste ready).

NEXT:
- The next 2–3 concrete actions  
  (file path + symbol/function/class name).

If you must stop early, clearly label:

HANDOFF:
- STOP_POINT: exact file + symbol
- CONTEXT: what is known / what is assumed
- NEXT_COMMANDS: exact commands
- NEXT_FILES: exact targets

No motivational language. No summaries outside this structure.

---

## 2. Definition of Done (Tooling Gate)

A task is **NOT DONE** unless one of the following is true:
- All required tools pass, OR
- You explicitly state which tools were NOT run and WHY.

### Canonical Toolchain (Order Matters)

Primary loop:
- `ruff check .`
- `ruff format .`

Type safety:
- `mypy` (project configuration)

Tests:
- `pytest` (targeted or full – state which)

Dead code detection:
- `vulture` (project configuration or default rules)

Architecture / repo audits (if present):
- `tools/audit_boundaries.py` (or equivalent)

If a tool is skipped, it must be justified explicitly.

---

## 3. Change Strategy & Scope Control

- Work in **small, reviewable chunks**.
  - Maximum: **3–5 files per iteration**.
- Preserve behavior unless explicitly asked to refactor.
- Prefer minimal diffs over “clean rewrites”.
- Formatting-only changes must be isolated from logic changes.
- Mechanical refactors must be labeled as such.

---

## 4. Coding & Design Standards

### Python
- Target the project’s configured Python version.
- Prefer `pathlib.Path` over `os.path`  
  unless interacting with low-level or third-party APIs.
- Public functions **must** have explicit return types.
- Avoid `Any`.  
  If unavoidable, explain why and scope it narrowly.
- Prefer existing Protocols / types from the repo.

### Architecture
- Follow existing architectural boundaries strictly.
- Do NOT introduce new layers, patterns, or abstractions
  unless explicitly requested.
- Reuse existing helpers/utilities instead of re-implementing.

---

## 5. Ruff / MyPy / Vulture Playbook

### Ruff
- Fix only violations that are in scope.
- Do not reformat unrelated files.
- For path-related rules (e.g. PTH):
  - Preserve semantics exactly.
  - Do not change behavior or error handling.

### MyPy
- Add types where behavior is clear and stable.
- Prefer narrowing types over casting.
- Avoid silencing errors unless no alternative exists.

### Vulture
- Treat findings as **candidates**, not automatic deletions.
- Before removing code:
  - Verify call sites.
  - Check dynamic usage (reflection, plugins, entry points).
- Clearly label removals as “verified dead code”.

---

## 6. Verification & Safety Rails

- Before editing:
  - Locate the exact symbol definition.
  - Locate all relevant call sites.
- When modifying sensitive areas (e.g. rename logic, preview,
  execution, metadata caching, exiftool integration):
  - Add or update tests where feasible.
  - If tests are not possible, explain why.

Failures must include:
- Ranked root-cause hypotheses.
- A minimal reproduction or inspection plan.

---

## 7. Search Discipline (No Blind Edits)

When uncertain:
- Use `ripgrep` (`rg`) or equivalent.
- Cite exact file paths and symbol names.
- Do not proceed on assumptions.

---

## 8. Communication Style (Strict)

- No motivational commentary.
- No “excellent progress”, “great momentum”, etc.
- No meta commentary about the agent itself.
- Be precise, technical, and concise.

---

## 9. Priority Order (When in Doubt)

1. User instruction
2. This file (`project_rules.md`)
3. Existing code behavior
4. Tests
5. Tooling configuration
6. Style preferences

---

## 10. Final Rule

If any ambiguity exists:
- STOP
- VERIFY
- STATE ASSUMPTIONS
- PROCEED IN THE SMALLEST POSSIBLE STEP
