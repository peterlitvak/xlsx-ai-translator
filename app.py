import logging
import os
import tempfile

import openpyxl
import streamlit as st

from translator import XLSXTranslator

# Configure logging for Streamlit app
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler()]
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
    "English": "en"
}

MODEL_OPTIONS = {
    "GPT-4o": {"model": "gpt-4o", "threads": 11},
    "GPT-4o-mini": {"model": "gpt-4o-mini", "threads": 11}
}

# Pricing info per model (July 2025)
MODEL_PRICING = {
    "gpt-4o": {"input": 0.005, "output": 0.015},  # $ per 1K tokens
    "gpt-4o-mini": {"input": 0.0005, "output": 0.0015}
}

# Output token estimation factors by (source, target) language pair
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
    # add more as needed
}

st.set_page_config(page_title="XLSX LLM Translator", layout="wide")
st.title("XLSX LLM Translator")
st.markdown("Upload an .xlsx file and translate all its text using GPT-4o or GPT-4o-mini")
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


def format_func(lang_name):
    return f"{lang_name} ({LANGUAGES[lang_name]})"


lang_names = list(LANGUAGES.keys())

with col1:
    uploaded_file = st.file_uploader("Choose an XLSX file", type=["xlsx"])
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
    if uploaded_file is not None and st.button("Translate XLSX", key="translate_btn"):
        logger.info(f"User triggered translation: {uploaded_file.name} to {target_language} using {model_label}")
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        input_path = temp_input.name
        temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        output_path = temp_output.name
        with open(input_path, "wb") as f:
            f.write(uploaded_file.read())
        translator = XLSXTranslator(
            input_path=input_path,
            target_language=target_language,
            model_name=model_info["model"],
            max_workers=model_info["threads"],
            rpm_limit=2555
        )
        progress_bar = st.progress(0, text="Starting translation...")
        try:
            for prog in translator.translate_with_progress():
                progress_bar.progress(prog, text=f"{int(prog * 100)}% complete")
            if translator.error:
                st.error(f"Translation failed: {translator.error}")
                logger.error(f"Translation failed: {translator.error}")
            else:
                result_path = translator.get_result(output_path)
                if result_path:
                    # Compose download filename: {original}_{lang}.xlsx
                    import os

                    orig_base = os.path.splitext(os.path.basename(uploaded_file.name))[0]
                    lang_code = target_language
                    download_filename = f"{orig_base}_{lang_code}.xlsx"
                    with open(result_path, "rb") as f:
                        st.success("Translation complete! Download your file below.")
                        st.download_button(
                            label="Download translated XLSX",
                            data=f,
                            file_name=download_filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        logger.info(f"User downloaded file: {download_filename}")
                    # Show actual usage/cost in info panel
                    st.session_state["show_actual_usage"] = True
                    st.session_state["actual_input_tokens"] = getattr(translator, "actual_input_tokens", None)
                    st.session_state["actual_output_tokens"] = getattr(translator, "actual_output_tokens", None)
                    st.session_state["actual_cost"] = getattr(translator, "actual_cost", None)
                else:
                    st.error("Translation failed. See logs for details.")
        finally:
            try:
                os.remove(input_path)
            except Exception:
                pass
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
            except Exception:
                pass

with col2:
    if uploaded_file is not None:
        try:
            import tiktoken

            enc = tiktoken.encoding_for_model(model_info["model"])
            texts = []
            wb = openpyxl.load_workbook(uploaded_file)
            sheets = [sheet for sheet in wb.worksheets if getattr(sheet, 'sheet_state', 'visible') == 'visible']
            progress = st.progress(0, text="Estimating tokens...")
            for idx, sheet in enumerate(sheets):
                for row in sheet.iter_rows():
                    for cell in row:
                        if cell.value and isinstance(cell.value, str):
                            val = cell.value.strip()
                            if val and any(char.isalnum() for char in val):
                                texts.append(cell.value)
                progress.progress((idx + 1) / len(sheets), text=f"Estimating tokens... ({idx + 1}/{len(sheets)})")
            total_tokens = sum(len(enc.encode(str(text))) for text in texts)
            progress.empty()
        except Exception:
            total_tokens = sum(len(str(text).split()) for text in texts)
        model_key = model_info["model"]
        price_info = MODEL_PRICING.get(model_key, MODEL_PRICING["gpt-4o"])
        factor = OUTPUT_TOKEN_FACTORS.get((source_language, target_language), 1.0)
        est_output_tokens = int(total_tokens * factor)
        input_cost = total_tokens / 1000 * price_info["input"]
        output_cost = est_output_tokens / 1000 * price_info["output"]
        total_cost = input_cost + output_cost
        info_md = f"""
**Translation Summary**

- **Model:** {model_label}
- **Source language:** {selected_source_lang_name}
- **Target language:** {selected_lang_name}
- **Estimated input tokens:** {total_tokens}
- **Estimated output tokens:** {est_output_tokens}
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
            if actual_input is not None and actual_output is not None and actual_cost is not None:
                st.info(
                    f"**Actual OpenAI usage:**\n\n- Input tokens: {actual_input}\n- Output tokens: {actual_output}\n- Actual cost: ${actual_cost:.2f}")
            # Reset after showing
            st.session_state["show_actual_usage"] = False
