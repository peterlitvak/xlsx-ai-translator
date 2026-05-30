"""Browser-backed Streamlit UI flow tests for XLSX and ZIP uploads."""

import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path
from typing import Any, ClassVar

PROJECT_ROOT = Path(__file__).parent
FIXTURE_DIR = PROJECT_ROOT / "test_fixtures"
SAMPLE_XLSX_PATH = FIXTURE_DIR / "sample.xlsx"
SAMPLE_ZIP_PATH = FIXTURE_DIR / "sample.zip"
SERVER_START_TIMEOUT_SECONDS = 30
TRANSLATION_TIMEOUT_MS = 120000


def find_available_port() -> int:
    """Return an available local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(("127.0.0.1", 0))
        return int(server_socket.getsockname()[1])


def wait_for_server(url: str) -> None:
    """Wait until the Streamlit server responds to HTTP requests."""
    deadline = time.monotonic() + SERVER_START_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except OSError:
            time.sleep(0.25)
    raise TimeoutError(f"Streamlit server did not start at {url}.")


class TestStreamlitUploadUIFlow(unittest.TestCase):
    """Validate the UI upload and summary flows through a real browser."""

    server_process: ClassVar[subprocess.Popen[bytes]]
    temp_directory: ClassVar[tempfile.TemporaryDirectory[str]]
    app_url: ClassVar[str]
    playwright_context: ClassVar[Any]
    browser: ClassVar[Any]

    @classmethod
    def setUpClass(cls) -> None:
        """Start Streamlit and Playwright once for the UI test class."""
        from playwright.sync_api import sync_playwright

        cls.temp_directory = tempfile.TemporaryDirectory()
        port = find_available_port()
        cls.app_url = f"http://127.0.0.1:{port}"
        env = os.environ.copy()
        env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
        cls.server_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "app.py",
                "--server.headless",
                "true",
                "--server.port",
                str(port),
            ],
            cwd=PROJECT_ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        try:
            wait_for_server(cls.app_url)
            cls.playwright_context = sync_playwright().start()
            cls.browser = cls.playwright_context.chromium.launch()
        except Exception:
            cls.tearDownClass()
            raise

    @classmethod
    def tearDownClass(cls) -> None:
        """Stop browser and Streamlit resources created for UI tests."""
        browser = getattr(cls, "browser", None)
        if browser is not None:
            browser.close()

        playwright_context = getattr(cls, "playwright_context", None)
        if playwright_context is not None:
            playwright_context.stop()

        server_process = getattr(cls, "server_process", None)
        if server_process is not None:
            server_process.terminate()
            try:
                server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.wait(timeout=10)

        temp_directory = getattr(cls, "temp_directory", None)
        if temp_directory is not None:
            temp_directory.cleanup()

    def setUp(self) -> None:
        """Open a clean browser page for each UI flow test."""
        self.page: Any = self.browser.new_page()

    def tearDown(self) -> None:
        """Close the browser page for the completed test."""
        self.page.close()

    def test_single_xlsx_upload_summary_flow(self) -> None:
        sample_path = Path(self.temp_directory.name) / "ui-single.xlsx"
        sample_path.write_bytes(SAMPLE_XLSX_PATH.read_bytes())

        self.page.goto(self.app_url)
        self.page.locator("input[type='file']").set_input_files(str(sample_path))

        self.expect_summary_text("XLSX workbook")
        self.expect_summary_text("ui-single.xlsx")
        self.translate_and_expect_download("XLSX")

    def test_zip_upload_summary_flow(self) -> None:
        sample_path = Path(self.temp_directory.name) / "ui-archive.zip"
        sample_path.write_bytes(SAMPLE_ZIP_PATH.read_bytes())

        self.page.goto(self.app_url)
        self.page.locator("input[type='file']").set_input_files(str(sample_path))

        self.expect_summary_text("ZIP archive")
        self.expect_summary_text("Workbooks detected:")
        self.expect_summary_text("ui-archive.zip")
        self.translate_and_expect_download("ZIP")

    def expect_summary_text(self, text: str) -> None:
        """Assert that text is visible in the translation summary panel."""
        from playwright.sync_api import expect

        summary = self.page.locator("[data-testid='stAlert']").filter(
            has_text="Translation Summary"
        )
        expect(summary).to_be_visible(timeout=10000)
        expect(summary.get_by_text(text)).to_be_visible(timeout=10000)

    def translate_and_expect_download(self, output_type: str) -> None:
        """Run the UI translation and assert that a download button appears."""
        from playwright.sync_api import expect

        self.page.get_by_role("button", name="Translate file").click()
        expect(
            self.page.get_by_text("Translation complete! Download your file below.")
        ).to_be_visible(timeout=TRANSLATION_TIMEOUT_MS)
        expect(
            self.page.get_by_role("button", name=f"Download translated {output_type}")
        ).to_be_visible(timeout=10000)
