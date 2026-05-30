"""Integration coverage for CLI source discovery and translation output."""

import csv
import shutil
import subprocess
import sys
import tempfile
import unittest
import os
from pathlib import Path

import openpyxl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = PROJECT_ROOT / "resources" / "test_fixtures"
SAMPLE_XLSX_PATH = FIXTURE_DIR / "sample.xlsx"
OPENAI_TEST_MODEL = "gpt-4o-mini"


class TestCLITranslateIntegration(unittest.TestCase):
    """Validate CLI behavior for both single-file and directory sources."""

    def run_cli(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """Run the CLI module with the current Python interpreter."""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "cli.translate", *args],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            env=env,
            check=False,
        )

    def read_report_rows(self, report_path: Path) -> list[list[str]]:
        """Read a generated CSV report into rows."""
        with report_path.open(newline="") as report_file:
            return list(csv.reader(report_file))

    def assert_workbook_has_content(self, workbook_path: Path) -> None:
        """Assert that an output workbook exists and contains visible values."""
        self.assertTrue(workbook_path.exists(), f"Missing workbook: {workbook_path}")
        workbook = openpyxl.load_workbook(workbook_path)
        visible_values = [
            cell.value
            for sheet in workbook.worksheets
            if getattr(sheet, "sheet_state", "visible") == "visible"
            for row in sheet.iter_rows()
            for cell in row
            if cell.value
        ]
        self.assertTrue(visible_values, f"Workbook appears empty: {workbook_path}")

    def test_cli_estimate_accepts_single_file_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_path = temp_path / "source.xlsx"
            shutil.copy(SAMPLE_XLSX_PATH, source_path)

            result = self.run_cli(
                [
                    "--root",
                    str(source_path),
                    "--source",
                    "ja",
                    "--target",
                    "en",
                    "--model",
                    OPENAI_TEST_MODEL,
                    "--estimate",
                ]
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("Files processed : 1", result.stdout)
            report_paths = list(temp_path.glob("estimate_report_ja_to_en_*.csv"))
            self.assertEqual(1, len(report_paths))
            rows = self.read_report_rows(report_paths[0])
            self.assertEqual("source.xlsx", rows[1][0])
            self.assertEqual("TOTAL", rows[2][0])

    def test_cli_estimate_accepts_directory_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            nested_dir = temp_path / "nested"
            nested_dir.mkdir()
            shutil.copy(SAMPLE_XLSX_PATH, temp_path / "root.xlsx")
            shutil.copy(SAMPLE_XLSX_PATH, nested_dir / "team.xlsx")
            (temp_path / "notes.txt").write_text("Ignore me.", encoding="utf-8")

            result = self.run_cli(
                [
                    "--root",
                    str(temp_path),
                    "--source",
                    "ja",
                    "--target",
                    "en",
                    "--model",
                    OPENAI_TEST_MODEL,
                    "--estimate",
                ]
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("Files processed : 2", result.stdout)
            report_paths = list(temp_path.glob("estimate_report_ja_to_en_*.csv"))
            self.assertEqual(1, len(report_paths))
            rows = self.read_report_rows(report_paths[0])
            self.assertEqual(
                ["nested/team.xlsx", "root.xlsx"], sorted(row[0] for row in rows[1:3])
            )
            self.assertEqual("TOTAL", rows[3][0])

    def test_cli_translate_single_file_with_real_openai(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_path = temp_path / "source.xlsx"
            shutil.copy(SAMPLE_XLSX_PATH, source_path)

            result = self.run_cli(
                [
                    "--root",
                    str(source_path),
                    "--source",
                    "ja",
                    "--target",
                    "en",
                    "--model",
                    OPENAI_TEST_MODEL,
                ]
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assert_workbook_has_content(temp_path / "en" / "source_en.xlsx")
            self.assertEqual(
                1, len(list(temp_path.glob("actual_report_ja_to_en_*.csv")))
            )

    def test_cli_translate_directory_with_real_openai(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            nested_dir = temp_path / "nested"
            nested_dir.mkdir()
            shutil.copy(SAMPLE_XLSX_PATH, temp_path / "root.xlsx")
            shutil.copy(SAMPLE_XLSX_PATH, nested_dir / "team.xlsx")

            result = self.run_cli(
                [
                    "--root",
                    str(temp_path),
                    "--source",
                    "ja",
                    "--target",
                    "en",
                    "--model",
                    OPENAI_TEST_MODEL,
                ]
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assert_workbook_has_content(temp_path / "en" / "root_en.xlsx")
            self.assert_workbook_has_content(nested_dir / "en" / "team_en.xlsx")
            self.assertEqual(
                1, len(list(temp_path.glob("actual_report_ja_to_en_*.csv")))
            )


if __name__ == "__main__":
    unittest.main()
