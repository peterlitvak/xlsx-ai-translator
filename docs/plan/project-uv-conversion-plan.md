# Project UV Conversion Plan

## Goal

Convert the project from `pip` plus `requirements.txt` installation to `uv` project management with:

- `pyproject.toml` as the dependency and project metadata source of truth.
- `uv.lock` as the committed reproducible lockfile.
- `uv run` and `uv sync` as the standard command workflow.
- No required `PYTHONPATH=src` prefix for normal project commands.

The migration should preserve current CLI, Streamlit UI, translation, and test behavior.

Official uv references checked:

- Project management and `uv run`: https://docs.astral.sh/uv/guides/projects/
- Dependency management and importing from requirements files: https://docs.astral.sh/uv/concepts/projects/dependencies/
- Project files, `.venv`, and `uv.lock`: https://docs.astral.sh/uv/concepts/projects/layout/
- Project packaging behavior and `tool.uv.package`: https://docs.astral.sh/uv/concepts/projects/config/

## Current State

- Dependencies are pinned in `requirements.txt`.
- The file appears to be a frozen environment export because it includes both direct and transitive dependencies.
- The project has no `pyproject.toml` or `uv.lock`.
- Commands currently need `PYTHONPATH=src` because the source tree is not installed as a package.
- Tests use `unittest`; the browser-backed tests use Playwright.
- Runtime imports directly use:
  - `dotenv`
  - `langchain_openai`
  - `openpyxl`
  - `pydantic`
  - `streamlit`
  - `tiktoken`
  - `tqdm`

## Target Layout

Add these top-level files:

```text
pyproject.toml
uv.lock
.python-version
```

Keep these existing files and directories:

```text
src/
tests/
resources/
docs/
.local/
```

Remove `requirements.txt` after the `uv` workflow is validated and README commands are updated.

## Dependency Model

Use `pyproject.toml` for direct dependencies only. Do not copy every line from `requirements.txt` into
`project.dependencies` without review because that would preserve transitive dependencies as direct project API.

Recommended runtime dependencies, initially pinned to the current working versions:

```toml
dependencies = [
  "langchain-openai==1.2.2",
  "openpyxl==3.1.5",
  "pydantic==2.13.4",
  "python-dotenv==1.2.2",
  "streamlit==1.58.0",
  "tiktoken==0.13.0",
  "tqdm==4.67.3",
]
```

Recommended development dependency group:

```toml
[dependency-groups]
dev = [
  "black==26.5.1",
  "pip==26.1.1",
  "playwright==1.60.0",
  "pyright==1.1.409",
]

[tool.uv]
default-groups = ["dev"]

[tool.black]
target-version = ["py311"]
```

Use exact pins for the initial migration to reduce behavior drift. Dependency upgrades can be planned separately after
the toolchain conversion is stable.

## Packaging Model

Configure the project as an installed package instead of a virtual dependency-only project.

Recommended approach:

- Add a build backend in `pyproject.toml`.
- Configure package discovery for the existing `src` layout.
- Add a console script for CLI translation.

Example target:

```toml
[project.scripts]
xlsx-translate = "cli.translate:main"

[build-system]
requires = ["setuptools==82.0.1"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

This should let commands run without `PYTHONPATH=src`:

```bash
uv run xlsx-translate --help
uv run python -m unittest discover -s tests
```

## Command Expectations

After migration, use:

```bash
uv sync
uv run xlsx-translate --root ./resources/test_fixtures/sample.xlsx --source ja --target en --estimate
uv run streamlit run src/app/streamlit_app.py
uv run python -m unittest discover -s tests
uv run pyright
uv run black src tests
uv run playwright install chromium
uvx pip-audit --path .venv/lib/python3.11/site-packages --skip-editable --progress-spinner off
```

The live OpenAI and browser-backed tests should continue to run through `uv run python -m unittest discover -s tests`.

## README And Agent Updates

- Replace virtualenv and `pip install -r requirements.txt` setup instructions with `uv sync`.
- Replace `PYTHONPATH=src python -m cli.translate` examples with `uv run xlsx-translate`.
- Replace `PYTHONPATH=src streamlit run ...` with `uv run streamlit run ...`.
- Replace test commands with `uv run ...` commands.
- Update `AGENTS.md` common commands after the conversion is complete.

## Test Strategy

- Run a dependency sync from a clean environment.
- Confirm CLI module and console script both work.
- Confirm Streamlit starts through `uv run`.
- Run formatting, type checking, and tests through `uv run`.
- Audit the synced environment with `pip-audit`.
- Run the full live integration suite when `OPENAI_API_KEY` and Playwright Chromium are available.

## Open Decisions

- Whether to keep `requirements.txt` as an exported compatibility artifact.

Recommended initial behavior: remove `requirements.txt` as a source of truth after `uv.lock` is committed. If external
deployments still require it, generate it from `uv.lock` in a later dedicated compatibility task.

- Whether to keep using generic top-level package names such as `app`, `cli`, `services`, and `utils`.

Recommended initial behavior: keep the current package names for this migration and avoid combining package renaming with
toolchain conversion.

- Whether to upgrade dependencies during conversion.

Recommended initial behavior: do not upgrade dependencies in the migration. Convert first with exact current versions,
then plan dependency upgrades separately.
