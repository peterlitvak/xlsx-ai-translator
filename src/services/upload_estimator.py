"""Upload estimation services for XLSX and ZIP Streamlit uploads."""

import tempfile
from io import BytesIO
from pathlib import Path

from enums.upload_type import UploadType
from models.upload_summary import UploadSummary
from services.translation_estimator import estimate_xlsx_file
from services.translation_workflow import TranslationError
from utils.file_names import is_xlsx_filename, is_zip_filename
from utils.zip_archives import find_xlsx_files, safe_extract_zip


def estimate_uploaded_file(
    uploaded_bytes: bytes,
    filename: str,
    source_language: str,
    target_language: str,
    model_name: str,
) -> UploadSummary:
    """Estimate aggregate translation usage for an XLSX or ZIP upload."""
    if is_xlsx_filename(filename):
        input_tokens, output_tokens, _ = estimate_xlsx_file(
            BytesIO(uploaded_bytes),
            source_language,
            target_language,
            model_name,
        )
        return UploadSummary(
            upload_type=UploadType.XLSX_WORKBOOK,
            workbook_count=None,
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
        )

    if is_zip_filename(filename):
        return estimate_zip_upload(
            uploaded_bytes,
            source_language,
            target_language,
            model_name,
        )

    raise TranslationError("Unsupported file type. Upload an .xlsx or .zip file.")


def estimate_zip_upload(
    uploaded_bytes: bytes,
    source_language: str,
    target_language: str,
    model_name: str,
) -> UploadSummary:
    """Estimate aggregate translation usage for workbooks inside a zip archive."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_zip_path = temp_path / "input.zip"
        extract_dir = temp_path / "extract"

        input_zip_path.write_bytes(uploaded_bytes)
        extract_dir.mkdir()
        safe_extract_zip(str(input_zip_path), str(extract_dir))

        workbook_paths = find_xlsx_files(str(extract_dir))
        if not workbook_paths:
            raise TranslationError("No .xlsx workbooks found in the zip archive.")

        input_tokens = 0
        output_tokens = 0
        for workbook_path in workbook_paths:
            workbook_input_tokens, workbook_output_tokens, _ = estimate_xlsx_file(
                workbook_path,
                source_language,
                target_language,
                model_name,
            )
            input_tokens += workbook_input_tokens
            output_tokens += workbook_output_tokens

    return UploadSummary(
        upload_type=UploadType.ZIP_ARCHIVE,
        workbook_count=len(workbook_paths),
        estimated_input_tokens=input_tokens,
        estimated_output_tokens=output_tokens,
    )
