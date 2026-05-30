"""Upload type labels used by UI estimation models."""

from enum import auto

from enums.auto_name_enum import AutoNameEnum


class UploadType(AutoNameEnum):
    """Supported upload categories."""

    XLSX_WORKBOOK = auto()
    ZIP_ARCHIVE = auto()
    UNKNOWN = auto()

    @property
    def display_name(self) -> str:
        """Return the user-facing upload type label."""
        return UPLOAD_TYPE_DISPLAY_NAMES[self]

    def __str__(self) -> str:
        """Return the user-facing upload type label."""
        return self.display_name


UPLOAD_TYPE_DISPLAY_NAMES: dict[UploadType, str] = {
    UploadType.XLSX_WORKBOOK: "XLSX workbook",
    UploadType.ZIP_ARCHIVE: "ZIP archive",
    UploadType.UNKNOWN: "Unknown",
}
