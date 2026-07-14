"""Unit tests for the wx-free in-browser read-aloud page builder."""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.browser_reader import build_reader_html, remove_reader_pages


def test_page_has_controls_and_speech() -> None:
    page = build_reader_html("My Doc", "Hello world. Second sentence.")
    # Accessible controls and the Web Speech API are present.
    assert 'id="voice"' in page and "<label" in page
    assert 'id="play"' in page and 'id="stop"' in page
    assert "speechSynthesis" in page
    assert "onvoiceschanged" in page  # picks up online voices as they load
    assert 'aria-live="polite"' in page


def test_title_and_text_are_escaped_in_markup() -> None:
    page = build_reader_html("<script>x</script>", "a & b < c")
    # Visible title/body go through html.escape.
    assert "<script>x</script>" not in page.split("<script>")[0]
    assert "&lt;script&gt;x&lt;/script&gt;" in page
    assert "a &amp; b &lt; c" in page


def test_text_embedded_as_json_string_for_speech() -> None:
    text = 'He said "hi".\nNext line.'
    page = build_reader_html("t", text)
    # The spoken text is embedded as a JS string literal (json.dumps), so quotes
    # and newlines can never break out of the script.
    assert "var TEXT = " + json.dumps(text) in page


def test_empty_text_is_safe() -> None:
    page = build_reader_html("Empty", "")
    assert 'var TEXT = ""' in page
    assert "<article" in page


def test_language_filter_uses_base_subtag() -> None:
    # A regional tag is reduced to its base subtag for voice filtering.
    page = build_reader_html("Doc", "hi", lang="fr-CA")
    assert 'var LANG = "fr"' in page
    assert 'id="alllangs"' in page  # escape hatch to show every language
    assert "langMatches" in page


def test_default_language_is_english() -> None:
    page = build_reader_html("Doc", "hi")
    assert 'var LANG = "en"' in page


def test_multilingual_voices_are_filtered_out() -> None:
    page = build_reader_html("Doc", "hi")
    # Edge "Multilingual" voices crash speechSynthesis; the picker drops them.
    assert "function usable(" in page
    assert "/multilingual/i" in page
    assert "voices().filter(usable)" in page


def test_stop_button_starts_disabled() -> None:
    page = build_reader_html("Doc", "hi")
    # Stop is inert until playback begins, and setState toggles it.
    assert '<button id="stop" type="button" disabled>' in page
    assert "stop.disabled = (s==='idle')" in page


def test_stop_errors_are_not_announced_as_faults() -> None:
    page = build_reader_html("Doc", "hi")
    # Pressing Stop cancels pending utterances, which fire 'interrupted'/'canceled'
    # errors; these must be ignored, not spammed to the aria-live status.
    assert "'interrupted'" in page and "'canceled'" in page
    assert "return; }}" in page or "return; }" in page  # early-return in onerror


def test_playback_is_chunk_by_chunk_with_resume() -> None:
    page = build_reader_html("Doc", "One. Two. Three.")
    # Chunks are spoken one at a time (advancing on onend), not all queued up
    # front, so memory stays small and the queue stays reliable on long docs.
    assert "function speakNext()" in page
    assert "idx >= chunks.length" in page
    # Pause keeps the place and reports the position; Stop resets to the top.
    assert "Paused at section" in page
    assert "Resuming at section" in page
    assert "idx=0; setState('idle'); say('Stopped.')" in page


def test_error_advances_so_player_never_wedges() -> None:
    page = build_reader_html("Doc", "hi")
    # A non-stop chunk error skips the chunk and continues, so the player cannot
    # get stuck in the 'playing' state forever.
    assert "idx++; speakNext();" in page


def test_article_carries_document_language() -> None:
    page = build_reader_html("Doc", "bonjour", lang="fr-CA")
    # The document text gets the document's language for correct pronunciation,
    # while the page chrome stays English.
    assert '<article id="doc" lang="fr"' in page
    assert '<html lang="en">' in page


def test_article_language_defaults_to_english() -> None:
    page = build_reader_html("Doc", "hi")
    assert '<article id="doc" lang="en"' in page


def test_saved_rate_sets_aria_valuetext_on_load() -> None:
    page = build_reader_html("Doc", "hi")
    # aria-valuetext is initialised from the restored rate, not left at the
    # static "Normal speed" until the slider is first moved.
    assert "rate.setAttribute('aria-valuetext'" in page
    assert page.count("aria-valuetext") >= 3  # initial attr, on-load, on-input


def test_remove_reader_pages_deletes_html_and_tmp(tmp_path: Path) -> None:
    d = tmp_path / "browser-reader"
    d.mkdir()
    (d / "read-aloud.html").write_text("secret document text", encoding="utf-8")
    (d / "read-aloud.tmp").write_text("partial", encoding="utf-8")
    remove_reader_pages(d)
    assert list(d.glob("*.html")) == []
    assert list(d.glob("*.tmp")) == []


def test_remove_reader_pages_is_safe_when_dir_absent(tmp_path: Path) -> None:
    # Must not raise when the directory was never created (nothing to clean).
    remove_reader_pages(tmp_path / "does-not-exist")
