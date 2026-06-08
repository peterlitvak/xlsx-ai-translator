"""Services for staging and cleaning up UI download artifacts."""

import os
import shutil
import tempfile
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any, Optional

from models.download_artifact import DownloadArtifact

TRANSLATION_WORK_DIR_ENV = "TRANSLATION_WORK_DIR"
TMPDIR_ENV = "TMPDIR"
DEFAULT_TRANSLATION_WORK_DIR_NAME = "xlsx-llm-translator"
DOWNLOAD_ARTIFACT_DIR_KEY = "download_artifact_dir"
DOWNLOAD_ARTIFACT_PREFIX = "download-"


def get_translation_work_dir() -> Path:
    """Return the directory used for staged download artifacts."""
    configured_work_dir = os.environ.get(TRANSLATION_WORK_DIR_ENV)
    if configured_work_dir:
        return Path(configured_work_dir).expanduser()
    return Path(tempfile.gettempdir()) / DEFAULT_TRANSLATION_WORK_DIR_NAME


def ensure_translation_work_dirs(work_dir: Optional[Path] = None) -> Path:
    """Create configured runtime work directories and return the artifact root."""
    if work_dir is None:
        _ensure_configured_temp_dir()

    artifact_root = work_dir or get_translation_work_dir()
    _ensure_directory(artifact_root)

    return artifact_root


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

    artifact_root = ensure_translation_work_dirs(work_dir)
    artifact_dir = Path(
        tempfile.mkdtemp(
            prefix=DOWNLOAD_ARTIFACT_PREFIX,
            dir=artifact_root,
        )
    )
    artifact_path = artifact_dir / filename
    artifact_path.write_bytes(data)
    session_state[DOWNLOAD_ARTIFACT_DIR_KEY] = str(artifact_dir)

    return DownloadArtifact(path=artifact_path, directory=artifact_dir)


def _ensure_configured_temp_dir() -> None:
    """Create the configured tempfile directory before tempfile chooses a fallback."""
    configured_temp_dir = os.environ.get(TMPDIR_ENV)
    if not configured_temp_dir:
        return

    temp_dir = Path(configured_temp_dir).expanduser()
    _ensure_directory(temp_dir)

    cached_temp_dir = tempfile.tempdir
    if cached_temp_dir is not None and _temp_dir_path(cached_temp_dir) != temp_dir:
        tempfile.tempdir = None


def _temp_dir_path(temp_dir: object) -> Optional[Path]:
    """Return a Path for supported tempfile cache values."""
    if isinstance(temp_dir, str):
        return Path(temp_dir).expanduser()
    return None


def _ensure_directory(directory: Path) -> None:
    """Create a directory and validate that the resulting path is usable."""
    directory.mkdir(parents=True, exist_ok=True)
    if not directory.is_dir():
        raise NotADirectoryError(f"Expected a directory: {directory}")
