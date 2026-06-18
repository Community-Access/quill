"""Unit tests for quill.core.ai.translation."""

from __future__ import annotations

import pytest

from quill.core.ai.translation import (
    LANGUAGE_NAMES,
    SUPPORTED_LANGUAGES,
    TranslationAuthError,
    TranslationError,
    _parse_translation_response,
    _resolve_target_name,
)

# ---------------------------------------------------------------------------
# SUPPORTED_LANGUAGES / LANGUAGE_NAMES
# ---------------------------------------------------------------------------


def test_supported_languages_nonempty() -> None:
    assert len(SUPPORTED_LANGUAGES) > 0


def test_supported_languages_values_are_iso_codes() -> None:
    for name, code in SUPPORTED_LANGUAGES.items():
        assert isinstance(code, str)
        assert 2 <= len(code) <= 7, f"Unexpected code length for {name}: {code!r}"


def test_language_names_is_inverse_of_supported() -> None:
    for _name, code in SUPPORTED_LANGUAGES.items():
        # Last write wins for duplicate codes; just check it maps to a name
        assert LANGUAGE_NAMES.get(code) is not None


def test_english_in_supported() -> None:
    assert "English" in SUPPORTED_LANGUAGES
    assert SUPPORTED_LANGUAGES["English"] == "en"


def test_french_in_supported() -> None:
    assert "French" in SUPPORTED_LANGUAGES


# ---------------------------------------------------------------------------
# _resolve_target_name
# ---------------------------------------------------------------------------


def test_resolve_by_display_name() -> None:
    assert _resolve_target_name("French") == "French"


def test_resolve_by_iso_code() -> None:
    # "fr" -> "French"
    result = _resolve_target_name("fr")
    assert result == "French"


def test_resolve_unknown_passthrough() -> None:
    result = _resolve_target_name("Klingon")
    assert result == "Klingon"


# ---------------------------------------------------------------------------
# _parse_translation_response
# ---------------------------------------------------------------------------


def test_parse_translation_with_source_json_line() -> None:
    response = '{"source": "es"}\nThis is the translated text.'
    translated, source = _parse_translation_response(response)
    assert translated == "This is the translated text."
    assert source == "es"


def test_parse_translation_multiline_translated_text() -> None:
    response = '{"source": "de"}\nLine one.\nLine two.\nLine three.'
    translated, source = _parse_translation_response(response)
    assert "Line one." in translated
    assert "Line three." in translated
    assert source == "de"


def test_parse_translation_no_json_line_returns_full_text() -> None:
    response = "Just the translation without any JSON line."
    translated, source = _parse_translation_response(response)
    assert "Just the translation" in translated
    assert source == "unknown"


def test_parse_translation_malformed_json_falls_back() -> None:
    response = "{not valid json}\nSome text."
    translated, source = _parse_translation_response(response)
    # Should not crash; returns something
    assert isinstance(translated, str)
    assert isinstance(source, str)


def test_parse_translation_empty_source_field() -> None:
    response = '{"source": ""}\nTranslated text.'
    translated, source = _parse_translation_response(response)
    assert translated == "Translated text."
    assert source == ""


def test_parse_translation_strips_whitespace() -> None:
    response = '  {"source": "it"}  \n  Ciao mondo.  '
    translated, source = _parse_translation_response(response)
    assert translated == "Ciao mondo."
    assert source == "it"


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


def test_auth_error_is_translation_error() -> None:
    assert issubclass(TranslationAuthError, TranslationError)


def test_translation_error_message() -> None:
    with pytest.raises(TranslationError, match="no provider"):
        raise TranslationError("no provider configured")
