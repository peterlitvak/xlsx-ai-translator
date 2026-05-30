# XLSX LLM Translator

A Python service and Streamlit UI that translate Excel `.xlsx` workbooks using LangChain and OpenAI models. The CLI
translates one workbook or every workbook under a directory tree. The web UI accepts either one `.xlsx` file or a `.zip`
archive containing workbooks.

## Features

- Translate workbook text using GPT-4o or GPT-4o mini
- Upload a single `.xlsx` file or a `.zip` archive through the Streamlit UI
- Preserve workbook paths inside translated zip downloads
- Estimate token usage and cost before translation, then show actual OpenAI usage after translation
- Translate one CLI source file or every `.xlsx` file under a directory
- Simple function: `translate_xlsx_file(input_path, output_path, target_language)`

## Usage Example

```python
from services.xlsx_translator import translate_xlsx_file

translate_xlsx_file("input.xlsx", "output.xlsx", target_language="fr")
```

## Installation

### 1. Clone the repository

```bash
$ git clone https://github.com/your-org/xlsx-llm-translator.git
$ cd xlsx-llm-translator
```

### 2. Install uv

```bash
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Sync dependencies

```bash
$ uv sync
```

### 4. Set your OpenAI credentials

The application relies on the OpenAI API. Make sure you have an API key, then export it as an environment variable so
both the CLI and UI can read it:

```bash
$ export OPENAI_API_KEY="sk-..."
```

---

## Running the Command-Line Interface (CLI)

The CLI accepts `--root` as either one `.xlsx` file or a directory. Directory input is searched recursively. Real
translation runs write translated workbooks into a target-language subdirectory next to each source workbook:
`reports/q1.xlsx` becomes `reports/en/q1_en.xlsx`.

```bash
# Translate one workbook
$ uv run xlsx-translate --root ./resources/test_fixtures/sample.xlsx --source ja --target en --model gpt-4o

# Translate every workbook under a directory
$ uv run xlsx-translate --root ./my_spreadsheets --source ja --target en --model gpt-4o
```

Dry run token and cost estimation:

```bash
$ uv run xlsx-translate --root ./my_spreadsheets --source ja --target en --estimate
```

Arguments:

| Flag         | Description                                                      |
|--------------|------------------------------------------------------------------|
| `--root`     | One `.xlsx` file or a root directory to search recursively       |
| `--source`   | Source language code (ISO-639-1)                                 |
| `--target`   | Target language code (ISO-639-1)                                 |
| `--model`    | `gpt-4o` (default) or `gpt-4o-mini`                              |
| `--estimate` | Perform a dry-run cost estimation without calling the OpenAI API |

Dry runs write `estimate_report_<src>_to_<tgt>_<timestamp>.csv`. Real translation runs write
`actual_report_<src>_to_<tgt>_<timestamp>.csv`. Reports are written to the source file's parent directory for single-file
runs, or to the root directory for directory runs. Each report contains per-file token usage and cost plus overall totals.

---

## Running the Web UI (Streamlit)

Launch the Streamlit app to translate files through an interactive web interface:

```bash
$ uv run streamlit run src/app/streamlit_app.py
```

Visit the URL printed in the console (typically http://localhost:8501) and upload the spreadsheet you wish to translate.
For a local smoke test, use `resources/test_fixtures/sample.xlsx` or `resources/test_fixtures/sample.zip`.

The file picker accepts:

- `.xlsx`: translates one workbook and downloads `<original_base>_<target>.xlsx`.
- `.zip`: safely extracts the archive, translates every `.xlsx` workbook found recursively, and downloads
  `<original_zip_base>_<target>.zip`.

For zip uploads, translated workbook paths are preserved inside the archive and each workbook basename receives the
target-language suffix. For example, `nested/report.xlsx` becomes `nested/report_en.xlsx`. Non-workbook files are skipped
in the translated download.

The summary panel shows the upload type, workbook count for zip archives, selected model, languages, estimated tokens,
and estimated cost. After a successful translation, it also shows actual OpenAI input tokens, output tokens, and cost.
Zip translations show both overall archive progress and current workbook progress.

The UI rejects unsupported file types, invalid zip files, unsafe zip member paths, and zip archives that do not contain
any `.xlsx` workbooks.

---

## Running with Docker

Build the Streamlit service image:

```bash
$ docker build -t xlsx-llm-translator:local .
```

Run a foreground smoke test on the Docker host:

```bash
$ mkdir -p .local/docker-work
$ chmod 1777 .local/docker-work
$ docker run --rm \
    --name xlsx-llm-translator \
    --cpus 1 \
    --memory 2g \
    --env OPENAI_API_KEY="$OPENAI_API_KEY" \
    --volume "$PWD/.local/docker-work:/work" \
    --publish 8501:8501 \
    xlsx-llm-translator:local
```

Run it as a long-lived LAN service:

```bash
$ mkdir -p .local/docker-work
$ chmod 1777 .local/docker-work
$ docker run -d \
    --name xlsx-llm-translator \
    --restart unless-stopped \
    --cpus 1 \
    --memory 2g \
    --env-file .env \
    --volume "$PWD/.local/docker-work:/work" \
    --publish 8501:8501 \
    xlsx-llm-translator:local
```

The UI is available from trusted LAN machines at:

```text
http://<docker-host-lan-ip>:8501
```

To deploy to the configured remote LAN Docker host, put these keys in the local `.env` file:

```bash
OPENAI_API_KEY=sk-...
DEPLOY_HOST_IP=...
DEPLOY_HOST_USER=...
DEPLOY_HOST_PWD=...
```

Then run:

```bash
$ ./scripts/deploy_docker_remote.sh
```

The deploy script builds the image, saves it under `.local/`, copies it to the remote host over SSH, writes a remote
runtime env file containing only `OPENAI_API_KEY`, loads the image, replaces the container, and checks the Streamlit
health endpoint. If `DEPLOY_HOST_PWD` is set, the script uses `sshpass -e` when available, falls back to `expect` when
available, and otherwise uses normal SSH key or interactive authentication. It also creates a host work directory,
mounts it at `/work`, and starts the container with `--cpus 1 --memory 2g` by default.

Useful deployment overrides:

```bash
$ INSTALL_DOCKER_IF_MISSING=true ./scripts/deploy_docker_remote.sh
$ DOCKER_CPUS=2 DOCKER_MEMORY=4g ./scripts/deploy_docker_remote.sh
$ REMOTE_WORK_DIR=/srv/xlsx-llm-translator/work ./scripts/deploy_docker_remote.sh
```

Automatic Docker installation is opt-in. Linux hosts use Docker's convenience script and require passwordless `sudo`.
macOS hosts use Docker Desktop's command-line installer from Docker's official DMG and require an admin password through
the configured SSH password flow.

Streamlit is configured for uploads up to 500 MB. Uploaded files and generated download artifacts use the mounted work
directory; staged download artifacts are removed when the download button is clicked.

This app does not include built-in authentication. Publish it only on a trusted in-house network, or place it behind an
authenticated reverse proxy before exposing it more broadly.

---

## Running Tests

The integration suite uses real OpenAI calls, and the UI flow tests use Playwright with Chromium.

```bash
$ uv run playwright install chromium
$ uv run python -m unittest discover -s tests
$ uv run pyright
```

## Requirements

- Python 3.11+
- uv
- Set `OPENAI_API_KEY` in your environment
