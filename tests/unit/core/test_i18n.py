"""Tests for the i18n helpers behind the display-language switcher."""

from __future__ import annotations

from pathlib import Path

import quill.core.i18n as i18n


def test_language_display_name_exact_base_and_fallback() -> None:
    assert i18n.language_display_name("en") == "English"
    # Base-language fallback: a regional variant uses the base language name.
    assert i18n.language_display_name("fr_CA").startswith("French")
    assert i18n.language_display_name("fr-CA").startswith("French")
    # Unknown tag falls back to the tag itself.
    assert i18n.language_display_name("xx") == "xx"


def test_available_languages_lists_only_compiled(tmp_path: Path, monkeypatch) -> None:
    locale_dir = tmp_path / "locale"
    # A language with a compiled .mo is listed.
    (locale_dir / "fr" / "LC_MESSAGES").mkdir(parents=True)
    (locale_dir / "fr" / "LC_MESSAGES" / "quill.mo").write_bytes(b"")
    # A language with only a .po (no .mo) is not yet switchable.
    (locale_dir / "de" / "LC_MESSAGES").mkdir(parents=True)
    (locale_dir / "de" / "LC_MESSAGES" / "quill.po").write_text("", encoding="utf-8")
    monkeypatch.setattr(i18n, "_LOCALE_DIR", locale_dir)
    assert i18n.available_languages() == ["fr"]


def test_available_languages_empty_when_only_template(monkeypatch) -> None:
    monkeypatch.setattr(i18n, "_LOCALE_DIR", Path("/does/not/exist"))
    assert i18n.available_languages() == []
