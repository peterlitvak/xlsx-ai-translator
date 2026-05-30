"""Pydantic model for zip archive translation results."""

from pydantic import BaseModel, ConfigDict

from models.translation_usage import TranslationUsage


class ZipXLSXTranslationResult(BaseModel):
    """Downloadable result for a translated zip archive."""

    model_config = ConfigDict(frozen=True)

    data: bytes
    filename: str
    mime_type: str
    usage: TranslationUsage
    workbook_count: int
