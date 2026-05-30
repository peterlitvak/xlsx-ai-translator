# UI Enhancement Plan: XLSX And ZIP Uploads

## Goal

Enhance the Streamlit UI so users can upload either:

- A single `.xlsx` workbook and receive a translated `.xlsx` workbook.
- A `.zip` archive containing one or more `.xlsx` workbooks and receive a translated `.zip` archive.

The underlying workbook translation behavior should continue to use the existing `XLSXTranslator` implementation.

## Current State

- `src/app/streamlit_app.py` accepts `.xlsx` and `.zip` uploads.
- `XLSXTranslator` translates one workbook at a time.
- `src/cli/translate.py` demonstrates multi-file translation by discovering `.xlsx` files under a directory and translating each one.
- Token and cost estimation in the UI currently reads the uploaded workbook directly and estimates usage for that one workbook.

## Target User Flow

### Single Workbook

1. User uploads `source.xlsx`.
2. User chooses source language, target language, and model.
3. UI estimates token usage and cost for the workbook.
4. User starts translation.
5. UI returns `source_<target>.xlsx`.

### ZIP Archive

1. User uploads `source_files.zip`.
2. UI safely inspects the archive and discovers `.xlsx` files recursively.
3. User chooses source language, target language, and model.
4. UI estimates aggregate token usage and cost across discovered workbooks.
5. User starts translation.
6. UI translates each workbook and returns `source_files_<target>.zip`.

## Output Rules

- Single `.xlsx` upload returns a single translated `.xlsx`.
- `.zip` upload returns a `.zip` containing translated `.xlsx` files.
- Preserve relative paths from the uploaded archive.
- Add the target language suffix before each workbook extension.

Example:

```text
input.zip
  reports/q1.xlsx
  nested/team/file.xlsx

output_en.zip
  reports/q1_en.xlsx
  nested/team/file_en.xlsx
```

Non-XLSX files should be skipped in the translated output archive unless a later requirement explicitly asks to preserve them.

## Safety Requirements

- Reject unsafe zip entries that attempt path traversal.
- Ignore directories and hidden system files that are not `.xlsx`.
- Surface a clear UI error when a zip contains no `.xlsx` files.
- Clean up temporary input, extraction, output, and archive files after each translation run.
- Keep OpenAI token and cost aggregation accurate across all translated workbooks.

## UX Requirements

- Use one upload control accepting `.xlsx` and `.zip`.
- Use neutral wording such as "Choose an XLSX or ZIP file" and "Translate file".
- Show detected upload type in the summary panel.
- For zip uploads, show discovered workbook count.
- Show aggregate estimated input tokens, output tokens, and cost.
- During zip translation, show current file progress and per-file translation progress.
- Provide only the relevant download button:
  - `.xlsx` for single workbook uploads.
  - `.zip` for archive uploads.

## Test Strategy

- Unit-test safe zip extraction/path validation.
- Unit-test workbook discovery from extracted archives.
- Unit-test output filename generation for `.xlsx` and `.zip` workflows.
- Unit-test aggregate estimation using small generated workbooks.
- Mock `XLSXTranslator` for batch UI helper tests so tests do not call OpenAI.
- Keep existing translator behavior tests focused on workbook translation and formula handling.

## Open Decisions

- Whether to include a CSV usage report inside translated zip archives.
- Whether to preserve non-XLSX files in the output archive.
- Whether to expose per-file failures as partial success downloads or fail the whole archive translation.

Recommended initial behavior: fail the archive translation if any workbook fails, show the failing relative path, and do not produce a partial zip.
