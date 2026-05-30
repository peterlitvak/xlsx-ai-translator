# Project Structure Modularization Implementation Notes

## Scope

Refactor repository layout and imports while preserving current behavior:

- Streamlit UI still translates `.xlsx` and `.zip` uploads.
- CLI still accepts one workbook or a directory tree.
- Translation internals still use `XLSXTranslator`.
- Existing tests should continue to cover the same behavior after they move under `tests/`.

Avoid functional rewrites unless they are needed to remove duplicated logic or make the package boundaries coherent.

## Proposed File Changes

### Documentation

- `doc/` -> `docs/`
  - Keep the existing `plan/` and `impl/` subdirectories.
  - Update internal references from `doc/...` to `docs/...`.
- `AGENTS.md`
  - Expand it into the project entry point for agents and contributors.
  - Reference `README.md`, `docs/plan/`, and `docs/impl/`.
- `README.md`
  - Update commands after the source and test moves are complete.
- `.gitignore`
  - Ignore `.local/` for local e2e tests and debug artifacts.

### Runtime Source

| Current File | Target File | Notes |
| --- | --- | --- |
| `app.py` | `src/app/streamlit_app.py` | Keep Streamlit UI rendering here; import services for estimation and translation. |
| `cli_translate.py` | `src/cli/translate.py` | Keep CLI parsing and report writing here; reuse service/utility modules. |
| `copy_pattern.py` | `src/cli/copy_pattern.py` | Keep the existing copy utility under CLI code. |
| `translator.py` | `src/services/xlsx_translator.py` | Keep `XLSXTranslator`, `TranslationOutput`, and `translate_xlsx_file` here. |
| `pricing.py` | `src/services/model_pricing.py` | Keep `MODEL_PRICING` centralized here. |
| `app_helpers.py` | split across `src/services/` and `src/utils/` | Move domain workflows to services and pure utilities to utils. |

### Utility And Service Split

Move these responsibilities out of `app_helpers.py`:

| Responsibility | Target Module |
| --- | --- |
| `is_xlsx_filename`, `is_zip_filename`, translated output names | `src/utils/file_names.py` |
| `UnsafeZipError`, safe extraction, path validation, workbook discovery, zip creation | `src/utils/zip_archives.py` |
| Workbook text extraction, token estimates, output token factors, cost math | `src/services/translation_estimator.py` |
| Translation result models, progress models, translator protocol, single XLSX workflow, zip workflow | `src/services/translation_workflow.py` |

Move duplicated CLI estimation and workbook discovery logic to these same utility/service modules so the CLI and UI use one implementation.

### Tests And Resources

| Current Path | Target Path | Notes |
| --- | --- | --- |
| `test_app_helpers.py` | `tests/test_app_helpers.py` | Update imports to new utility/service modules. |
| `test_cli_translate.py` | `tests/test_cli_translate.py` | Update subprocess command to `uv run xlsx-translate`. |
| `test_openai_integration.py` | `tests/test_openai_integration.py` | Update imports and fixture paths. |
| `test_translator.py` | `tests/test_translator.py` | Update import to `services.xlsx_translator`. |
| `test_ui_flow.py` | `tests/test_ui_flow.py` | Update Streamlit command to `src/app/streamlit_app.py`. |
| `sample_workbooks.py` | `tests/utils/sample_workbooks.py` | Test-only fixture builder. |
| `test_fixtures/` | `resources/test_fixtures/` | Committed sample XLSX and ZIP fixtures. |
| `test.xlsx` | `resources/test_fixtures/test.xlsx` | Formula-heavy workbook fixture used by translator tests. |
| `.local/` | `.local/` | Ignored local workspace for temporary e2e tests and debug artifacts. |

## Dependency Direction

Keep imports flowing in one direction:

```text
app -> services -> utils
cli -> services -> utils
tests -> app/services/utils/cli
```

Rules:

- `utils` must not import `app`, `cli`, Streamlit, LangChain, or OpenAI clients.
- `services` may import `utils` and third-party workbook/LLM libraries.
- `app` may import `services` and `utils`, but should not own business logic.
- `cli` may import `services` and `utils`, but should not duplicate estimator logic.
- Tests may import any public module needed to verify behavior.

