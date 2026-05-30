"""Streamlit entry point for XLSX and ZIP workbook translation."""

import logging
import tempfile
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional, TypedDict

import streamlit as st

from services.translation_estimator import (
    estimate_translation_costs,
    estimate_xlsx_file,
)
from services.translation_workflow import (
    TranslationError,
    ZipTranslationProgress,
    translate_single_xlsx,
    translate_xlsx_zip,
)
from utils.file_names import is_xlsx_filename, is_zip_filename
from utils.zip_archives import UnsafeZipError, find_xlsx_files, safe_extract_zip

# Configure logging for Streamlit app
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

LANGUAGES = {
    "French": "fr",
    "German": "de",
    "Spanish": "es",
    "Russian": "ru",
    "Chinese (Simplified)": "zh",
    "Chinese (Traditional)": "zh-tw",
    "Italian": "it",
    "Portuguese": "pt",
    "Japanese": "ja",
    "Korean": "ko",
    "Arabic": "ar",
    "Hindi": "hi",
    "Dutch": "nl",
    "Polish": "pl",
    "Turkish": "tr",
    "Czech": "cs",
    "Greek": "el",
    "Hebrew": "he",
    "Vietnamese": "vi",
    "Ukrainian": "uk",
    "Swedish": "sv",
    "Finnish": "fi",
    "Danish": "da",
    "Norwegian": "no",
    "Hungarian": "hu",
    "Romanian": "ro",
    "Bulgarian": "bg",
    "Indonesian": "id",
    "Thai": "th",
    "Malay": "ms",
    "English": "en",
}


class ModelOption(TypedDict):
    """Streamlit-selectable model configuration."""

    model: str
    threads: int


@dataclass(frozen=True)
class UploadSummary:
    """Estimated usage and detected type for an uploaded file."""

    upload_type: str
    workbook_count: Optional[int]
    estimated_input_tokens: int
    estimated_output_tokens: int


MODEL_OPTIONS: dict[str, ModelOption] = {
    "GPT-4o": {"model": "gpt-4o", "threads": 11},
    "GPT-4o-mini": {"model": "gpt-4o-mini", "threads": 11},
}


def format_func(lang_name: str) -> str:
    """Format language select options with display name and code."""
    return f"{lang_name} ({LANGUAGES[lang_name]})"


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
            upload_type="XLSX workbook",
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
        upload_type="ZIP archive",
        workbook_count=len(workbook_paths),
        estimated_input_tokens=input_tokens,
        estimated_output_tokens=output_tokens,
    )


