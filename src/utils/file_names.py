"""Filename utilities for uploaded and translated workbook artifacts."""

import os

XLSX_EXTENSION = ".xlsx"
ZIP_EXTENSION = ".zip"
TRANSLATED_FALLBACK_STEM = "translated"
IGNORED_XLSX_PREFIXES = ("~$", "._")


def translated_xlsx_name(filename: str, target_language: str) -> str:
    """Build a translated workbook filename with the target language suffix."""
    return _translated_name(filename, target_language, XLSX_EXTENSION)


def translated_zip_name(filename: str, target_language: str) -> str:
    """Build a translated archive filename with the target language suffix."""
    return _translated_name(filename, target_language, ZIP_EXTENSION)


def is_xlsx_filename(filename: str) -> bool:
    """Return true when filename points to a supported workbook."""
    base_name = os.path.basename(filename)
    if base_name.startswith(IGNORED_XLSX_PREFIXES):
        return False
    return base_name.lower().endswith(XLSX_EXTENSION)


def is_zip_filename(filename: str) -> bool:
    """Return true when filename points to a zip archive."""
    base_name = os.path.basename(filename)
    return base_name.lower().endswith(ZIP_EXTENSION)


def _translated_name(filename: str, target_language: str, extension: str) -> str:
    """Build an output filename with a target-language suffix and extension."""
    base_name = os.path.basename(filename)
    stem, _ = os.path.splitext(base_name)
    if not stem:
        stem = TRANSLATED_FALLBACK_STEM
    return f"{stem}_{target_language}{extension}"
