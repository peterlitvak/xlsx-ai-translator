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

## Requirements
- Python 3.8+
- Set `OPENAI_API_KEY` in your environment
