"""Models for staged downloadable artifacts."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class DownloadArtifact(BaseModel):
    """Translated file staged for UI download."""

    model_config = ConfigDict(frozen=True)

    path: Path
    directory: Path
