import os
import tempfile
import zipfile
from dataclasses import dataclass
from os import PathLike
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Callable, Iterable, List, Optional, Protocol, Tuple, Union

import openpyxl

from pricing import MODEL_PRICING
from translator import XLSXTranslator

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

WorkbookSource = Union[str, PathLike, BinaryIO]
ProgressCallback = Callable[[float], None]

XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
ZIP_MIME_TYPE = "application/zip"


class TranslationError(RuntimeError):
    """Raised when an uploaded workbook cannot be translated."""


class UnsafeZipError(ValueError):
    """Raised when a zip archive contains an unsafe member path."""


class XLSXTranslatorLike(Protocol):
    """Protocol for translator instances used by UI orchestration helpers."""

    error: Optional[str]
    actual_input_tokens: int
    actual_output_tokens: int
    actual_cost: float

    def translate_with_progress(self) -> Iterable[float]:
        """Translate the workbook and yield progress values from 0 to 1."""
        ...

    def get_result(self, output_path: str) -> Optional[str]:
        """Write the translated workbook and return its path when successful."""
        ...


TranslatorFactory = Callable[..., XLSXTranslatorLike]


@dataclass(frozen=True)
class TranslationUsage:
    """Actual token and cost usage reported by a translation run."""

    input_tokens: int
    output_tokens: int
    cost: float


@dataclass(frozen=True)
class SingleXLSXTranslationResult:
    """Downloadable result for one translated workbook."""

    data: bytes
    filename: str
    mime_type: str
    usage: TranslationUsage


@dataclass(frozen=True)
class ZipTranslationProgress:
    """Progress update for one workbook inside a zip translation."""

    relative_path: str
    workbook_index: int
    workbook_count: int
    workbook_progress: float
    overall_progress: float


@dataclass(frozen=True)
class ZipXLSXTranslationResult:
    """Downloadable result for a translated zip archive."""

    data: bytes
    filename: str
    mime_type: str
    usage: TranslationUsage
    workbook_count: int


ZipProgressCallback = Callable[[ZipTranslationProgress], None]


def extract_translatable_texts(workbook_source: WorkbookSource) -> List[str]:
    """Extract text values from visible workbook sheets that should be translated."""
    workbook = openpyxl.load_workbook(workbook_source)
    texts: List[str] = []
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
    text_values: List[str] = [str(text) for text in texts]
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
) -> Tuple[float, float, float]:
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
) -> Tuple[int, int, float]:
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


def translated_xlsx_name(filename: str, target_language: str) -> str:
    """Build a translated workbook filename with the target language suffix."""
    base_name = os.path.basename(filename)
    stem, _ = os.path.splitext(base_name)
    if not stem:
        stem = "translated"
    return f"{stem}_{target_language}.xlsx"


def translated_zip_name(filename: str, target_language: str) -> str:
    """Build a translated archive filename with the target language suffix."""
    base_name = os.path.basename(filename)
    stem, _ = os.path.splitext(base_name)
    if not stem:
        stem = "translated"
    return f"{stem}_{target_language}.zip"


def is_xlsx_filename(filename: str) -> bool:
    """Return true when filename points to a supported workbook."""
    base_name = os.path.basename(filename)
    lower_name = base_name.lower()
    if base_name.startswith(("~$", "._")):
        return False
    return lower_name.endswith(".xlsx")


def is_zip_filename(filename: str) -> bool:
    """Return true when filename points to a zip archive."""
    base_name = os.path.basename(filename)
    return base_name.lower().endswith(".zip")


def safe_extract_zip(zip_path: str, extract_dir: str) -> None:
    """Extract a zip archive only if all members stay inside extract_dir."""
    extract_root = Path(extract_dir).resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            _validate_zip_member_path(member.filename, extract_root)
        archive.extractall(extract_root)


def _validate_zip_member_path(member_name: str, extract_root: Path) -> None:
    """Validate a zip member path against traversal and absolute-path attacks."""
    normalized_name = member_name.replace("\\", "/")
    member_path = PurePosixPath(normalized_name)
    parts = member_path.parts

    if not parts or member_path.is_absolute():
        raise UnsafeZipError(f"Unsafe zip member path: {member_name}")

    if any(part == ".." for part in parts):
        raise UnsafeZipError(f"Unsafe zip member path: {member_name}")

    if parts[0].endswith(":"):
        raise UnsafeZipError(f"Unsafe zip member path: {member_name}")

    resolved_path = (extract_root / Path(*parts)).resolve()
    if resolved_path != extract_root and extract_root not in resolved_path.parents:
        raise UnsafeZipError(f"Unsafe zip member path: {member_name}")


def find_xlsx_files(root_dir: str) -> List[str]:
    """Recursively discover workbook files below root_dir."""
    root_path = Path(root_dir)
    return sorted(
        str(path)
        for path in root_path.rglob("*")
        if path.is_file() and is_xlsx_filename(path.name)
    )


