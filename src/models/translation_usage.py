"""Pydantic model for translation usage metrics."""

from pydantic import BaseModel, ConfigDict


class TranslationUsage(BaseModel):
    """Actual token and cost usage reported by a translation run."""

    model_config = ConfigDict(frozen=True)

    input_tokens: int
    output_tokens: int
    cost: float
