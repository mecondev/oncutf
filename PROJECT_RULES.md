SENTINEL: PINEAPPLE-7391
# Project Rules (Authoritative)

SENTINEL: PINEAPPLE-7391

## 0. Non-negotiables
- Never mention time constraints (“tomorrow”, “later”, “running out of time”).
- If you must stop, output a HANDOFF block with exact next commands and next files.
- Do not invent files, symbols, APIs, or repo structure. Verify via search first.

## 1. Output Contract (every response)
End every response with:
- STATUS: what changed / what was verified
- FILES: list of touched files
- COMMANDS: exact commands to run next
- NEXT: the next 2–3 concrete steps (file + symbol)

## 2. Tooling Gate (definition of done)
A change is not “done” unless these pass (or you explicitly say what was not run and why):
- ruff check .
- ruff format .
- mypy (project config)
- pytest (targeted or full; state which)
- vulture

## 3. Change strategy
- Work in small chunks: max 3–5 files per iteration.
- Keep diffs minimal; preserve behavior unless explicitly asked to refactor.
- Do not mix formatting-only changes with behavior changes.

## 4. Coding standards
- Prefer pathlib.Path over os.path unless interacting with low-level APIs.
- Add type hints safely; avoid Any unless unavoidable (explain when used).
- Follow existing patterns in the repo (imports, logging, error handling).

## 5. Verification rules
- Before proposing edits, locate the exact symbol and call sites.
- When modifying rename/preview/execution/metadata caching, add or update tests where feasible.
- If a failure occurs, provide ranked root-cause hypotheses + a minimal repro plan.

## 6. Search discipline
When unsure, use ripgrep searches and cite exact file+symbol locations before changing code.
