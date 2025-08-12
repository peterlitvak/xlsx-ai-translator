import os
import shutil
import subprocess
import tempfile
import openpyxl
import unittest

class TestCLITranslateIntegration(unittest.TestCase):
    def setUp(self):
        self.base_dir = tempfile.mkdtemp()
        self.test_xlsx_path = os.path.abspath("test.xlsx")
        self.create_test_dir_structure()

    def tearDown(self):
        shutil.rmtree(self.base_dir)

    def create_test_dir_structure(self):
        os.makedirs(os.path.join(self.base_dir, "subdir1"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "subdir2"), exist_ok=True)
        # Place xlsx files
        shutil.copy(self.test_xlsx_path, os.path.join(self.base_dir, "test1.xlsx"))
        shutil.copy(self.test_xlsx_path, os.path.join(self.base_dir, "subdir1", "test2.xlsx"))
        # Place non-xlsx files
        with open(os.path.join(self.base_dir, "file.txt"), "w") as f:
            f.write("This is a text file.")
        with open(os.path.join(self.base_dir, "subdir2", "file.csv"), "w") as f:
            f.write("col1,col2\n1,2")

    def validate_translated_files(self, target_lang):
        expected = [
            os.path.join(self.base_dir, target_lang, "test1.xlsx"),
            os.path.join(self.base_dir, "subdir1", target_lang, "test2.xlsx"),
        ]
        for path in expected:
            self.assertTrue(os.path.exists(path), f"Missing translated file: {path}")
            wb = openpyxl.load_workbook(path)
            sheet = wb.active
            found_nonempty = any(cell.value for row in sheet.iter_rows() for cell in row)
            self.assertTrue(found_nonempty, f"Translated file {path} appears empty")

    def test_cli_translate_integration(self):
        # Run CLI: ja -> en
        result = subprocess.run([
            "python", "cli_translate.py",
            "--root", self.base_dir,
            "--source", "ja",
            "--target", "en"
        ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
        print("STDOUT:\n", result.stdout)
        print("STDERR:\n", result.stderr)
        self.assertEqual(result.returncode, 0, f"CLI failed: {result.stderr}")
        self.validate_translated_files("en")

if __name__ == "__main__":
    unittest.main()
