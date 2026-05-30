#!/usr/bin/env python3
"""Copy files matching a glob pattern while preserving relative paths."""

import argparse
import shutil
from pathlib import Path


def copy_matching(source_dir: str, target_dir: str, pattern: str) -> None:
    """Copy matching files or directories from source_dir to target_dir."""
    source_path = Path(source_dir).resolve()
    target_path = Path(target_dir).resolve()
    for path in source_path.rglob(pattern):
        rel_path = path.relative_to(source_path)
        dest_path = target_path / rel_path
        if path.is_dir():
            dest_path.mkdir(parents=True, exist_ok=True)
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest_path)


def main() -> None:
    """Run the copy-pattern command-line interface."""
    parser = argparse.ArgumentParser(
        description="Copy files and directories matching a pattern, preserving structure."
    )
    parser.add_argument("source", help="Source directory to scan")
    parser.add_argument("target", help="Target directory to copy to")
    parser.add_argument(
        "pattern",
        help='Glob pattern to match relative paths (e.g. "en/*.xlsx", "*.txt", "foo/bar/*", "en/**/*.xlsx")',
    )
    args = parser.parse_args()
    copy_matching(args.source, args.target, args.pattern)


if __name__ == "__main__":
    main()
