"""Translation orchestration services for workbook and zip upload workflows."""

import tempfile
from pathlib import Path
from typing import Callable, Iterable, Optional, Protocol

from models.single_xlsx_translation_result import SingleXLSXTranslationResult
from models.translation_usage import TranslationUsage
from models.zip_translation_progress import ZipTranslationProgress
from models.zip_xlsx_translation_result import ZipXLSXTranslationResult
from services.xlsx_translator import XLSXTranslator
from utils.file_names import translated_xlsx_name, translated_zip_name
from utils.zip_archives import (
    create_zip_from_directory,
    find_xlsx_files,
    safe_extract_zip,
)

ProgressCallback = Callable[[float], None]
XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
ZIP_MIME_TYPE = "application/zip"


class TranslationError(RuntimeError):
    """Raised when an uploaded workbook cannot be translated."""


class XLSXTranslatorLike(Protocol):
    """Protocol for translator instances used by upload orchestration services."""

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


ZipProgressCallback = Callable[[ZipTranslationProgress], None]


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
        temp_path = Path(temp_dir)
        input_path = temp_path / "input.xlsx"
        output_path = temp_path / "output.xlsx"

        input_path.write_bytes(uploaded_bytes)

        translator = translator_factory(
            input_path=str(input_path),
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

        result_path = translator.get_result(str(output_path))
        if result_path is None:
            raise TranslationError("Translation failed. See logs for details.")

        translated_data = Path(result_path).read_bytes()

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

        create_zip_from_directory(output_dir, output_zip_path)
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
