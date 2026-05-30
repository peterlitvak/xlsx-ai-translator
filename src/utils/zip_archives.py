"""Safe zip archive extraction, discovery, and creation utilities."""

import zipfile
from pathlib import Path, PurePosixPath

from utils.file_names import is_xlsx_filename


class UnsafeZipError(ValueError):
    """Raised when a zip archive contains an unsafe member path."""


def safe_extract_zip(zip_path: str, extract_dir: str) -> None:
    """Extract a zip archive only if all members stay inside extract_dir."""
    extract_root = Path(extract_dir).resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            _validate_zip_member_path(member.filename, extract_root)
        archive.extractall(extract_root)


def find_xlsx_files(source_path: str) -> list[str]:
    """Find supported workbook files from one workbook or a directory tree."""
    source = Path(source_path)
    if source.is_file():
        return [str(source)] if is_xlsx_filename(source.name) else []

    if not source.is_dir():
        return []

    return sorted(
        str(path)
        for path in source.rglob("*")
        if path.is_file() and is_xlsx_filename(path.name)
    )


def create_zip_from_directory(source_dir: Path, zip_path: Path) -> None:
    """Create a zip archive from all files below source_dir."""
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(source_dir.rglob("*")):
            if file_path.is_file():
                archive.write(
                    file_path,
                    arcname=file_path.relative_to(source_dir).as_posix(),
                )


def _validate_zip_member_path(member_name: str, extract_root: Path) -> None:
    """Validate a zip member path against traversal and absolute-path attacks."""
    normalized_name = member_name.replace("\\", "/")
    member_path = PurePosixPath(normalized_name)
    parts = member_path.parts

    if not parts or member_path.is_absolute():
        raise UnsafeZipError(f"Unsafe zip member path: {member_name}")

    if any(part == ".." for part in parts):
        raise UnsafeZipError(f"Unsafe zip member path: {member_name}")

    if parts[0].endswith(":"):
        raise UnsafeZipError(f"Unsafe zip member path: {member_name}")

    resolved_path = (extract_root / Path(*parts)).resolve()
    if resolved_path != extract_root and extract_root not in resolved_path.parents:
        raise UnsafeZipError(f"Unsafe zip member path: {member_name}")
