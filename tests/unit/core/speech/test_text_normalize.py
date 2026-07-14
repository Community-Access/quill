"""Unit tests for TTS text normalization (batch-document-to-speech §4.9)."""

from __future__ import annotations

from quill.core.speech.text_normalize import TextNormalizationOptions, normalize_for_tts


def _n(text: str, **kw: object) -> str:
    return normalize_for_tts(text, TextNormalizationOptions(**kw))  # type: ignore[arg-type]


def test_publication_shorthand_spoken() -> None:
    assert _n("Vol. 12, No. 3") == "Volume 12, Number 3"
    assert _n("Vol. 12", publications=False) == "Vol. 12"  # opt-out leaves it


def test_resolution_numbers_spoken() -> None:
    assert _n("Resolution 2025-02 passed") == "Resolution 2025 dash 2 passed"
    assert _n("2025-123") == "2025 dash 123"
    assert _n("see 1984") == "see 1984"  # a plain year is untouched


def test_smart_quotes_and_apostrophes() -> None:
    assert _n("“Hi” don’t") == '"Hi" don\'t'


def test_em_dash_becomes_comma_pause_by_default() -> None:
    assert _n("yes—no") == "yes, no"


def test_en_dash_and_smart_ranges() -> None:
    assert _n("pages 5–10") == "pages 5 to 10"  # smart range default on


def test_em_dash_modes() -> None:
    assert _n("a—b", dash_mode="hyphen") == "a - b"
    assert _n("a—b", dash_mode="spoken") == "a em dash b"
    assert _n("a—b", dash_mode="remove") == "a b"


def test_ellipsis_collapses_to_pause() -> None:
    assert _n("wait… ok") == "wait, ok"
    assert _n("wait... ok") == "wait, ok"


def test_invisibles_and_control_chars_removed() -> None:
    assert _n("a b​c­d﻿e") == "a bcde"


def test_ligatures() -> None:
    assert _n("ﬁle ﬂow") == "file flow"


def test_symbols_speak_strip_keep() -> None:
    assert "copyright" in _n("© 2026")
    assert "©" not in _n("© 2026", symbols="strip")
    assert "©" in _n("© 2026", symbols="keep")


def test_currency_and_percent() -> None:
    assert _n("$5 and 50%") == "5 dollars and 50 percent"


def test_fractions() -> None:
    assert "one half" in _n("½ cup")


def test_bullets_stripped_at_line_start() -> None:
    assert _n("• first\n• second") == "first\nsecond"


def test_repeated_punctuation_collapsed() -> None:
    assert _n("really???") == "really?"
    assert _n("wow!!!") == "wow!"


def test_phone_numbers_spoken_as_grouped_digits() -> None:
    out = _n("Call (555) 123-4567 now", phone_numbers=True)
    assert "five five five" in out
    assert "minus" not in out  # the dash was claimed, not read as subtraction
    assert "-" not in out


def test_phone_numbers_off_by_default() -> None:
    assert "(555) 123-4567" in _n("Call (555) 123-4567 now")


def test_email_speak_then_repeat_by_default() -> None:
    out = _n("write jeff@quill.app")
    assert out.count("jeff at quill dot app") == 2  # said then repeated
    assert "@" not in out and "<" not in out


def test_url_announce_mode() -> None:
    assert "link" in _n("see https://example.com/x", address_mode="announce")


def test_long_url_falls_back_to_link() -> None:
    long_url = "https://example.com/" + "a" * 80
    assert _n(f"go {long_url}").strip().endswith("link")


def test_acronyms_opt_in_spells_out_but_keeps_words() -> None:
    out = _n("Learn SQL at NASA", acronyms=True)
    assert "S Q L" in out
    assert "NASA" in out  # known word-acronym kept


def test_extra_replacements_applied_last() -> None:
    out = _n("the § sign", extra_replacements={"section": "SECTION-MARK"})
    assert "SECTION-MARK" in out  # symbol -> "section" -> overridden by escape hatch


def test_options_round_trip() -> None:
    original = TextNormalizationOptions(
        dash_mode="hyphen", symbols="strip", phone_numbers=True, extra_replacements={"x": "y"}
    )
    clone = TextNormalizationOptions.from_dict(original.to_dict())
    assert clone == original


def test_empty_text() -> None:
    assert normalize_for_tts("", None) == ""
