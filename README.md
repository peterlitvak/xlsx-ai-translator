# XLSX LLM Translator Backend

A Python service that accepts XLSX files, extracts text, translates it using LangChain + OpenAI GPT-4o, and returns a translated XLSX file.

## Features
- Translate all text in XLSX files using GPT-4o
- Simple function: `translate_xlsx_file(input_path, output_path, target_language)`

## Usage Example

```python
from translator import translate_xlsx_file

translate_xlsx_file('input.xlsx', 'output.xlsx', target_language='fr')
```

## Installation

### 1. Clone the repository

```bash
$ git clone https://github.com/your-org/xlsx-llm-translator.git
$ cd xlsx-llm-translator
```

### 2. Create & activate a virtual environment (recommended)

```bash
$ python3 -m venv .venv
$ source .venv/bin/activate          # on macOS / Linux
# .venv\Scripts\activate.bat        # on Windows PowerShell/cmd
```

### 3. Install dependencies

```bash
(.venv) $ pip install -r requirements.txt
```

### 4. Set your OpenAI credentials

The application relies on the OpenAI API. Make sure you have an API key, then export it as an environment variable so both the CLI and UI can read it:

```bash
(.venv) $ export OPENAI_API_KEY="sk-..."
```

---

## Running the Command-Line Interface (CLI)

The CLI translates **all** `.xlsx` files under a directory (recursively) and writes the translated versions to a sibling sub-folder named after the target language code (e.g. `fr`).

```bash
# Basic usage
(.venv) $ python cli_translate.py \
    --root ./my_spreadsheets \
    --source ja \
    --target en \
    --model gpt-4o
```

# Dry run (token & cost estimation only)
(.venv) $ python cli_translate.py \
    --root ./my_spreadsheets \
    --source ja \
    --target en \
    --estimate

Arguments:

| Flag | Description |
|------|-------------|
| `--root`   | Root directory to search for `.xlsx` files |
| `--source` | Source language code (ISO-639-1) |
| `--target` | Target language code (ISO-639-1) |
| `--model`  | `gpt-4o` (default) or `gpt-4o-mini` |
| `--estimate` | Perform a dry-run cost estimation without calling the OpenAI API |

After a **real** translation run (i.e., without `--estimate`), the CLI automatically writes an `actual_report_<src>_to_<tgt>_<timestamp>.csv` file in the root directory. This report contains per-file token usage and cost, plus overall totals.

---

## Running the Web UI (Streamlit)

Launch the Streamlit app to translate files through an interactive web interface:

```bash
(.venv) $ streamlit run app.py
```

Visit the URL printed in the console (typically http://localhost:8501) and upload the spreadsheet you wish to translate. The UI will estimate token usage, cost, and allow you to download the translated file once finished.

---

Happy translating! :rocket:

## Requirements
- Python 3.8+
- Set `OPENAI_API_KEY` in your environment
