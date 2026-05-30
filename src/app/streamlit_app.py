"""Streamlit entry point for XLSX and ZIP workbook translation."""

import logging
import zipfile

import streamlit as st

from enums.language import SupportedLanguage
from enums.translation_model import TranslationModel
from enums.upload_type import UploadType
from models.upload_summary import UploadSummary
from services.actual_usage_state import (
    clear_actual_usage_on_source_change,
    forget_uploaded_source,
    get_actual_usage_for_source,
    get_uploaded_source_key,
    store_actual_usage,
)
from services.download_artifacts import (
    cleanup_download_artifact,
    stage_download_artifact,
)
from services.translation_estimator import (
    estimate_translation_costs,
)
from services.translation_workflow import (
    TranslationError,
    ZipTranslationProgress,
    translate_single_xlsx,
    translate_xlsx_zip,
)
from services.upload_estimator import estimate_uploaded_file
from utils.file_names import is_xlsx_filename, is_zip_filename
from utils.zip_archives import UnsafeZipError

# Configure logging for Streamlit app
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

LANGUAGE_OPTIONS = list(SupportedLanguage)
MODEL_OPTIONS = list(TranslationModel)


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

with col1:
    uploaded_file = st.file_uploader("Choose an XLSX or ZIP file", type=["xlsx", "zip"])
    uploaded_source_key = None
    if uploaded_file is None:
        forget_uploaded_source(st.session_state)
    else:
        uploaded_source_key = get_uploaded_source_key(uploaded_file)
        clear_actual_usage_on_source_change(st.session_state, uploaded_source_key)

    selected_source_language = st.selectbox(
        "Source language",
        options=LANGUAGE_OPTIONS,
        index=LANGUAGE_OPTIONS.index(SupportedLanguage.JAPANESE),
    )
    source_language = selected_source_language.language_code
    selected_target_language = st.selectbox(
        "Target language",
        options=LANGUAGE_OPTIONS,
        index=LANGUAGE_OPTIONS.index(SupportedLanguage.ENGLISH),
    )
    target_language = selected_target_language.language_code
    selected_model = st.selectbox("Model", MODEL_OPTIONS, index=0)
    model_label = selected_model.display_name
    if uploaded_file is not None and st.button("Translate file", key="translate_btn"):
        logger.info(
            f"User triggered translation: {uploaded_file.name} to {target_language} using {model_label}"
        )
        cleanup_download_artifact(st.session_state)
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
                    model_name=selected_model.model_name,
                    max_workers=selected_model.thread_count,
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
                    model_name=selected_model.model_name,
                    max_workers=selected_model.thread_count,
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
            if uploaded_source_key is None:
                uploaded_source_key = get_uploaded_source_key(uploaded_file)
            download_artifact = stage_download_artifact(
                translation_result.data,
                translation_result.filename,
                st.session_state,
            )
            st.success("Translation complete! Download your file below.")
            downloaded = st.download_button(
                label=f"Download translated {translation_result.filename.rsplit('.', 1)[-1].upper()}",
                data=download_artifact.path.read_bytes(),
                file_name=translation_result.filename,
                mime=translation_result.mime_type,
                on_click=cleanup_download_artifact,
                args=(st.session_state,),
            )
            if downloaded:
                logger.info(f"User downloaded file: {translation_result.filename}")
            store_actual_usage(
                st.session_state,
                uploaded_source_key,
                translation_result.usage,
            )

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
                    selected_model.model_name,
                )
        except Exception as exc:
            st.error(f"Could not estimate token usage: {exc}")
            upload_summary = UploadSummary(
                upload_type=UploadType.UNKNOWN,
                workbook_count=None,
                estimated_input_tokens=0,
                estimated_output_tokens=0,
            )
        model_key = selected_model.model_name
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

- **Upload type:** {upload_summary.upload_type.display_name}
{workbook_count_line}- **File:** {uploaded_file.name}
- **Model:** {model_label}
- **Source language:** {selected_source_language.display_name}
- **Target language:** {selected_target_language.display_name}
- **Estimated input tokens:** {upload_summary.estimated_input_tokens}
- **Estimated output tokens:** {upload_summary.estimated_output_tokens}
- **Estimated cost:** ${total_cost:.2f}
    - _Input:_ ${input_cost:.2f}
    - _Output:_ ${output_cost:.2f}
"""
        st.info(info_md)
        if uploaded_source_key is not None:
            actual_usage = get_actual_usage_for_source(
                st.session_state,
                uploaded_source_key,
            )
            if actual_usage is not None:
                st.info(
                    "**Actual OpenAI usage:**\n\n"
                    f"- Input tokens: {actual_usage.input_tokens}\n"
                    f"- Output tokens: {actual_usage.output_tokens}\n"
                    f"- Actual cost: ${actual_usage.cost:.2f}"
                )
