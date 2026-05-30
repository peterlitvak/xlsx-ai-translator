"""Pydantic model for single workbook translation results."""

from pydantic import BaseModel, ConfigDict

from models.translation_usage import TranslationUsage


class SingleXLSXTranslationResult(BaseModel):
    """Downloadable result for one translated workbook."""

    model_config = ConfigDict(frozen=True)

    data: bytes
    filename: str
    mime_type: str
    usage: TranslationUsage
