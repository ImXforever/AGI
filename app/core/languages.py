"""Supported languages and language detection utilities for Kia-Agent platform."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MenuLanguage:
    code: str
    native_name: str
    english_name: str
    rtl: bool = False


SUPPORTED_MENU_LANGUAGES: tuple[MenuLanguage, ...] = (
    MenuLanguage("en", "English", "English", False),
    MenuLanguage("fa", "فارسی", "Persian", True),
    MenuLanguage("ar", "العربية", "Arabic", True),
    MenuLanguage("es", "Español", "Spanish", False),
    MenuLanguage("fr", "Français", "French", False),
    MenuLanguage("de", "Deutsch", "German", False),
    MenuLanguage("it", "Italiano", "Italian", False),
    MenuLanguage("pt", "Português", "Portuguese", False),
    MenuLanguage("tr", "Türkçe", "Turkish", False),
    MenuLanguage("ru", "Русский", "Russian", False),
    MenuLanguage("zh", "中文", "Chinese", False),
    MenuLanguage("ja", "日本語", "Japanese", False),
    MenuLanguage("ko", "한국어", "Korean", False),
    MenuLanguage("hi", "हिन्दी", "Hindi", False),
    MenuLanguage("nl", "Nederlands", "Dutch", False),
    MenuLanguage("uk", "Українська", "Ukrainian", False),
    MenuLanguage("sv", "Svenska", "Swedish", False),
    MenuLanguage("id", "Bahasa Indonesia", "Indonesian", False),
    MenuLanguage("ms", "Melayu", "Malay", False),
    MenuLanguage("vi", "Tiếng Việt", "Vietnamese", False),
    MenuLanguage("he", "עברית", "Hebrew", True),
)

LANGUAGE_BY_CODE = {language.code: language for language in SUPPORTED_MENU_LANGUAGES}

LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "fa": "Persian (فارسی)",
    "ar": "Arabic (العربية)",
    "es": "Spanish (Español)",
    "fr": "French (Français)",
    "de": "German (Deutsch)",
    "it": "Italian (Italiano)",
    "pt": "Portuguese (Português)",
    "tr": "Turkish (Türkçe)",
    "ru": "Russian (Русский)",
    "zh": "Chinese (中文)",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)",
    "hi": "Hindi (हिन्दी)",
    "nl": "Dutch (Nederlands)",
    "uk": "Ukrainian (Українська)",
    "sv": "Swedish (Svenska)",
    "id": "Indonesian (Bahasa Indonesia)",
    "ms": "Malay (Melayu)",
    "vi": "Vietnamese (Tiếng Việt)",
    "he": "Hebrew (עברית)",
}


def get_language_name(code: str) -> str:
    """Return friendly language name from code, default to English."""
    return LANGUAGE_NAMES.get(code.lower(), "English")


def language_buttons(*, columns: int = 2) -> list[list[MenuLanguage]]:
    """Return menu languages in rows while preserving the canonical order."""
    if columns < 1:
        raise ValueError("columns must be positive")
    return [
        list(SUPPORTED_MENU_LANGUAGES[index : index + columns])
        for index in range(0, len(SUPPORTED_MENU_LANGUAGES), columns)
    ]


# Persian-specific unique letters
_PERSIAN_SPECIFIC_CHARS = set("گچپژکى")
# Common Persian markers
_PERSIAN_WORDS = frozenset(
    {
        "سلام",
        "درود",
        "خوبی",
        "قیمت",
        "چند",
        "میخوام",
        "می‌خوام",
        "لطفا",
        "لطفاً",
        "ممنون",
        "تشکر",
        "مرسی",
        "هست",
        "نیست",
        "چطور",
        "چگونه",
        "کالا",
        "محصول",
        "خرید",
        "سفارش",
        "پیش‌فاکتور",
        "فاکتور",
        "کمک",
        "پشتیبانی",
        "رو",
        "به",
        "با",
        "از",
        "برای",
        "که",
        "این",
        "آن",
        "شد",
        "کرد",
        "من",
        "تو",
        "ما",
        "شما",
    }
)

# Common Arabic markers
_ARABIC_WORDS = frozenset(
    {
        "مرحبا",
        "اهلا",
        "أهلا",
        "شكرا",
        "شكراً",
        "كم",
        "سعر",
        "اريد",
        "أريد",
        "هل",
        "من فضلك",
        "عرض",
        "خدمة",
        "السلام",
        "عليكم",
        "في",
        "على",
        "إلى",
        "عن",
        "مع",
        "هذا",
        "هذه",
    }
)


def detect_language(text: str) -> str:
    """Fast, accurate rule-based language detector. Default is English ('en')."""
    if not text or not text.strip():
        return "en"

    clean = text.strip()

    # 1. Check Persian specific characters (گ, چ, پ, ژ)
    if any(c in _PERSIAN_SPECIFIC_CHARS for c in clean):
        return "fa"

    words = set(re.findall(r"\w+", clean.lower()))

    # 2. Check Persian dictionary matches
    if words.intersection(_PERSIAN_WORDS):
        return "fa"

    # 3. Check Arabic dictionary matches
    if words.intersection(_ARABIC_WORDS):
        return "ar"

    # 4. Check Cyrillic (Russian / Ukrainian)
    cyrillic = sum(1 for c in clean if "\u0400" <= c <= "\u04FF")
    if cyrillic > len(clean) * 0.3:
        if any(c in "ієї" for c in clean.lower()):
            return "uk"
        return "ru"

    # 5. Check CJK (Chinese / Japanese / Korean)
    if any("\u4e00" <= c <= "\u9fff" for c in clean):
        if any("\u3040" <= c <= "\u30ff" for c in clean):
            return "ja"
        return "zh"
    if any("\uac00" <= c <= "\ud7af" for c in clean):
        return "ko"

    # 6. Check Arabic script characters
    arabic_script_count = sum(1 for c in clean if "\u0600" <= c <= "\u06FF")
    latin_count = sum(1 for c in clean if "a" <= c.lower() <= "z")

    if arabic_script_count > latin_count:
        # Default Arabic script to Persian if ambiguous
        return "fa"

    # Default to English
    return "en"
