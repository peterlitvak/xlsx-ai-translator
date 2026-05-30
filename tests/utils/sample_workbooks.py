"""Utilities for creating small XLSX and ZIP samples for integration tests."""

import zipfile
from pathlib import Path

import openpyxl

DEFAULT_WORKBOOK_NAME = "sample.xlsx"
DEFAULT_ZIP_WORKBOOK_PATH = "nested/sample.xlsx"
VISIBLE_SHEET_NAME = "挨拶"
HIDDEN_SHEET_NAME = "非表示"
SOURCE_TEXT = "こんにちは"
SECONDARY_SOURCE_TEXT = "世界"
HIDDEN_SOURCE_TEXT = "秘密"


def create_sample_xlsx_file(output_path: str | Path) -> Path:
    """Create a minimal workbook with visible text and a hidden sheet."""
    workbook_path = Path(output_path)
    workbook_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = openpyxl.Workbook()
    visible_sheet = workbook.active
    if visible_sheet is None:
        raise RuntimeError("OpenPyXL did not create an active worksheet.")
    visible_sheet.title = VISIBLE_SHEET_NAME
    visible_sheet["A1"] = SOURCE_TEXT
    visible_sheet["A2"] = SECONDARY_SOURCE_TEXT

    hidden_sheet = workbook.create_sheet(HIDDEN_SHEET_NAME)
    hidden_sheet.sheet_state = "hidden"
    hidden_sheet["A1"] = HIDDEN_SOURCE_TEXT

    workbook.save(workbook_path)
    return workbook_path


def create_sample_zip_file(
    zip_path: str | Path,
    workbook_member_path: str = DEFAULT_ZIP_WORKBOOK_PATH,
) -> Path:
    """Create a zip archive containing one generated XLSX workbook."""
    archive_path = Path(zip_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    workbook_path = archive_path.with_suffix(".xlsx")
    create_sample_xlsx_file(workbook_path)

    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        archive.write(workbook_path, arcname=workbook_member_path)

    return archive_path