## Implementation Steps

1. Rename documentation references.
   - Move `doc/` to `docs/`.
   - Update existing docs that still mention `doc/...`.
   - Update `AGENTS.md` to reference `README.md`, `docs/plan/`, and `docs/impl/`.

2. Create package directories.
   - Add `src/app/`, `src/cli/`, `src/services/`, and `src/utils/`.
   - Add `__init__.py` files to each package.

3. Move stable service modules.
   - Move `pricing.py` to `src/services/model_pricing.py`.
   - Move `translator.py` to `src/services/xlsx_translator.py`.
   - Update imports from `pricing` to `services.model_pricing`.
   - Run translator-focused tests after import updates.

4. Split utility and workflow modules.
   - Move filename utilities to `src/utils/file_names.py`.
   - Move zip utilities to `src/utils/zip_archives.py`.
   - Move estimation utilities to `src/services/translation_estimator.py`.
   - Move upload translation workflows to `src/services/translation_workflow.py`.
   - Update the UI and tests to import from the new modules.

5. Move entry points.
   - Move `app.py` to `src/app/streamlit_app.py`.
   - Move `cli_translate.py` to `src/cli/translate.py`.
   - Update subprocess and browser tests to use the new paths.

6. Move tests and resources.
   - Move root `test_*.py` files to `tests/`.
   - Move `sample_workbooks.py` to `tests/utils/sample_workbooks.py`.
   - Move `test_fixtures/` to `resources/test_fixtures/`.
   - Update fixture path constants.

7. Update project configuration and user docs.
   - Update `pyrightconfig.json` so `src` imports resolve.
   - Update `README.md` commands and examples.
   - Update any remaining references to old root module paths.

8. Validate.
   - Run Black on touched Python files.
   - Run Pyright.
   - Run the full unittest suite.
   - Run CLI and Streamlit smoke commands if full UI tests are not run.

9. Add local artifact workspace.
   - Create top-level `.local/`.
   - Add `.local/` to `.gitignore`.
   - Document `.local/` as the place for temporary e2e tests, debug logs, screenshots, generated reports, and scratch artifacts.

## Validation Commands

Use the uv-managed project environment:

```bash
uv run python -m unittest discover -s tests
uv run xlsx-translate --help
uv run streamlit run src/app/streamlit_app.py
uv run black src tests
uv run pyright
```

The Streamlit command is interactive. For automated validation, prefer the existing browser-backed UI flow test after its entry-point path is updated.

## Commit Message Requirements

Commit messages must always be detailed. Use a short milestone-prefixed subject, then include a body that explains the
main structural changes, documentation updates, and validation commands run.

## Implementation Milestones

Status key: ✅ done, 🟡 in progress, ⚪ not started, 🛑 blocked.

| Milestone | Status | Work Item | Notes |
| --- | --- | --- | --- |
| M1 | ✅ | Document target structure and migration notes | Captured in `docs/plan/project-structure-modularization-plan.md` and this file. |
| M2 | ✅ | Standardize docs directory and AGENTS entry point | Renamed `doc` to `docs`, updated references, and made `AGENTS.md` a useful source map. |
| M3 | ✅ | Create `src` packages and move core services | Moved pricing and translator modules under `src/services/`. |
| M4 | ✅ | Split utility and workflow modules | Moved filename/archive utilities to `src/utils/` and estimation/workflow logic to `src/services/`. |
| M5 | ✅ | Move UI and CLI entry points | Moved UI and CLI to `src/app/streamlit_app.py` and `src/cli/translate.py`. |
| M6 | ✅ | Move tests and resources | Put tests under `tests/` and committed fixtures under `resources/test_fixtures/`. |
| M7 | ✅ | Run formatting, type checking, and test validation | Black, Pyright, unittest, CLI smoke, and UI flow coverage passed. |
| M8 | ✅ | Add local artifact workspace | Added ignored top-level `.local/` for temporary e2e tests and debug artifacts. |