def translate_single_xlsx(
    uploaded_bytes: bytes,
    original_filename: str,
    target_language: str,
    model_name: str,
    max_workers: int,
    rpm_limit: int = 2555,
    progress_callback: Optional[ProgressCallback] = None,
    translator_factory: TranslatorFactory = XLSXTranslator,
) -> SingleXLSXTranslationResult:
    """Translate one uploaded workbook and return a ready-to-download result."""
    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, "input.xlsx")
        output_path = os.path.join(temp_dir, "output.xlsx")

        with open(input_path, "wb") as input_file:
            input_file.write(uploaded_bytes)

        translator = translator_factory(
            input_path=input_path,
            target_language=target_language,
            model_name=model_name,
            max_workers=max_workers,
            rpm_limit=rpm_limit,
        )

        for progress in translator.translate_with_progress():
            if progress_callback is not None:
                progress_callback(progress)

        if translator.error:
            raise TranslationError(f"Translation failed: {translator.error}")

        result_path = translator.get_result(output_path)
        if result_path is None:
            raise TranslationError("Translation failed. See logs for details.")

        with open(result_path, "rb") as output_file:
            translated_data = output_file.read()

    return SingleXLSXTranslationResult(
        data=translated_data,
        filename=translated_xlsx_name(original_filename, target_language),
        mime_type=XLSX_MIME_TYPE,
        usage=TranslationUsage(
            input_tokens=translator.actual_input_tokens,
            output_tokens=translator.actual_output_tokens,
            cost=translator.actual_cost,
        ),
    )


def translate_xlsx_zip(
    uploaded_bytes: bytes,
    original_filename: str,
    target_language: str,
    model_name: str,
    max_workers: int,
    rpm_limit: int = 2555,
    progress_callback: Optional[ZipProgressCallback] = None,
    translator_factory: TranslatorFactory = XLSXTranslator,
) -> ZipXLSXTranslationResult:
    """Translate all workbooks in an uploaded zip and return a translated archive."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_zip_path = temp_path / "input.zip"
        extract_dir = temp_path / "extract"
        output_dir = temp_path / "output"
        output_zip_path = temp_path / "translated.zip"

        input_zip_path.write_bytes(uploaded_bytes)
        extract_dir.mkdir()
        output_dir.mkdir()

        safe_extract_zip(str(input_zip_path), str(extract_dir))
        workbook_paths = [Path(path) for path in find_xlsx_files(str(extract_dir))]
        if not workbook_paths:
            raise TranslationError("No .xlsx workbooks found in the zip archive.")

        input_tokens = 0
        output_tokens = 0
        actual_cost = 0.0
        workbook_count = len(workbook_paths)

        for workbook_index, workbook_path in enumerate(workbook_paths, start=1):
            relative_path = workbook_path.relative_to(extract_dir)
            relative_label = relative_path.as_posix()
            output_relative_path = relative_path.with_name(
                translated_xlsx_name(relative_path.name, target_language)
            )
            output_path = output_dir / output_relative_path
            output_path.parent.mkdir(parents=True, exist_ok=True)

            translator = translator_factory(
                input_path=str(workbook_path),
                target_language=target_language,
                model_name=model_name,
                max_workers=max_workers,
                rpm_limit=rpm_limit,
            )

            last_progress: Optional[float] = None
            _emit_zip_progress(
                progress_callback,
                relative_label,
                workbook_index,
                workbook_count,
                0.0,
            )
            for progress in translator.translate_with_progress():
                normalized_progress = _normalize_progress(progress)
                last_progress = normalized_progress
                _emit_zip_progress(
                    progress_callback,
                    relative_label,
                    workbook_index,
                    workbook_count,
                    normalized_progress,
                )

            if translator.error:
                raise TranslationError(
                    f"Translation failed for {relative_label}: {translator.error}"
                )

            result_path = translator.get_result(str(output_path))
            if result_path is None:
                raise TranslationError(
                    f"Translation failed for {relative_label}. See logs for details."
                )

            if Path(result_path) != output_path:
                output_path.write_bytes(Path(result_path).read_bytes())

            if last_progress != 1.0:
                _emit_zip_progress(
                    progress_callback,
                    relative_label,
                    workbook_index,
                    workbook_count,
                    1.0,
                )

            input_tokens += translator.actual_input_tokens
            output_tokens += translator.actual_output_tokens
            actual_cost += translator.actual_cost

        _create_zip_from_directory(output_dir, output_zip_path)
        translated_data = output_zip_path.read_bytes()

    return ZipXLSXTranslationResult(
        data=translated_data,
        filename=translated_zip_name(original_filename, target_language),
        mime_type=ZIP_MIME_TYPE,
        usage=TranslationUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=actual_cost,
        ),
        workbook_count=workbook_count,
    )


def _emit_zip_progress(
    progress_callback: Optional[ZipProgressCallback],
    relative_path: str,
    workbook_index: int,
    workbook_count: int,
    workbook_progress: float,
) -> None:
    """Send a zip translation progress update when a callback is available."""
    if progress_callback is None:
        return

    progress_callback(
        ZipTranslationProgress(
            relative_path=relative_path,
            workbook_index=workbook_index,
            workbook_count=workbook_count,
            workbook_progress=workbook_progress,
            overall_progress=(workbook_index - 1 + workbook_progress) / workbook_count,
        )
    )


def _normalize_progress(progress: float) -> float:
    """Clamp a translator progress value to the expected zero-to-one range."""
    return min(max(progress, 0.0), 1.0)


def _create_zip_from_directory(source_dir: Path, zip_path: Path) -> None:
    """Create a zip archive from all files below source_dir."""
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(source_dir.rglob("*")):
            if file_path.is_file():
                archive.write(
                    file_path,
                    arcname=file_path.relative_to(source_dir).as_posix(),
                )
