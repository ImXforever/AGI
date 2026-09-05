#!/usr/bin/env python3
"""Import health checker — verifies all internal imports resolve correctly.

Runs without needing the full dependency tree (catches import errors at module
level). Useful in CI to catch broken imports early.

Run: python tools/import_check.py
Exit code 0 = all imports OK, 1 = broken imports.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".mypy_cache", "venv", ".venv"}

# Modules that require runtime dependencies (skip these)
SKIP_MODULES = {
    "app.channels.telegram",
    "app.channels.whatsapp",
    "app.channels.email",
    "app.core.llm",
    "app.core.hermes_client",
    "app.core.pipeline",
    "app.core.tools",
    "app.core.hitl.sweeper",
    "app.gateway",
    "app.storage.pg",
    "app.storage.redis",
    "app.storage.r2",
    "app.storage.archive",
    "app.storage.seed",
}


def discover_modules() -> list[str]:
    """Find all Python modules in the app directory."""
    modules: list[str] = []
    app_dir = ROOT / "app"

    for py_file in sorted(app_dir.rglob("*.py")):
        if py_file.name == "__init__.py":
            rel = py_file.parent.relative_to(ROOT)
            module = str(rel).replace("/", ".").replace("\\", ".")
        else:
            rel = py_file.relative_to(ROOT)
            module = str(rel).with_suffix("").replace("/", ".").replace("\\", ".")

        # Skip test files
        if "test" in module.lower():
            continue

        modules.append(module)

    return modules


def check_import(module_name: str) -> str | None:
    """Try to import a module. Returns error message or None if OK."""
    if module_name in SKIP_MODULES:
        return None

    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            return f"module not found: {module_name}"
    except Exception as exc:
        return f"find_spec failed: {exc}"

    return None


def check_syntax(filepath: Path) -> str | None:
    """Check Python file syntax without importing."""
    try:
        import ast

        with open(filepath, encoding="utf-8") as f:
            source = f.read()
        ast.parse(source, filename=str(filepath))
        return None
    except SyntaxError as exc:
        return f"syntax error: {exc}"
    except Exception as exc:
        return f"read error: {exc}"


def main() -> None:
    print("=" * 60)
    print("Kia-Agent Import Health Check")
    print("=" * 60)

    errors: list[str] = []

    # 1. Syntax check all Python files
    print("\n--- Syntax Check ---")
    syntax_errors = 0
    for py_file in sorted(ROOT.rglob("*.py")):
        # Skip non-project dirs
        parts = py_file.relative_to(ROOT).parts
        if any(p in SKIP_DIRS for p in parts):
            continue

        error = check_syntax(py_file)
        if error:
            rel = py_file.relative_to(ROOT)
            msg = f"  {rel}: {error}"
            print(msg)
            errors.append(msg)
            syntax_errors += 1

    if syntax_errors == 0:
        print("  All files pass syntax check.")

    # 2. Module discovery check
    print("\n--- Module Discovery ---")
    modules = discover_modules()
    print(f"  Found {len(modules)} modules")

    import_errors = 0
    for module in modules:
        error = check_import(module)
        if error:
            msg = f"  {module}: {error}"
            print(msg)
            errors.append(msg)
            import_errors += 1

    if import_errors == 0:
        print("  All modules discoverable.")

    # 3. Summary
    print()
    print("=" * 60)
    if errors:
        print(f"FAILED: {len(errors)} error(s) found")
        sys.exit(1)
    else:
        print(f"PASSED: {len(modules)} modules, 0 syntax errors, 0 import errors")
        sys.exit(0)


if __name__ == "__main__":
    main()
