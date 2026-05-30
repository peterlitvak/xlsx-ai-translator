#!/usr/bin/env python3
import argparse
import shutil
from pathlib import Path


def copy_matching(source_dir, target_dir, pattern):
    source_dir = Path(source_dir).resolve()
    target_dir = Path(target_dir).resolve()
    # Use rglob with the pattern for standard glob matching
    for path in source_dir.rglob(pattern):
        rel_path = path.relative_to(source_dir)
        dest_path = target_dir / rel_path
        if path.is_dir():
            dest_path.mkdir(parents=True, exist_ok=True)
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest_path)


def main():
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
