# Project Structure Modularization Plan

## Goal

Move the project to a clearer Python source layout that separates runtime code, tests, resources, and documentation.
The restructuring should improve maintainability without changing translator, CLI, or Streamlit behavior.

The target top-level project directories are:

- `src/` for application code.
- `tests/` for automated tests and test-only utilities.
- `resources/` for committed sample workbooks, zip archives, and other static resources.
- `docs/` for planning and implementation documentation.
- `.local/` for ignored local e2e tests, debug artifacts, generated reports, and other work-in-progress files.

## Current State

- Runtime modules are stored under `src/`:
  - `src/app/streamlit_app.py` contains the Streamlit UI entry point.
  - `src/cli/translate.py` contains CLI parsing, reporting, and translation orchestration.
  - `src/services/xlsx_translator.py` contains the `XLSXTranslator` service and OpenAI-backed workbook translation logic.
  - `src/services/translation_estimator.py` contains workbook text extraction, token estimation, and cost estimation.
  - `src/services/translation_workflow.py` contains single-workbook and zip upload translation orchestration.
  - `src/services/model_pricing.py` contains model pricing constants.
  - `src/utils/` contains filename and zip archive utilities.
- Test modules are stored under `tests/`.
- Test fixture builders are stored under `tests/utils/`.
- Committed sample fixtures are stored under `resources/test_fixtures/`.
- Documentation is stored under `docs/`, with `docs/plan/` and `docs/impl/`.
- `README.md` describes user-facing setup, CLI usage, UI usage, and test commands.
- `AGENTS.md` is the repository entry point for agents and contributors.

## Target Package Layout

```text
src/
  app/
    __init__.py
    streamlit_app.py
  cli/
    __init__.py
    copy_pattern.py
    translate.py
  services/
    __init__.py
    model_pricing.py
    translation_estimator.py
    translation_workflow.py
    xlsx_translator.py
  utils/
    __init__.py
    file_names.py
    zip_archives.py
tests/
  utils/
    sample_workbooks.py
  test_app_helpers.py
  test_cli_translate.py
  test_openai_integration.py
  test_translator.py
  test_ui_flow.py
resources/
  test_fixtures/
    sample.xlsx
    sample.zip
    test.xlsx
docs/
  plan/
  impl/
.local/
```

## Package Responsibilities

### `src/app/`

Contains the Streamlit application only.

- Owns page configuration, form controls, progress widgets, summary rendering, and download buttons.
- Imports services for estimation and translation workflows.
- Does not contain archive safety logic, workbook parsing, token math, or OpenAI translation logic.

Recommended file:

- `src/app/streamlit_app.py` for the Streamlit entry point.

### `src/cli/`

Contains command-line entry points and CLI-specific reporting.

- Owns `argparse` configuration, process exit behavior, terminal progress display, and CSV report writing.
- Imports services for workbook discovery, estimation, and translation.
- Does not duplicate token estimation or workbook text extraction logic.

Recommended file:

- `src/cli/translate.py` for the current `cli_translate.py` behavior.

### `src/services/`

Contains domain and application services.

- Owns OpenAI-backed XLSX translation.
- Owns token and cost estimation.
- Owns upload translation workflows that coordinate single-workbook and zip-archive translation.
- Owns DTO-style result models used across UI and tests.

Recommended files:

- `src/services/xlsx_translator.py` for `XLSXTranslator`, `TranslationOutput`, and `translate_xlsx_file`.
- `src/services/model_pricing.py` for model pricing constants.
- `src/services/translation_estimator.py` for workbook text extraction, token estimation, output token estimation, and cost calculation.
- `src/services/translation_workflow.py` for `translate_single_xlsx`, `translate_xlsx_zip`, result models, translator protocol, and progress models.

### `src/utils/`

Contains small, deterministic utility modules.

- Owns filename classification and translated output filename generation.
- Owns safe zip extraction, zip member path validation, workbook discovery under directories, and zip creation.
- Does not import Streamlit, CLI modules, or OpenAI services.

Recommended files:

- `src/utils/file_names.py` for `is_xlsx_filename`, `is_zip_filename`, `translated_xlsx_name`, and `translated_zip_name`.
- `src/utils/zip_archives.py` for `UnsafeZipError`, `safe_extract_zip`, `find_xlsx_files`, and archive creation utilities.

### `tests/`

Contains all tests.

- Move root `test_*.py` files into `tests/`.
- Keep tests organized by behavior, not by implementation detail.
- Store test-only workbook factory utilities in `tests/utils/`.
- Update subprocess and browser-backed tests to use the new CLI and Streamlit paths.

### `resources/`

Contains committed static resources.

- Move `test_fixtures/sample.xlsx` and `test_fixtures/sample.zip` to `resources/test_fixtures/`.
- Keep generated or user-specific files out of this directory unless they are intentionally committed fixtures.
- Do not store secrets, `.env` files, or generated translation outputs here.

### `.local/`

Contains ignored local work artifacts.

- Use this directory for temporary e2e experiments, browser screenshots, debug logs, generated reports, and scratch fixtures.
- Do not place source code, committed tests, canonical fixtures, or secrets here.
- Keep `.local/` in `.gitignore` so local artifacts do not pollute source control.

## Import And Command Expectations

Runtime modules should use absolute imports from packages under `src`.

Examples:

```python
from utils.file_names import is_xlsx_filename
from services.xlsx_translator import XLSXTranslator
from services.translation_estimator import estimate_xlsx_file
```

Expected commands after migration:

```bash
PYTHONPATH=src .venv/bin/python -m cli.translate --root ./resources/test_fixtures/sample.xlsx --source ja --target en --estimate
PYTHONPATH=src .venv/bin/streamlit run src/app/streamlit_app.py
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
.venv/bin/black src tests
.venv/bin/pyright
```

`pyrightconfig.json` should include `src` in the analysis path so imports resolve without ad hoc test configuration.

## Documentation Requirements

- Keep `README.md` focused on user-facing installation, usage, and test commands.
- Keep `AGENTS.md` as the contributor and agent entry point:
  - Link to `README.md`.
  - Link to `docs/plan/` and `docs/impl/`.
  - Explain where source, tests, resources, and project docs live.
- Keep planning docs under `docs/plan/`.
- Keep implementation notes and milestone status under `docs/impl/`.
- Update related documentation in the same change as any source layout migration.

## Test Strategy

- Run fast unit tests after each move or split.
- Keep pure utility tests focused on deterministic path, filename, archive, and estimator behavior.
- Run CLI tests after moving `src/cli/translate.py`.
- Run Streamlit browser flow tests after moving the UI entry point.
- Run live OpenAI integration tests only when required by the implementation milestone or before final signoff.

## Open Decisions

- Whether to add temporary root-level compatibility launchers such as `app.py` or `cli_translate.py`.

Recommended initial behavior: do not keep compatibility launchers unless an external consumer depends on the old commands. Update `README.md`, tests, and docs to the new commands instead.

- Whether to introduce a project namespace package such as `translation_ai`.

Recommended initial behavior: follow the requested direct packages under `src/`: `app`, `cli`, `services`, and `utils`.

- Whether `resources/test_fixtures/` should eventually be renamed to `resources/samples/`.

Recommended initial behavior: use `resources/test_fixtures/` because the current files are test fixtures and existing tests already treat them that way.
