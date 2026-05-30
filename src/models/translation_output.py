"""Structured LLM translation output models."""

from pydantic import BaseModel, ConfigDict


class TranslationOutput(BaseModel):
    """Structured response containing translated text values."""

    model_config = ConfigDict(frozen=True)

    translations: list[str]
