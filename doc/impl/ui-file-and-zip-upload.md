# UI Enhancement Implementation Notes: XLSX And ZIP Uploads

## Scope

Implement upload orchestration in `app.py` while reusing `XLSXTranslator` for each workbook. Avoid changing translation internals unless a defect blocks the UI workflow.

## Proposed File Changes

- `app.py`
  - Add zip handling imports: `zipfile`, `pathlib.Path`, and any typing helpers needed.
  - Replace single-workbook upload logic with dispatch based on uploaded file extension.
  - Use helper functions for estimation, output naming, safe zip extraction, workbook discovery, and batch translation.
- `app_helpers.py`
  - Keep Streamlit-free helper functions for estimation, output naming, safe zip extraction, workbook discovery, and batch translation.
- `test_app.py`
  - Add unit tests for new pure helper functions.
  - Mock translator calls for UI batch orchestration tests.
- `README.md`
  - Update Streamlit UI usage docs after implementation.

## Helper Functions

Recommended helpers for `app_helpers.py`:

```python
def is_xlsx_filename(filename: str) -> bool:
    """Return true when filename points to a supported workbook."""


def is_zip_filename(filename: str) -> bool:
    """Return true when filename points to a zip archive."""


def translated_xlsx_name(filename: str, target_language: str) -> str:
    """Build a translated workbook filename with the target language suffix."""


def translated_zip_name(filename: str, target_language: str) -> str:
    """Build a translated archive filename with the target language suffix."""


def safe_extract_zip(zip_path: str, extract_dir: str) -> None:
    """Extract a zip archive only if all members stay inside extract_dir."""


def find_xlsx_files(root_dir: str) -> list[str]:
    """Recursively discover workbook files below root_dir."""


def estimate_xlsx_file(file_path: str, source_language: str, target_language: str, model_name: str) -> tuple[int, int, float]:
    """Estimate input tokens, output tokens, and cost for one workbook."""
```

The existing UI estimation code has been moved into `estimate_xlsx_file` so both single and zip workflows use the same path.

## Single XLSX Flow

1. Save uploaded bytes to a temporary `.xlsx`.
2. Estimate usage from that temporary file.
3. Run `XLSXTranslator`.
4. Write translated output to a temporary `.xlsx`.
5. Render `st.download_button` with:
   - Filename: `<original_base>_<target>.xlsx`
   - MIME: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

## ZIP Flow

1. Save uploaded bytes to a temporary `.zip`.
2. Safely extract the archive into a temporary input directory.
3. Discover `.xlsx` files recursively under the extracted directory.
4. If no workbooks are found, show `st.error` and stop.
5. Estimate aggregate usage by summing `estimate_xlsx_file` across discovered workbooks.
6. For each workbook:
   - Compute its relative path from the extraction root.
   - Translate it to a matching path under a temporary output directory.
   - Add the target language suffix to the workbook basename.
   - Accumulate actual input tokens, output tokens, and cost.
7. Build a translated zip from the temporary output directory.
8. Render `st.download_button` with:
   - Filename: `<original_zip_base>_<target>.zip`
   - MIME: `application/zip`

## Progress Handling

For single workbook uploads, keep the current progress bar behavior.

For zip uploads, use two progress indicators:

- Overall archive progress by workbook count.
- Current workbook translation progress using `translator.translate_with_progress()`.

Progress text should include the current relative workbook path so failures are actionable.

## Error Handling

- Unsupported extension: show a clear Streamlit error.
- Unsafe zip member: reject the archive and show a clear error.
- Zip with no workbooks: show a clear error.
- Workbook translation failure: stop the batch and show the failing relative path.
- Cleanup failures should be logged but should not replace the user-facing translation error.

## Testing Details

Each implementation milestone should include relevant unit or integration coverage in the same change.

Run Black and Pyright before finalizing each implementation milestone. Use the project virtualenv:

```bash
.venv/bin/python -m black .
.venv/bin/pyright
```

Use committed sample XLSX/ZIP fixtures for integration flows. Keep `openpyxl` fixture utilities available for refreshing or creating additional samples.

Mock `XLSXTranslator` in UI orchestration tests:

- `translate_with_progress()` yields deterministic progress values.
- `get_result()` writes or copies a generated workbook to the requested output path.
- Actual usage attributes return fixed token and cost values for aggregation checks.

Live OpenAI calls and browser-backed UI checks run as part of the integration suite. Keep fixtures small to limit API usage and execution time.

## Implementation Milestones

Status key: ✅ done, 🟡 in progress, ⚪ not started, 🛑 blocked.

| Milestone | Status | Work Item | Notes |
| --- | --- | --- | --- |
| M1 | ✅ | Document target UI behavior and output rules | Captured in `doc/plan/ui-file-and-zip-upload.md`. |
| M2 | ✅ | Extract reusable estimation helpers | Moved workbook text extraction, token estimation, output token estimation, and cost math into `app_helpers.py`; added `test_app_helpers.py` unit and integration-style coverage; validated with Black and Pyright. |
| M3 | ✅ | Add single XLSX orchestration helper | Moved single-workbook temp-file translation orchestration into `translate_single_xlsx`; added fake-translator unit coverage; validated with Black, Pyright, and helper tests. |
| M4 | ✅ | Add safe ZIP extraction and workbook discovery | Added `safe_extract_zip`, `UnsafeZipError`, `is_xlsx_filename`, and `find_xlsx_files`; covered normal extraction, traversal rejection, absolute path rejection, and workbook discovery filtering. |
| M5 | ✅ | Add ZIP batch translation and archive creation | Preserve relative paths and suffix translated workbook names. |
| M6 | ✅ | Update Streamlit controls and summary panel | Accept `.xlsx` and `.zip`, show workbook count for archives. |
| M7 | ✅ | Add batch workflow integration tests | Added committed XLSX/ZIP samples, CLI single-file and directory source coverage, live OpenAI integration tests, and browser-backed UI upload/translation flow tests. |
| M8 | ✅ | Update README UI instructions | Documented CLI single-file and directory inputs, UI XLSX/ZIP upload and download behavior, zip path preservation, progress, usage summaries, and test setup. |
