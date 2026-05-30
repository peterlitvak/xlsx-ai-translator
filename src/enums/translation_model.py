"""Supported OpenAI model options for translation workflows."""

from enum import auto

from enums.auto_name_enum import AutoNameEnum


class TranslationModel(AutoNameEnum):
    """LLM models exposed by the Streamlit UI."""

    GPT_4O = auto()
    GPT_4O_MINI = auto()

    @property
    def model_name(self) -> str:
        """Return the OpenAI model identifier passed to services."""
        return TRANSLATION_MODEL_NAMES[self]

    @property
    def display_name(self) -> str:
        """Return the human-readable model label."""
        return TRANSLATION_MODEL_DISPLAY_NAMES[self]

    @property
    def thread_count(self) -> int:
        """Return the default number of translation worker threads."""
        return TRANSLATION_MODEL_THREAD_COUNTS[self]

    def __str__(self) -> str:
        """Return the display name for select controls."""
        return self.display_name


TRANSLATION_MODEL_DISPLAY_NAMES: dict[TranslationModel, str] = {
    TranslationModel.GPT_4O: "GPT-4o",
    TranslationModel.GPT_4O_MINI: "GPT-4o-mini",
}
TRANSLATION_MODEL_NAMES: dict[TranslationModel, str] = {
    TranslationModel.GPT_4O: "gpt-4o",
    TranslationModel.GPT_4O_MINI: "gpt-4o-mini",
}
TRANSLATION_MODEL_THREAD_COUNTS: dict[TranslationModel, int] = {
    TranslationModel.GPT_4O: 11,
    TranslationModel.GPT_4O_MINI: 11,
}
