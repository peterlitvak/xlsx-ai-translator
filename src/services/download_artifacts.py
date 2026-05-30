"""Services for staging and cleaning up UI download artifacts."""

import os
import shutil
import tempfile
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any, Optional

from models.download_artifact import DownloadArtifact

TRANSLATION_WORK_DIR_ENV = "TRANSLATION_WORK_DIR"
DEFAULT_TRANSLATION_WORK_DIR = Path(tempfile.gettempdir()) / "xlsx-llm-translator"
DOWNLOAD_ARTIFACT_DIR_KEY = "download_artifact_dir"


def get_translation_work_dir() -> Path:
    """Return the directory used for staged download artifacts."""
    return Path(
        os.environ.get(TRANSLATION_WORK_DIR_ENV, str(DEFAULT_TRANSLATION_WORK_DIR))
    ).expanduser()


def cleanup_download_artifact(session_state: MutableMapping[Any, Any]) -> None:
    """Remove the staged download artifact stored in the provided session state."""
    artifact_dir = session_state.pop(DOWNLOAD_ARTIFACT_DIR_KEY, None)
    if isinstance(artifact_dir, str) and artifact_dir:
        shutil.rmtree(artifact_dir, ignore_errors=True)


def stage_download_artifact(
    data: bytes,
    filename: str,
    session_state: MutableMapping[Any, Any],
    work_dir: Optional[Path] = None,
) -> DownloadArtifact:
    """Write translated bytes to external work storage until download is requested."""
    cleanup_download_artifact(session_state)

    artifact_root = work_dir or get_translation_work_dir()
    artifact_root.mkdir(parents=True, exist_ok=True)
    artifact_dir = Path(tempfile.mkdtemp(prefix="download-", dir=artifact_root))
    artifact_path = artifact_dir / filename
    artifact_path.write_bytes(data)
    session_state[DOWNLOAD_ARTIFACT_DIR_KEY] = str(artifact_dir)

    return DownloadArtifact(path=artifact_path, directory=artifact_dir)
