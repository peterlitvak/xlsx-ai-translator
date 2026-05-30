"""Workbook text extraction and translation cost estimation services."""

from os import PathLike
from typing import BinaryIO, Iterable

import openpyxl

from services.model_pricing import MODEL_PRICING

OUTPUT_TOKEN_FACTORS = {
    ("en", "en"): 1.0,
    ("en", "ja"): 0.6,
    ("en", "de"): 1.1,
    ("en", "fr"): 1.1,
    ("en", "zh"): 0.7,
    ("ja", "en"): 1.7,
    ("ja", "ja"): 1.0,
    ("de", "en"): 0.9,
    ("fr", "en"): 0.9,
}

WorkbookSource = str | PathLike[str] | BinaryIO


def extract_translatable_texts(workbook_source: WorkbookSource) -> list[str]:
    """Extract text values from visible workbook sheets that should be translated."""
    workbook = openpyxl.load_workbook(workbook_source)
    texts: list[str] = []
    sheets = [
        sheet
        for sheet in workbook.worksheets
        if getattr(sheet, "sheet_state", "visible") == "visible"
    ]
    for sheet in sheets:
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str):
                    value = cell.value.strip()
                    if value and any(char.isalnum() for char in value):
                        texts.append(cell.value)
    return texts


def estimate_input_tokens(texts: Iterable[str], model_name: str) -> int:
    """Estimate input tokens for the provided strings using the selected model."""
    text_values: list[str] = [str(text) for text in texts]
    try:
        import tiktoken

        encoding = tiktoken.encoding_for_model(model_name)
        return sum(len(encoding.encode(text)) for text in text_values)
    except Exception:
        return sum(len(text.split()) for text in text_values)


def estimate_output_tokens(
    input_tokens: int, source_language: str, target_language: str
) -> int:
    """Estimate translated output tokens for the source and target language pair."""
    factor = OUTPUT_TOKEN_FACTORS.get((source_language, target_language), 1.0)
    return int(input_tokens * factor)


def estimate_translation_costs(
    input_tokens: int, output_tokens: int, model_name: str
) -> tuple[float, float, float]:
    """Estimate input, output, and total translation cost for token counts."""
    price_info = MODEL_PRICING.get(model_name, MODEL_PRICING["gpt-4o"])
    input_cost = input_tokens / 1000 * price_info["input"]
    output_cost = output_tokens / 1000 * price_info["output"]
    total_cost = input_cost + output_cost
    return input_cost, output_cost, total_cost


def estimate_xlsx_file(
    workbook_source: WorkbookSource,
    source_language: str,
    target_language: str,
    model_name: str,
) -> tuple[int, int, float]:
    """Estimate input tokens, output tokens, and total cost for one workbook."""
    texts = extract_translatable_texts(workbook_source)
    input_tokens = estimate_input_tokens(texts, model_name)
    output_tokens = estimate_output_tokens(
        input_tokens, source_language, target_language
    )
    _, _, total_cost = estimate_translation_costs(
        input_tokens, output_tokens, model_name
    )
    return input_tokens, output_tokens, total_cost
