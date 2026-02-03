#!/usr/bin/env python3
"""Boundary audit for the OnCutF repo (path-based layers).

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
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

TYPE_IGNORE_RE = re.compile(r"#\s*type:\s*ignore(\[[^\]]+\])?")

# External libraries that should NOT be imported in certain layers.
# Keys are layer names, values are sets of forbidden module prefixes.
FORBIDDEN_EXTERNAL_IMPORTS: dict[str, set[str]] = {
    # Pure business logic layers - no Qt/GUI dependencies
    "domain": {"PyQt5", "PyQt6", "PySide2", "PySide6", "sip"},
    "app": {"PyQt5", "PyQt6", "PySide2", "PySide6", "sip"},
    # Core should be Qt-free for testability (but currently has violations)
    "core": {"PyQt5", "PyQt6", "PySide2", "PySide6", "sip"},
}

# Allowed Qt imports in core (temporary whitelist during migration).
# Add relative paths here to suppress violations during incremental migration.
CORE_QT_WHITELIST: set[str] = set()


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
    """Classify a Python file into a layer based on its path relative to package_dir.

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


class ImportVisitor(ast.NodeVisitor):
    """AST visitor that collects runtime imports (excluding TYPE_CHECKING blocks)."""

    def __init__(self):
        self.imports: list[ImportRef] = []
        self._in_type_checking = False
        self._type_checking_depth = 0

    def visit_If(self, node: ast.If) -> None:
        """Track if we're inside a TYPE_CHECKING block."""
        # Check if this is `if TYPE_CHECKING:`
        is_type_checking = self._is_type_checking_condition(node.test)

        if is_type_checking:
            # Enter TYPE_CHECKING block
            old_state = self._in_type_checking
            old_depth = self._type_checking_depth
            self._in_type_checking = True
            self._type_checking_depth += 1

            # Visit the body (but don't collect imports)
            for stmt in node.body:
                self.visit(stmt)

            # Restore state after leaving block
            self._in_type_checking = old_state
            self._type_checking_depth = old_depth

            # Visit orelse (elif/else) normally
            for stmt in node.orelse:
                self.visit(stmt)
        else:
            # Normal if block - visit all
            self.generic_visit(node)

    def _is_type_checking_condition(self, test_node: ast.expr) -> bool:
        """Check if condition is TYPE_CHECKING (or typing.TYPE_CHECKING)."""
        # Handle: if TYPE_CHECKING:
        if isinstance(test_node, ast.Name) and test_node.id == "TYPE_CHECKING":
            return True
        # Handle: if typing.TYPE_CHECKING:
        if isinstance(test_node, ast.Attribute):
            if test_node.attr == "TYPE_CHECKING":
                if isinstance(test_node.value, ast.Name) and test_node.value.id == "typing":
                    return True
        return False

    def visit_Import(self, node: ast.Import) -> None:
        """Collect import statements (only if not in TYPE_CHECKING block)."""
        if not self._in_type_checking:
            for alias in node.names:
                if alias.name:
                    self.imports.append(
                        ImportRef(module=alias.name, lineno=node.lineno, kind="import")
                    )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Collect from-import statements (only if not in TYPE_CHECKING block)."""
        if not self._in_type_checking and node.module:
            self.imports.append(
                ImportRef(module=node.module, lineno=node.lineno, kind="from")
            )
        self.generic_visit(node)


def iter_imports(py_file: Path) -> Iterator[ImportRef]:
    """Yield runtime import references in a Python file (excluding TYPE_CHECKING).

    Notes:
    - Captures `import X` and `from X import Y`.
    - Excludes imports inside `if TYPE_CHECKING:` blocks.
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

    visitor = ImportVisitor()
    visitor.visit(tree)
    yield from visitor.imports


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
    """Infer the layer of an imported module within our package namespace.

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

    # Check for special sub-packages first (utils/ui, controllers/ui)
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
    severity: str = "error"  # error, warning
    chain: list[str] = field(default_factory=list)  # Dependency chain for transitive violations


def check_forbidden_external(
    file_path: str,
    file_layer: str,
    module: str,
    lineno: int,
) -> RuleViolation | None:
    """Check if an external import is forbidden for this layer.

    Returns a RuleViolation if the import violates layer purity rules.
    """
    forbidden = FORBIDDEN_EXTERNAL_IMPORTS.get(file_layer)
    if not forbidden:
        return None

    # Check if module starts with any forbidden prefix
    for prefix in forbidden:
        if module == prefix or module.startswith(prefix + "."):
            # Check whitelist for core layer (temporary migration aid)
            if file_layer == "core":
                # Normalize path for comparison
                rel_path = file_path.replace("\\", "/")
                if any(wl in rel_path for wl in CORE_QT_WHITELIST):
                    return None

            return RuleViolation(
                file=file_path,
                file_layer=file_layer,
                imported=module,
                imported_layer="external_qt",
                lineno=lineno,
                rule=f"{file_layer}_must_not_import_qt",
                severity="error",
            )

    return None


def is_forbidden(file_layer: str, imported_layer: str, strict_ui_core: bool) -> str | None:
    """Return a rule name if the import is forbidden; otherwise None.

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
    if file_layer == "domain" and imported_layer in ui_side | {
        "app", "infra", "core", "controllers", "utils", "boot"
    }:
        return "domain_must_be_pure"

    # app must not depend on UI or concrete infra/core/boot
    # (app should be testable without knowing boot exists)
    if file_layer == "app" and imported_layer in ui_side | {"infra", "core", "boot"}:
        return "app_must_not_depend_on_ui_infra_core"

    # infra must not depend on UI or app/controllers/boot (keep infra concrete + isolated)
    if file_layer == "infra" and imported_layer in ui_side | {"app", "controllers", "boot"}:
        return "infra_must_not_depend_on_ui_app_controllers"

    # core must not import ui
    if file_layer == "core" and imported_layer in ui_side:
        return "core_must_not_import_ui"

    # ui must not import infra directly (should go through boot)
    if file_layer in ui_side:
        if imported_layer == "infra":
            return "ui_must_not_import_infra"
        if strict_ui_core and imported_layer == "core":
            return "ui_must_not_import_core"

    # controllers (non-ui) ideally should not import ui
    if file_layer == "controllers" and imported_layer in ui_side:
        return "controllers_must_not_import_ui"

    return None


