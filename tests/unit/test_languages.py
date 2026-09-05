"""Tests for the international Telegram language menu and Persian support."""

from __future__ import annotations

from app.core.languages import LANGUAGE_BY_CODE, SUPPORTED_MENU_LANGUAGES, detect_language, language_buttons


def test_supported_languages_include_persian_and_international() -> None:
    codes = {language.code for language in SUPPORTED_MENU_LANGUAGES}
    assert {"ar", "en", "fa"}.issubset(codes)
    assert {"es", "fr", "de", "it", "pt", "tr", "ru", "zh", "ja", "ko", "hi", "nl"} <= codes
    assert len(codes) >= 21


def test_language_detection() -> None:
    assert detect_language("سلام، قیمت محصولات شما چنده؟") == "fa"
    assert detect_language("مرحبا، أريد معرفة الأسعار") == "ar"
    assert detect_language("Hello, what are your product prices?") == "en"


def test_language_codes_are_unique_and_button_callbacks_are_stable() -> None:
    assert len(LANGUAGE_BY_CODE) == len(SUPPORTED_MENU_LANGUAGES)
    rows = language_buttons(columns=2)
    flattened = [language.code for row in rows for language in row]
    assert flattened == [language.code for language in SUPPORTED_MENU_LANGUAGES]
    assert all(f"lang_{code}" for code in flattened)


def test_language_menu_rejects_invalid_column_count() -> None:
    try:
        language_buttons(columns=0)
    except ValueError as exc:
        assert "positive" in str(exc)
    else:
        raise AssertionError("expected ValueError")