st.set_page_config(page_title="XLSX LLM Translator", layout="wide")
st.title("XLSX LLM Translator")
st.markdown(
    "Upload an .xlsx file or a .zip archive and translate workbook text using GPT-4o or GPT-4o-mini"
)
st.markdown(
    """
    <style>
        /* Streamlit ≤1.34 main content wrapper */
        .main .block-container {
            max-width: 80vw;            /* 80 % of viewport width           */
            margin-left: auto;          /* center it                        */
            margin-right: auto;
            padding-left: 2rem;         /* optional breathing room          */
            padding-right: 2rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

col1, col2 = st.columns([3, 1], gap="large")


lang_names = list(LANGUAGES.keys())

with col1:
    uploaded_file = st.file_uploader("Choose an XLSX or ZIP file", type=["xlsx", "zip"])
    selected_source_lang_name = st.selectbox(
        "Source language",
        options=lang_names,
        index=lang_names.index("Japanese"),
        format_func=format_func,
    )
    source_language = LANGUAGES[selected_source_lang_name]
    selected_lang_name = st.selectbox(
        "Target language",
        options=lang_names,
        index=lang_names.index("English"),
        format_func=format_func,
    )
    target_language = LANGUAGES[selected_lang_name]
    selected_model = st.selectbox("Model", list(MODEL_OPTIONS.keys()), index=0)
    model_info = MODEL_OPTIONS[selected_model]
    model_label = selected_model
    if uploaded_file is not None and st.button("Translate file", key="translate_btn"):
        logger.info(
            f"User triggered translation: {uploaded_file.name} to {target_language} using {model_label}"
        )
        uploaded_bytes = uploaded_file.getvalue()
        translation_result = None

        try:
            if is_xlsx_filename(uploaded_file.name):
                progress_bar = st.progress(0, text="Starting translation...")

                def update_progress(progress: float) -> None:
                    progress_bar.progress(
                        progress,
                        text=f"{int(progress * 100)}% complete",
                    )

                translation_result = translate_single_xlsx(
                    uploaded_bytes=uploaded_bytes,
                    original_filename=uploaded_file.name,
                    target_language=target_language,
                    model_name=model_info["model"],
                    max_workers=model_info["threads"],
                    rpm_limit=2555,
                    progress_callback=update_progress,
                )
            elif is_zip_filename(uploaded_file.name):
                overall_progress_bar = st.progress(
                    0,
                    text="Starting archive translation...",
                )
                workbook_progress_bar = st.progress(
                    0,
                    text="Waiting for workbook translation...",
                )

                def update_zip_progress(progress: ZipTranslationProgress) -> None:
                    overall_progress_bar.progress(
                        progress.overall_progress,
                        text=(
                            f"Workbook {progress.workbook_index} of "
                            f"{progress.workbook_count}: {progress.relative_path}"
                        ),
                    )
                    workbook_progress_bar.progress(
                        progress.workbook_progress,
                        text=(
                            f"{int(progress.workbook_progress * 100)}% complete: "
                            f"{progress.relative_path}"
                        ),
                    )

                translation_result = translate_xlsx_zip(
                    uploaded_bytes=uploaded_bytes,
                    original_filename=uploaded_file.name,
                    target_language=target_language,
                    model_name=model_info["model"],
                    max_workers=model_info["threads"],
                    rpm_limit=2555,
                    progress_callback=update_zip_progress,
                )
            else:
                st.error("Unsupported file type. Upload an .xlsx or .zip file.")
        except (TranslationError, UnsafeZipError) as exc:
            st.error(str(exc))
            logger.error(str(exc))
        except zipfile.BadZipFile:
            st.error("Could not read zip archive. Upload a valid .zip file.")
            logger.exception("Could not read uploaded zip archive.")
        except Exception as exc:
            st.error(f"Translation failed: {exc}")
            logger.exception("Unexpected translation failure.")

        if translation_result is not None:
            st.success("Translation complete! Download your file below.")
            st.download_button(
                label=f"Download translated {translation_result.filename.rsplit('.', 1)[-1].upper()}",
                data=translation_result.data,
                file_name=translation_result.filename,
                mime=translation_result.mime_type,
            )
            logger.info(f"User downloaded file: {translation_result.filename}")
            # Show actual usage/cost in info panel
            st.session_state["show_actual_usage"] = True
            st.session_state["actual_input_tokens"] = (
                translation_result.usage.input_tokens
            )
            st.session_state["actual_output_tokens"] = (
                translation_result.usage.output_tokens
            )
            st.session_state["actual_cost"] = translation_result.usage.cost

with col2:
    if uploaded_file is not None:
        try:
            uploaded_bytes = uploaded_file.getvalue()
            with st.spinner("Estimating tokens..."):
                upload_summary = estimate_uploaded_file(
                    uploaded_bytes,
                    uploaded_file.name,
                    source_language,
                    target_language,
                    model_info["model"],
                )
        except Exception as exc:
            st.error(f"Could not estimate token usage: {exc}")
            upload_summary = UploadSummary(
                upload_type="Unknown",
                workbook_count=None,
                estimated_input_tokens=0,
                estimated_output_tokens=0,
            )
        model_key = model_info["model"]
        input_cost, output_cost, total_cost = estimate_translation_costs(
            upload_summary.estimated_input_tokens,
            upload_summary.estimated_output_tokens,
            model_key,
        )
        workbook_count_line = (
            f"- **Workbooks detected:** {upload_summary.workbook_count}\n"
            if upload_summary.workbook_count is not None
            else ""
        )
        info_md = f"""
**Translation Summary**

- **Upload type:** {upload_summary.upload_type}
{workbook_count_line}- **File:** {uploaded_file.name}
- **Model:** {model_label}
- **Source language:** {selected_source_lang_name}
- **Target language:** {selected_lang_name}
- **Estimated input tokens:** {upload_summary.estimated_input_tokens}
- **Estimated output tokens:** {upload_summary.estimated_output_tokens}
- **Estimated cost:** ${total_cost:.2f}
    - _Input:_ ${input_cost:.2f}
    - _Output:_ ${output_cost:.2f}
"""
        st.info(info_md)
        # Show actual usage/cost if available
        if st.session_state.get("show_actual_usage"):
            actual_input = st.session_state.get("actual_input_tokens")
            actual_output = st.session_state.get("actual_output_tokens")
            actual_cost = st.session_state.get("actual_cost")
            if (
                actual_input is not None
                and actual_output is not None
                and actual_cost is not None
            ):
                st.info(
                    f"**Actual OpenAI usage:**\n\n- Input tokens: {actual_input}\n- Output tokens: {actual_output}\n- Actual cost: ${actual_cost:.2f}"
                )
            # Reset after showing
            st.session_state["show_actual_usage"] = False