# -----------------------------
# Report generation
# -----------------------------


@dataclass
class FileReport:
    """Analysis report for a single Python file."""

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


def find_transitive_qt_dependencies(
    reports: list[FileReport],
    package: str,
) -> dict[str, list[str]]:
    """Find all files that transitively depend on Qt.

    Returns: dict mapping file_path -> dependency_chain showing how Qt is reached.
    """
    # Build module -> file mapping
    module_to_file: dict[str, str] = {}
    for rep in reports:
        # Convert file path to module name
        try:
            rel_path = Path(rep.path).relative_to(Path.cwd() / package)
            module_parts = list(rel_path.parts)
            if module_parts[-1] == "__init__.py":
                module_parts = module_parts[:-1]
            elif module_parts[-1].endswith(".py"):
                module_parts[-1] = module_parts[-1][:-3]
            module_name = package + "." + ".".join(module_parts) if module_parts else package
            module_to_file[module_name] = rep.path
        except ValueError:
            pass

    # Find files with direct Qt imports
    qt_prefixes = {"PyQt5", "PyQt6", "PySide2", "PySide6", "sip"}
    direct_qt_files: set[str] = set()
    for rep in reports:
        for imp in rep.imports:
            if any(imp.module == qt or imp.module.startswith(qt + ".") for qt in qt_prefixes):
                direct_qt_files.add(rep.path)
                break

    # Build reverse graph: module -> files that import it
    importers: dict[str, set[str]] = defaultdict(set)
    for rep in reports:
        for imp in rep.imports:
            importers[imp.module].add(rep.path)

    # BFS to find transitive dependencies
    transitive_qt: dict[str, list[str]] = {}

    # Start with direct Qt importers
    for qt_file in direct_qt_files:
        transitive_qt[qt_file] = [qt_file, "Qt"]

    # Propagate Qt taint backwards through the dependency graph
    queue: deque[tuple[str, list[str]]] = deque()
    for qt_file in direct_qt_files:
        queue.append((qt_file, [qt_file, "Qt"]))

    visited: set[str] = set(direct_qt_files)

    while queue:
        current_file, chain = queue.popleft()

        # Find module name for current file
        current_module = None
        for mod, fpath in module_to_file.items():
            if fpath == current_file:
                current_module = mod
                break

        if not current_module:
            continue

        # Find all files that import this module
        for importer_file in importers.get(current_module, []):
            if importer_file not in visited:
                visited.add(importer_file)
                new_chain = [importer_file, *chain]
                transitive_qt[importer_file] = new_chain
                queue.append((importer_file, new_chain))

    return transitive_qt


