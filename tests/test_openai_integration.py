"""Live OpenAI integration tests for XLSX and ZIP translation flows."""

import os
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

import openpyxl

from services.translation_workflow import (
    ZIP_MIME_TYPE,
    XLSX_MIME_TYPE,
    translate_single_xlsx,
    translate_xlsx_zip,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = PROJECT_ROOT / "resources" / "test_fixtures"
SAMPLE_XLSX_PATH = FIXTURE_DIR / "sample.xlsx"
SAMPLE_ZIP_PATH = FIXTURE_DIR / "sample.zip"
OPENAI_TEST_MODEL = os.getenv("OPENAI_TEST_MODEL", "gpt-4o-mini")


def visible_workbook_values(workbook_bytes: bytes) -> list[str]:
    """Read visible string values from workbook bytes."""
    workbook = openpyxl.load_workbook(BytesIO(workbook_bytes))
    return [
        str(cell.value)
        for sheet in workbook.worksheets
        if getattr(sheet, "sheet_state", "visible") == "visible"
        for row in sheet.iter_rows()
        for cell in row
        if isinstance(cell.value, str) and cell.value.strip()
    ]


class TestOpenAITranslationIntegration(unittest.TestCase):
    """Verify real OpenAI translation through app orchestration helpers."""

    def test_translate_sample_xlsx_with_real_openai(self) -> None:
        result = translate_single_xlsx(
            uploaded_bytes=SAMPLE_XLSX_PATH.read_bytes(),
            original_filename=SAMPLE_XLSX_PATH.name,
            target_language="en",
            model_name=OPENAI_TEST_MODEL,
            max_workers=1,
        )

        self.assertEqual("sample_en.xlsx", result.filename)
        self.assertEqual(XLSX_MIME_TYPE, result.mime_type)
        self.assertGreater(result.usage.input_tokens, 0)
        self.assertGreater(result.usage.output_tokens, 0)
        self.assertGreater(result.usage.cost, 0.0)
        self.assertTrue(visible_workbook_values(result.data))

    def test_translate_sample_zip_with_real_openai(self) -> None:
        result = translate_xlsx_zip(
            uploaded_bytes=SAMPLE_ZIP_PATH.read_bytes(),
            original_filename=SAMPLE_ZIP_PATH.name,
            target_language="en",
            model_name=OPENAI_TEST_MODEL,
            max_workers=1,
        )

        self.assertEqual("sample_en.zip", result.filename)
        self.assertEqual(ZIP_MIME_TYPE, result.mime_type)
        self.assertEqual(1, result.workbook_count)
        self.assertGreater(result.usage.input_tokens, 0)
        self.assertGreater(result.usage.output_tokens, 0)
        self.assertGreater(result.usage.cost, 0.0)

        with zipfile.ZipFile(BytesIO(result.data)) as archive:
            self.assertEqual(["nested/sample_en.xlsx"], archive.namelist())
            self.assertTrue(
                visible_workbook_values(archive.read("nested/sample_en.xlsx"))
            )


if __name__ == "__main__":
    unittest.main()
