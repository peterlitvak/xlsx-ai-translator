"""Pydantic model for zip translation progress updates."""

from pydantic import BaseModel, ConfigDict


class ZipTranslationProgress(BaseModel):
    """Progress update for one workbook inside a zip translation."""

    model_config = ConfigDict(frozen=True)

    relative_path: str
    workbook_index: int
    workbook_count: int
    workbook_progress: float
    overall_progress: float
