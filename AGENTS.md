# Project Agent Instructions

These instructions apply to the whole repository.

## Project Overview

This project is an XLSX LLM Translator: a Python service, command-line interface, and Streamlit UI for translating Excel
workbooks with OpenAI-backed LangChain models.

Use these files as the main project entry points:

- [README.md](./README.md) for installation, usage, current commands, and user-facing behavior.
- [docs/plan/](./docs/plan/) for planned behavior, requirements, and design constraints.
- [docs/impl/](./docs/impl/) for implementation notes, file-level migration guidance, milestones, and validation steps.
- Tests for executable behavior and regression coverage.

## Current Structure

The repository uses a modular source layout:

- `src/app/streamlit_app.py` contains the Streamlit UI entry point.
- `src/cli/translate.py` contains the CLI entry point.
- `src/services/` contains workbook translation, estimation, pricing, and upload orchestration services.
- `src/utils/` contains deterministic filename and zip archive utilities.
- `tests/` contains the test suite.
- `tests/utils/` contains test-only workbook fixture builders.
- `resources/test_fixtures/` contains committed workbook and zip fixtures.
- `docs/` contains planning and implementation documentation.
- `.local/` is an ignored local workspace for temporary e2e tests, debug files, generated reports, and other artifacts created while working.

The modularization work is documented in
[docs/plan/project-structure-modularization-plan.md](./docs/plan/project-structure-modularization-plan.md) and
[docs/impl/project-structure-modularization-impl.md](./docs/impl/project-structure-modularization-impl.md).

## Common Commands

Use the uv-managed project environment:

```bash
uv run python -m unittest discover -s tests
uv run black <touched-python-files>
uv run pyright
uv run xlsx-translate --help
uv run streamlit run src/app/streamlit_app.py
```

The live OpenAI and browser-backed tests require the environment described in `README.md`, including `OPENAI_API_KEY`
and Playwright Chromium setup.

## Coding Guidelines

- Use double quotes for strings.
- Use type hints for function parameters, return values, and variables.
- Write clear and concise docstrings for modules, classes, and methods.
- Use the `unittest` module when unit tests are requested.
- Keep changes minimal, focused, and aligned with the existing docs and code patterns.
- Run Black and Pyright on touched Python files before finalizing Python changes.

## Documentation Guidelines

- Update `README.md` when user-facing commands, setup, or behavior changes.
- Update the relevant file in `docs/plan/` when requirements or target behavior change.
- Update the relevant file in `docs/impl/` when implementation sequencing, file placement, or milestone status changes.
- Keep `AGENTS.md` as a concise project map rather than duplicating every detail from the README or implementation docs.

## Editing, Refactoring, And Debugging

- Check the relevant plan and implementation docs before starting larger changes.
- Preserve existing behavior unless the task explicitly changes it.
- Prefer small, verifiable moves when refactoring project structure.
- When project-aware JetBrains MCP tooling is available, use it for project file manipulation, refactoring, and debugging.

## Commit Guidelines

- Commit messages must always be detailed.
- Use a concise subject that includes the relevant milestone, task, or story code when one exists.
- Include a body that summarizes the main files or areas changed, why the change was made, and the validation that was run.
