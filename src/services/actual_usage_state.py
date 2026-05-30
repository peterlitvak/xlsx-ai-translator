"""Session-state helpers for Streamlit actual usage display."""

from collections.abc import MutableMapping
from typing import Any

from models.translation_usage import TranslationUsage

ACTUAL_USAGE_SOURCE_KEY = "actual_usage_source_key"
ACTUAL_INPUT_TOKENS_KEY = "actual_input_tokens"
ACTUAL_OUTPUT_TOKENS_KEY = "actual_output_tokens"
ACTUAL_COST_KEY = "actual_cost"
LEGACY_SHOW_ACTUAL_USAGE_KEY = "show_actual_usage"

ACTUAL_USAGE_KEYS = (
    ACTUAL_INPUT_TOKENS_KEY,
    ACTUAL_OUTPUT_TOKENS_KEY,
    ACTUAL_COST_KEY,
    LEGACY_SHOW_ACTUAL_USAGE_KEY,
)


def get_uploaded_source_key(uploaded_file: Any) -> str:
    """Return the upload identity Streamlit assigns to the current source file."""
    file_id = getattr(uploaded_file, "file_id", None)
    if isinstance(file_id, str) and file_id:
        return file_id

    name = getattr(uploaded_file, "name", "")
    size = getattr(uploaded_file, "size", "")
    file_type = getattr(uploaded_file, "type", "")
    return f"{name}:{size}:{file_type}"


def clear_actual_usage(session_state: MutableMapping[Any, Any]) -> None:
    """Remove stored actual usage values from the provided session state."""
    for key in ACTUAL_USAGE_KEYS:
        session_state.pop(key, None)


def clear_actual_usage_on_source_change(
    session_state: MutableMapping[Any, Any], uploaded_source_key: str
) -> None:
    """Clear actual usage when the user uploads a different source file."""
    previous_source_key = session_state.get(ACTUAL_USAGE_SOURCE_KEY)
    if previous_source_key != uploaded_source_key:
        clear_actual_usage(session_state)
        session_state[ACTUAL_USAGE_SOURCE_KEY] = uploaded_source_key


def forget_uploaded_source(session_state: MutableMapping[Any, Any]) -> None:
    """Forget the current upload identity without clearing stored usage values."""
    session_state.pop(ACTUAL_USAGE_SOURCE_KEY, None)


def store_actual_usage(
    session_state: MutableMapping[Any, Any],
    uploaded_source_key: str,
    usage: TranslationUsage,
) -> None:
    """Store actual usage for the translated source file."""
    session_state[ACTUAL_USAGE_SOURCE_KEY] = uploaded_source_key
    session_state[ACTUAL_INPUT_TOKENS_KEY] = usage.input_tokens
    session_state[ACTUAL_OUTPUT_TOKENS_KEY] = usage.output_tokens
    session_state[ACTUAL_COST_KEY] = usage.cost


def get_actual_usage_for_source(
    session_state: MutableMapping[Any, Any], uploaded_source_key: str
) -> TranslationUsage | None:
    """Return stored actual usage when it belongs to the current source file."""
    if session_state.get(ACTUAL_USAGE_SOURCE_KEY) != uploaded_source_key:
        return None

    input_tokens = session_state.get(ACTUAL_INPUT_TOKENS_KEY)
    output_tokens = session_state.get(ACTUAL_OUTPUT_TOKENS_KEY)
    cost = session_state.get(ACTUAL_COST_KEY)
    if input_tokens is None or output_tokens is None or cost is None:
        return None

    return TranslationUsage(
        input_tokens=int(input_tokens),
        output_tokens=int(output_tokens),
        cost=float(cost),
    )
