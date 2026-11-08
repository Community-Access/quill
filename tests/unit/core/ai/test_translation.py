"""Unit tests for quill.core.ai.translation."""

from __future__ import annotations

import pytest

from quill.core.ai.translation import (
    LANGUAGE_NAMES,
    SUPPORTED_LANGUAGES,
    UNCHANGED_TRANSLATION_MESSAGE,
    TranslationAuthError,
    TranslationError,
    _parse_translation_response,
    _resolve_target_name,
    translation_unchanged,
)

# ---------------------------------------------------------------------------
# translation_unchanged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("original", "translated"),
    [
        ("Hola, mundo.", "Hola, mundo."),
        ("Hola, mundo.", "  hola,   MUNDO. \n"),
        ("Line one\nline two", "line one line two"),
        ("Tab\there", "tab here"),
    ],
)
def test_translation_unchanged_ignores_case_and_whitespace(original: str, translated: str) -> None:
    assert translation_unchanged(original, translated)


@pytest.mark.parametrize(
    ("original", "translated"),
    [
        ("Hola, mundo.", "Hello, world."),
        ("Hola, mundo.", "Hola mundo"),
        ("", ""),
        ("   ", "  "),
        ("Hola", ""),
    ],
)
def test_translation_unchanged_false_for_real_or_empty_results(
    original: str, translated: str
) -> None:
    assert not translation_unchanged(original, translated)


def test_unchanged_message_wording() -> None:
    assert UNCHANGED_TRANSLATION_MESSAGE == (
        "The translation came back the same as the original. "
        "The source language may be wrong; choose it instead of Detect."
    )


def test_a_named_source_language_is_told_to_the_ai(monkeypatch) -> None:
    """Choosing the source instead of Detect is the fix the message offers, so it
    has to reach the request: the AI is told what language the text is in."""
    import quill.core.ai.translation as translation

    sent: dict[str, str] = {}

    def fake_response(_conn, _key, prompt, **_kwargs):
        sent["prompt"] = prompt
        return '{"source": "es"}\nHello', ""

    monkeypatch.setattr(translation, "generate_assistant_response", fake_response)
    result = translation.translate_text("Hola", "English", object(), "", source_language="Spanish")

    assert result == ("Hello", "es")
    assert "The following text is in Spanish. Translate it into English" in sent["prompt"]


def test_detect_leaves_the_request_as_it_was(monkeypatch) -> None:
    import quill.core.ai.translation as translation

    sent: dict[str, str] = {}

    def fake_response(_conn, _key, prompt, **_kwargs):
        sent["prompt"] = prompt
        return "Hello", ""

    monkeypatch.setattr(translation, "generate_assistant_response", fake_response)
    translation.translate_text(
        "Hola", "English", object(), "", source_language=translation.SOURCE_DETECT
    )

    assert "Translate the following text into English" in sent["prompt"]
    assert "is in" not in sent["prompt"].split("TEXT TO TRANSLATE")[0]


def test_the_free_ai_message_does_not_mention_a_detect_it_does_not_have() -> None:
    from quill.core.ai.translation import HOSTED_UNCHANGED_TRANSLATION_MESSAGE

    assert HOSTED_UNCHANGED_TRANSLATION_MESSAGE.startswith(
        "The translation came back the same as the original."
    )
    assert "Detect" not in HOSTED_UNCHANGED_TRANSLATION_MESSAGE


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
