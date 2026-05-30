"""Base enum type for project enums with uppercase auto-generated values."""

from enum import StrEnum


class AutoNameEnum(StrEnum):
    """String enum whose auto-generated value is the uppercase member name."""

    @staticmethod
    def _generate_next_value_(
        name: str,
        start: int,
        count: int,
        last_values: list[str],
    ) -> str:
        """Return the uppercase enum member name as the generated value."""
        return name.upper()
