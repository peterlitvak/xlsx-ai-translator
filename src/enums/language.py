"""Supported language options for translation workflows."""

from enum import auto

from enums.auto_name_enum import AutoNameEnum


class SupportedLanguage(AutoNameEnum):
    """Language codes supported by the Streamlit UI."""

    FRENCH = auto()
    GERMAN = auto()
    SPANISH = auto()
    RUSSIAN = auto()
    CHINESE_SIMPLIFIED = auto()
    CHINESE_TRADITIONAL = auto()
    ITALIAN = auto()
    PORTUGUESE = auto()
    JAPANESE = auto()
    KOREAN = auto()
    ARABIC = auto()
    HINDI = auto()
    DUTCH = auto()
    POLISH = auto()
    TURKISH = auto()
    CZECH = auto()
    GREEK = auto()
    HEBREW = auto()
    VIETNAMESE = auto()
    UKRAINIAN = auto()
    SWEDISH = auto()
    FINNISH = auto()
    DANISH = auto()
    NORWEGIAN = auto()
    HUNGARIAN = auto()
    ROMANIAN = auto()
    BULGARIAN = auto()
    INDONESIAN = auto()
    THAI = auto()
    MALAY = auto()
    ENGLISH = auto()

    @property
    def language_code(self) -> str:
        """Return the language code passed to translation services."""
        return SUPPORTED_LANGUAGE_CODES[self]

    @property
    def display_name(self) -> str:
        """Return the human-readable language name."""
        return SUPPORTED_LANGUAGE_DISPLAY_NAMES[self]

    @property
    def option_label(self) -> str:
        """Return the label shown in language select controls."""
        return f"{self.display_name} ({self.language_code})"

    def __str__(self) -> str:
        """Return the select-control label for this language."""
        return self.option_label


SUPPORTED_LANGUAGE_DISPLAY_NAMES: dict[SupportedLanguage, str] = {
    SupportedLanguage.FRENCH: "French",
    SupportedLanguage.GERMAN: "German",
    SupportedLanguage.SPANISH: "Spanish",
    SupportedLanguage.RUSSIAN: "Russian",
    SupportedLanguage.CHINESE_SIMPLIFIED: "Chinese (Simplified)",
    SupportedLanguage.CHINESE_TRADITIONAL: "Chinese (Traditional)",
    SupportedLanguage.ITALIAN: "Italian",
    SupportedLanguage.PORTUGUESE: "Portuguese",
    SupportedLanguage.JAPANESE: "Japanese",
    SupportedLanguage.KOREAN: "Korean",
    SupportedLanguage.ARABIC: "Arabic",
    SupportedLanguage.HINDI: "Hindi",
    SupportedLanguage.DUTCH: "Dutch",
    SupportedLanguage.POLISH: "Polish",
    SupportedLanguage.TURKISH: "Turkish",
    SupportedLanguage.CZECH: "Czech",
    SupportedLanguage.GREEK: "Greek",
    SupportedLanguage.HEBREW: "Hebrew",
    SupportedLanguage.VIETNAMESE: "Vietnamese",
    SupportedLanguage.UKRAINIAN: "Ukrainian",
    SupportedLanguage.SWEDISH: "Swedish",
    SupportedLanguage.FINNISH: "Finnish",
    SupportedLanguage.DANISH: "Danish",
    SupportedLanguage.NORWEGIAN: "Norwegian",
    SupportedLanguage.HUNGARIAN: "Hungarian",
    SupportedLanguage.ROMANIAN: "Romanian",
    SupportedLanguage.BULGARIAN: "Bulgarian",
    SupportedLanguage.INDONESIAN: "Indonesian",
    SupportedLanguage.THAI: "Thai",
    SupportedLanguage.MALAY: "Malay",
    SupportedLanguage.ENGLISH: "English",
}

SUPPORTED_LANGUAGE_CODES: dict[SupportedLanguage, str] = {
    SupportedLanguage.FRENCH: "fr",
    SupportedLanguage.GERMAN: "de",
    SupportedLanguage.SPANISH: "es",
    SupportedLanguage.RUSSIAN: "ru",
    SupportedLanguage.CHINESE_SIMPLIFIED: "zh",
    SupportedLanguage.CHINESE_TRADITIONAL: "zh-tw",
    SupportedLanguage.ITALIAN: "it",
    SupportedLanguage.PORTUGUESE: "pt",
    SupportedLanguage.JAPANESE: "ja",
    SupportedLanguage.KOREAN: "ko",
    SupportedLanguage.ARABIC: "ar",
    SupportedLanguage.HINDI: "hi",
    SupportedLanguage.DUTCH: "nl",
    SupportedLanguage.POLISH: "pl",
    SupportedLanguage.TURKISH: "tr",
    SupportedLanguage.CZECH: "cs",
    SupportedLanguage.GREEK: "el",
    SupportedLanguage.HEBREW: "he",
    SupportedLanguage.VIETNAMESE: "vi",
    SupportedLanguage.UKRAINIAN: "uk",
    SupportedLanguage.SWEDISH: "sv",
    SupportedLanguage.FINNISH: "fi",
    SupportedLanguage.DANISH: "da",
    SupportedLanguage.NORWEGIAN: "no",
    SupportedLanguage.HUNGARIAN: "hu",
    SupportedLanguage.ROMANIAN: "ro",
    SupportedLanguage.BULGARIAN: "bg",
    SupportedLanguage.INDONESIAN: "id",
    SupportedLanguage.THAI: "th",
    SupportedLanguage.MALAY: "ms",
    SupportedLanguage.ENGLISH: "en",
}
