"""Pydantic models for upload estimation summaries."""

from typing import Optional

from enums.upload_type import UploadType
from pydantic import BaseModel, ConfigDict


class UploadSummary(BaseModel):
    """Estimated usage and detected type for an uploaded file."""

    model_config = ConfigDict(frozen=True)

    upload_type: UploadType
    workbook_count: Optional[int]
    estimated_input_tokens: int
    estimated_output_tokens: int
