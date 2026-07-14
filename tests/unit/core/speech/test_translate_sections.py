"""Tests for the section translator (translated audio export, §7)."""

from __future__ import annotations

import pytest

from quill.core.speech.text_polish import DocumentSection
from quill.core.speech.translate_sections import (
    SectionTranslationError,
    translate_sections,
)


def test_translates_title_and_body_and_caches() -> None:
    calls: list[str] = []

    def fake(text: str) -> str:
        calls.append(text)
        return f"<{text}>"

    sections = [
        DocumentSection("Hello", "World"),
        DocumentSection("Hello", "Again"),  # "Hello" repeats -> translated once (cached)
    ]
    out = translate_sections(sections, fake, sleep=lambda _s: None)
    assert out[0] == DocumentSection("<Hello>", "<World>")
    assert out[1].title == "<Hello>" and out[1].text == "<Again>"
    # "Hello" appears twice but is only translated once.
    assert calls.count("Hello") == 1


def test_empty_strings_pass_through_untranslated() -> None:
    out = translate_sections(
        [DocumentSection("", "body only")], lambda t: t.upper(), sleep=lambda _s: None
    )
    assert out[0].title == "" and out[0].text == "BODY ONLY"


def test_retries_then_succeeds() -> None:
    attempts = {"n": 0}

    def flaky(text: str) -> str:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("transient")
        return "ok"

    out = translate_sections(
        [DocumentSection("", "x")], flaky, max_retries=3, sleep=lambda _s: None
    )
    assert out[0].text == "ok" and attempts["n"] == 3


def test_halts_on_persistent_failure() -> None:
    def always_fail(text: str) -> str:
        raise RuntimeError("down")

    with pytest.raises(SectionTranslationError):
        translate_sections(
            [DocumentSection("", "x")], always_fail, max_retries=2, sleep=lambda _s: None
        )


def test_empty_translation_result_is_a_failure() -> None:
    with pytest.raises(SectionTranslationError):
        translate_sections(
            [DocumentSection("", "x")], lambda t: "   ", max_retries=2, sleep=lambda _s: None
        )
