#!/usr/bin/env python3
"""Deployment packager — creates a distributable archive.

Creates a tarball containing:
- All source code
- Dockerfiles
- docker-compose.yml
- Configuration templates
- Database migrations and seeds
- Documentation

Run: python tools/package.py
Output: dist/Kia-Agent-{version}.tar.gz
"""

from __future__ import annotations

import json
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

# Files/patterns to include
INCLUDE_PATTERNS = [
    "app/",
    "admin/",
    "db/",
    "deploy/",
    "docs/",
    "provision/",
    "tools/",
    "tests/",
    ".github/",
    "Dockerfile",
    "Dockerfile.hermes",
    "Makefile",
    "pyproject.toml",
    "README.md",
    ".env.example",
    ".gitignore",
    "railway.json",
]

# Files/patterns to exclude from the archive
EXCLUDE_PATTERNS = {
    "__pycache__",
    "*.pyc",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "htmlcov",
    ".coverage",
    "dist",
    "build",
    "*.egg-info",
    "node_modules",
    ".git",
    ".venv",
    "venv",
    ".env",
    ".env.local",
}


def _should_include(path: Path) -> bool:
    parts = path.parts
    for part in parts:
        for pattern in EXCLUDE_PATTERNS:
            if pattern.startswith("*."):
                if path.suffix == pattern[1:]:
                    return False
            elif part == pattern:
                return False
    return True


def _get_version() -> str:
    pyproject = ROOT / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.strip().startswith("version"):
                _, _, val = line.partition("=")
                return val.strip().strip('"').strip("'")
    return "10.0.0"


def package() -> Path:
    DIST.mkdir(parents=True, exist_ok=True)
    version = _get_version()
    filename = f"Kia-Agent-{version}.tar.gz"
    output = DIST / filename

    print(f"Kia-Agent Packager v{version}")
    print(f"Output: {output}")
    print()

    file_count = 0

    with tarfile.open(output, "w:gz") as tar:
        for pattern in INCLUDE_PATTERNS:
            source = ROOT / pattern
            if source.is_dir():
                for path in sorted(source.rglob("*")):
                    if not _should_include(path.relative_to(ROOT)):
                        continue
                    if path.is_file():
                        arcname = str(path.relative_to(ROOT))
                        tar.add(path, arcname=arcname)
                        file_count += 1
            elif source.is_file():
                arcname = str(source.relative_to(ROOT))
                tar.add(source, arcname=arcname)
                file_count += 1

        # Add metadata
        meta = {
            "version": version,
            "packaged_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "file_count": file_count,
        }
        meta_bytes = json.dumps(meta, indent=2).encode("utf-8")
        import io

        info = tarfile.TarInfo(name=".package-meta.json")
        info.size = len(meta_bytes)
        tar.addfile(info, io.BytesIO(meta_bytes))

    size_kb = output.stat().st_size / 1024
    print(f"Package created: {output}")
    print(f"  Files: {file_count}")
    print(f"  Size:  {size_kb:.1f} KB")

    return output


if __name__ == "__main__":
    package()