def find_violations(
    reports: Iterable[FileReport],
    package: str,
    strict_ui_core: bool,
    check_external: bool = True,
    check_transitive: bool = True,
) -> list[RuleViolation]:
    """Find boundary violations based on the rule matrix."""
    violations: list[RuleViolation] = []
    reports_list = list(reports)

    for rep in reports_list:
        for imp in rep.imports:
            imp_layer = infer_imported_layer(imp.module, package)

            # Check internal layer violations
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
                continue

            # Check forbidden external imports (Qt in pure layers)
            if check_external and imp_layer == EXTERNAL:
                ext_violation = check_forbidden_external(
                    rep.path, rep.layer, imp.module, imp.lineno
                )
                if ext_violation:
                    violations.append(ext_violation)

    # Check transitive Qt dependencies
    if check_transitive and check_external:
        transitive_qt = find_transitive_qt_dependencies(reports_list, package)

        for rep in reports_list:
            # Check if this layer should be Qt-free
            if rep.layer not in FORBIDDEN_EXTERNAL_IMPORTS:
                continue

            # Check if this file transitively depends on Qt
            if rep.path in transitive_qt:
                chain = transitive_qt[rep.path]
                # Only report if this is NOT a direct import (those are already reported)
                if len(chain) > 2:  # file -> intermediate -> Qt
                    violations.append(
                        RuleViolation(
                            file=rep.path,
                            file_layer=rep.layer,
                            imported="Qt (transitive)",
                            imported_layer="external_qt",
                            lineno=0,
                            rule=f"{rep.layer}_must_not_import_qt_transitive",
                            severity="warning",
                            chain=chain,
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
            chain_info = ""
            if v.chain:
                # Show shortened chain
                chain_display = " -> ".join(
                    [Path(p).name if not p.startswith("Qt") else p for p in v.chain[:4]]
                )
                if len(v.chain) > 4:
                    chain_display += " -> ..."
                chain_info = f" [chain: {chain_display}]"
            print(
                f"  - {v.file}:{v.lineno} [{v.file_layer} -> {v.imported_layer}] {v.imported} ({v.rule}){chain_info}"
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
    parser.add_argument(
        "--no-external-check",
        action="store_true",
        help="Disable checking for forbidden external imports (Qt in pure layers).",
    )
    parser.add_argument(
        "--no-transitive",
        action="store_true",
        help="Disable checking for transitive Qt dependencies.",
    )

    args = parser.parse_args(argv)

    repo_root = Path(args.root).resolve()
    package_dir = repo_root / args.package
    if not package_dir.exists() or not package_dir.is_dir():
        print(f"ERROR: package directory not found: {package_dir}", file=sys.stderr)
        return 2

    reports = build_reports(repo_root, args.package)
    violations = find_violations(
        reports,
        args.package,
        strict_ui_core=args.strict_ui_core,
        check_external=not args.no_external_check,
        check_transitive=not args.no_transitive,
    )

    violations.sort(key=lambda v: (v.rule, v.file, v.lineno))

    print_human_report(
        reports, violations, only_violations=args.only_violations, max_items=args.max_items
    )

    if args.json_path:
        payload = {
            "summary": summarize(reports, violations),
            "violations": [v.__dict__ for v in violations],
            "type_ignores": [
                {"draft": r.path, "layer": r.layer, "count": r.type_ignores}
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
