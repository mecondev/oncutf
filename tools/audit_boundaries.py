#!/usr/bin/env python3
"""
Boundary audit for the OnCutF repo (path-based layers).

Repo-specific notes
-------------------
Your repo has top-level packages like:
- oncutf/ui, oncutf/app, oncutf/domain, oncutf/infra, oncutf/core
and also mixed areas:
- oncutf/utils/ui (Qt/UI helpers)
- oncutf/controllers/ui (UI-facing controllers)

This script classifies layers primarily by filesystem path (relative to the
package directory) and enforces a repo-tailored rule matrix.

Tested with
-----------
- Python 3.10+ (stdlib only)

Typical usage
-------------
python tools/audit_boundaries.py --package oncutf
python tools/audit_boundaries.py --only-violations
python tools/audit_boundaries.py --json boundary_report.json
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

TYPE_IGNORE_RE = re.compile(r"#\s*type:\s*ignore(\[[^\]]+\])?")


# -----------------------------
# Layer classification (repo-specific)
# -----------------------------

# These are the *internal* layer labels we will report/enforce on.
LAYER_INTERNAL = {
    "ui",
    "app",
    "domain",
    "infra",
    "core",
    "boot",  # Composition root - can import everything
    "controllers",
    "controllers_ui",
    "utils",
    "utils_ui",
    "models",
    "modules",
    "config",
    "unknown",
}

# Imports that do not start with our package name are treated as "external".
EXTERNAL = "external"


def classify_layer(py_file: Path, package_dir: Path) -> str:
    """
    Classify a Python file into a layer based on its path relative to package_dir.

    This is intentionally simple and transparent. The special handling below matches
    your repo layout:
    - oncutf/boot/*             -> boot (composition root)
    - oncutf/utils/ui/*         -> utils_ui
    - oncutf/controllers/ui/*   -> controllers_ui
    - oncutf/ui/*               -> ui
    - oncutf/app/*              -> app
    - oncutf/domain/*           -> domain
    - oncutf/infra/*            -> infra
    - oncutf/core/*             -> core
    - oncutf/config/*           -> config
    - oncutf/models/*           -> models
    - oncutf/modules/*          -> modules
    - oncutf/controllers/*      -> controllers
    - oncutf/utils/*            -> utils
    """
    try:
        rel = py_file.resolve().relative_to(package_dir.resolve())
    except Exception:
        return "unknown"

    parts = rel.parts
    if not parts:
        return "unknown"

    top = parts[0]

    # Special mixed subtrees
    if top == "utils" and len(parts) >= 2 and parts[1] == "ui":
        return "utils_ui"
    if top == "controllers" and len(parts) >= 2 and parts[1] == "ui":
        return "controllers_ui"

    # Direct top-level layers/packages
    if top in {
        "ui",
        "app",
        "domain",
        "infra",
        "core",
        "boot",  # Composition root
        "controllers",
        "utils",
        "models",
        "modules",
        "config",
    }:
        return top

    return "unknown"


# -----------------------------
# Import extraction
# -----------------------------


@dataclass(frozen=True)
class ImportRef:
    """A single import reference found in a file."""

    module: str
    lineno: int
    kind: str  # "import" or "from"


def iter_imports(py_file: Path) -> Iterator[ImportRef]:
    """
    Yield all syntactic import references in a Python file.

    Notes:
    - Captures `import X` and `from X import Y`.
    - Does not capture dynamic imports (importlib, __import__).
    """
    try:
        source = py_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return

    try:
        tree = ast.parse(source, filename=str(py_file))
    except SyntaxError:
        # Don't crash audits on a single bad file; treat as "no imports".
        return

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    yield ImportRef(module=alias.name, lineno=node.lineno, kind="import")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                yield ImportRef(module=node.module, lineno=node.lineno, kind="from")


def count_type_ignores(py_file: Path) -> int:
    """Count '# type: ignore' occurrences in a Python file."""
    try:
        text = py_file.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return 0
    return sum(1 for _ in TYPE_IGNORE_RE.finditer(text))


# -----------------------------
# Layer inference for imported modules
# -----------------------------


def infer_imported_layer(module: str, package: str) -> str:
    """
    Infer the layer of an imported module within our package namespace.

    Because your repo has mixed trees (utils/ui and controllers/ui), we infer:
    - oncutf.utils.ui.*         -> utils_ui
    - oncutf.controllers.ui.*   -> controllers_ui
    - oncutf.<top>.*            -> <top>  (if recognized: ui, app, domain,
                                           infra, core, boot, controllers,
                                           utils, models, modules, config)
    - otherwise                 -> unknown
    """
    if not (module == package or module.startswith(package + ".")):
        return EXTERNAL

    parts = module.split(".")
    if len(parts) == 1:
        return "unknown"

    # parts[0] == package
    if len(parts) >= 3 and parts[1] == "utils" and parts[2] == "ui":
        return "utils_ui"
    if len(parts) >= 3 and parts[1] == "controllers" and parts[2] == "ui":
        return "controllers_ui"

    top = parts[1]
    if top in {
        "ui",
        "app",
        "domain",
        "infra",
        "core",
        "boot",  # Composition root
        "controllers",
        "utils",
        "models",
        "modules",
        "config",
    }:
        return top

    return "unknown"


# -----------------------------
# Boundary rules (repo-tailored)
# -----------------------------


@dataclass(frozen=True)
class RuleViolation:
    """A detected boundary violation."""

    file: str
    file_layer: str
    imported: str
    imported_layer: str
    lineno: int
    rule: str


def is_forbidden(file_layer: str, imported_layer: str, strict_ui_core: bool) -> str | None:
    """
    Return a rule name if the import is forbidden; otherwise None.

    Philosophy (matching your goals):
    - boot is composition root: can import EVERYTHING (no violations)
    - domain must be pure: no ui/app/infra/core/controllers/utils_ui/boot
    - app should orchestrate use-cases without Qt and without concrete infra/core:
      no ui/infra/core/utils_ui/boot (app must be testable without boot)
    - infra should not depend on ui/app/controllers/utils_ui/boot
    - ui must not import infra directly (should go through boot or app services)
    - core must never import ui
    - controllers_ui is considered UI-facing; treat it like "ui".
    - utils_ui is UI-only helper; treat it like "ui".
    """
    if file_layer not in LAYER_INTERNAL or imported_layer not in (LAYER_INTERNAL | {EXTERNAL}):
        return None

    if imported_layer == EXTERNAL:
        return None

    # boot is composition root - can import anything
    if file_layer == "boot":
        return None

    # Helper sets
    ui_side = {"ui", "controllers_ui", "utils_ui"}

    # domain purity (boot is also forbidden for domain)
    if file_layer == "domain":
        if imported_layer in ui_side | {"app", "infra", "core", "controllers", "utils", "boot"}:
            return "domain_must_be_pure"

    # app must not depend on UI or concrete infra/core/boot
    # (app should be testable without knowing boot exists)
    if file_layer == "app":
        if imported_layer in ui_side | {"infra", "core", "boot"}:
            return "app_must_not_depend_on_ui_infra_core"

    # infra must not depend on UI or app/controllers/boot (keep infra concrete + isolated)
    if file_layer == "infra":
        if imported_layer in ui_side | {"app", "controllers", "boot"}:
            return "infra_must_not_depend_on_ui_app_controllers"

    # core must not import ui
    if file_layer == "core":
        if imported_layer in ui_side:
            return "core_must_not_import_ui"

    # ui must not import infra directly (should go through boot)
    if file_layer in ui_side:
        if imported_layer == "infra":
            return "ui_must_not_import_infra"
        if strict_ui_core and imported_layer == "core":
            return "ui_must_not_import_core"

    # controllers (non-ui) ideally should not import ui
    if file_layer == "controllers":
        if imported_layer in ui_side:
            return "controllers_must_not_import_ui"

    return None


# -----------------------------
# Report generation
# -----------------------------


@dataclass
class FileReport:
    path: str
    layer: str
    imports: list[ImportRef]
    type_ignores: int


def walk_python_files(package_dir: Path) -> Iterator[Path]:
    """Yield Python files under package_dir, skipping common junk directories."""
    skip_dirs = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "build",
        "dist",
    }
    for root, dirs, files in os.walk(package_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for name in files:
            if name.endswith(".py"):
                yield Path(root) / name


def build_reports(repo_root: Path, package: str) -> list[FileReport]:
    """Build per-file reports for a given package directory."""
    package_dir = repo_root / package
    reports: list[FileReport] = []
    for py_file in walk_python_files(package_dir):
        layer = classify_layer(py_file, package_dir)
        imports = list(iter_imports(py_file))
        ti = count_type_ignores(py_file)
        reports.append(FileReport(path=str(py_file), layer=layer, imports=imports, type_ignores=ti))
    return reports


def find_violations(
    reports: Iterable[FileReport],
    package: str,
    strict_ui_core: bool,
) -> list[RuleViolation]:
    """Find boundary violations based on the rule matrix."""
    violations: list[RuleViolation] = []
    for rep in reports:
        for imp in rep.imports:
            imp_layer = infer_imported_layer(imp.module, package)
            rule = is_forbidden(rep.layer, imp_layer, strict_ui_core=strict_ui_core)
            if rule:
                violations.append(
                    RuleViolation(
                        file=rep.path,
                        file_layer=rep.layer,
                        imported=imp.module,
                        imported_layer=imp_layer,
                        lineno=imp.lineno,
                        rule=rule,
                    )
                )
    return violations


def summarize(reports: list[FileReport], violations: list[RuleViolation]) -> dict:
    """Create a compact summary dict for printing or JSON output."""
    files_by_layer: dict[str, int] = {}
    for rep in reports:
        files_by_layer[rep.layer] = files_by_layer.get(rep.layer, 0) + 1

    type_ignores_total = sum(r.type_ignores for r in reports)

    by_rule: dict[str, int] = {}
    by_direction: dict[str, int] = {}
    for v in violations:
        by_rule[v.rule] = by_rule.get(v.rule, 0) + 1
        direction = f"{v.file_layer}->{v.imported_layer}"
        by_direction[direction] = by_direction.get(direction, 0) + 1

    return {
        "files_scanned": len(reports),
        "files_by_layer": dict(sorted(files_by_layer.items())),
        "type_ignores_total": type_ignores_total,
        "violations_total": len(violations),
        "violations_by_rule": dict(sorted(by_rule.items(), key=lambda kv: (-kv[1], kv[0]))),
        "violations_by_direction": dict(
            sorted(by_direction.items(), key=lambda kv: (-kv[1], kv[0]))
        ),
    }


def print_human_report(
    reports: list[FileReport],
    violations: list[RuleViolation],
    only_violations: bool,
    max_items: int,
) -> None:
    """Print a readable report to stdout."""
    summary = summarize(reports, violations)

    print("=== Boundary Audit Summary ===")
    print(f"Files scanned:        {summary['files_scanned']}")
    print(f"Type ignores total:   {summary['type_ignores_total']}")
    print(f"Violations total:     {summary['violations_total']}")
    print()

    print("Files by layer:")
    for layer, cnt in summary["files_by_layer"].items():
        print(f"  - {layer:<14} {cnt}")
    print()

    if summary["violations_total"]:
        print("Violations by rule:")
        for rule, cnt in summary["violations_by_rule"].items():
            print(f"  - {rule:<45} {cnt}")
        print()

        print("Violations by direction:")
        for direction, cnt in summary["violations_by_direction"].items():
            print(f"  - {direction:<22} {cnt}")
        print()

        print("Top violations (file:line -> import):")
        for v in violations[:max_items]:
            print(
                f"  - {v.file}:{v.lineno} [{v.file_layer} -> {v.imported_layer}] {v.imported} ({v.rule})"
            )
        if len(violations) > max_items:
            print(f"  ... ({len(violations) - max_items} more)")
        print()

    if only_violations:
        return

    ignores = [(r.type_ignores, r.path) for r in reports if r.type_ignores]
    ignores.sort(reverse=True)
    if ignores:
        print("Top '# type: ignore' hotspots:")
        for n, path in ignores[:max_items]:
            print(f"  - {path}: {n}")
        if len(ignores) > max_items:
            print(f"  ... ({len(ignores) - max_items} more)")
        print()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Audit internal import boundaries and '# type: ignore' usage."
    )
    parser.add_argument("--root", default=".", help="Repository root directory (default: .)")
    parser.add_argument(
        "--package", default="oncutf", help="Top-level package directory to scan (default: oncutf)"
    )
    parser.add_argument(
        "--only-violations", action="store_true", help="Print only boundary violations."
    )
    parser.add_argument(
        "--max-items", type=int, default=60, help="Max items to print for lists (default: 60)"
    )
    parser.add_argument(
        "--json", dest="json_path", default="", help="Write JSON report to this path (optional)."
    )
    parser.add_argument(
        "--strict-ui-core",
        action="store_true",
        help="If enabled, flags ui -> core imports as violations (stricter mode).",
    )

    args = parser.parse_args(argv)

    repo_root = Path(args.root).resolve()
    package_dir = repo_root / args.package
    if not package_dir.exists() or not package_dir.is_dir():
        print(f"ERROR: package directory not found: {package_dir}", file=sys.stderr)
        return 2

    reports = build_reports(repo_root, args.package)
    violations = find_violations(reports, args.package, strict_ui_core=args.strict_ui_core)

    violations.sort(key=lambda v: (v.rule, v.file, v.lineno))

    print_human_report(
        reports, violations, only_violations=args.only_violations, max_items=args.max_items
    )

    if args.json_path:
        payload = {
            "summary": summarize(reports, violations),
            "violations": [v.__dict__ for v in violations],
            "type_ignores": [
                {"file": r.path, "layer": r.layer, "count": r.type_ignores}
                for r in reports
                if r.type_ignores
            ],
        }
        out = Path(args.json_path).resolve()
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote JSON report: {out}")

    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
