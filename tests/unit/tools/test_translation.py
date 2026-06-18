"""Tests for the translation infrastructure CI gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.tools.check_translation import (
    _extract_placeholders,
    _mnemonic_count,
    _parse_po,
    check_babel_cfg,
    check_pot_exists,
    run,
)


def test_babel_cfg_exists() -> None:
    errors = check_babel_cfg()
    assert not errors, "\n".join(errors)


def test_pot_file_present_or_friendly_error() -> None:
    errors = check_pot_exists()
    for err in errors:
        assert "pybabel" in err, f"Error message missing pybabel hint: {err!r}"


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "s, expected",
    [
        ("&Open", 1),
        ("&Save &As", 2),
        ("No mnemonic", 0),
        ("&&", 0),  # escaped literal &, not a mnemonic
        ("&File && menu", 1),  # one real mnemonic, one escaped
    ],
)
def test_mnemonic_count(s: str, expected: int) -> None:
    assert _mnemonic_count(s) == expected


@pytest.mark.parametrize(
    "s, expected",
    [
        ("{name}", ["{name}"]),
        ("{count} words", ["{count}"]),
        ("%(provider)s key", ["%(provider)s"]),
        ("no placeholders", []),
        ("{a} and {b}", ["{a}", "{b}"]),
    ],
)
def test_extract_placeholders(s: str, expected: list[str]) -> None:
    assert _extract_placeholders(s) == expected


def test_parse_po_basic(tmp_path: Path) -> None:
    po = tmp_path / "test.po"
    po.write_text(
        '# comment\nmsgid "Hello"\nmsgstr "Bonjour"\n\nmsgid "Goodbye"\nmsgstr "Au revoir"\n',
        encoding="utf-8",
    )
    pairs = _parse_po(po)
    assert ("Hello", "Bonjour", False) in pairs
    assert ("Goodbye", "Au revoir", False) in pairs


def test_parse_po_multiline(tmp_path: Path) -> None:
    po = tmp_path / "test.po"
    po.write_text(
        'msgid ""\n"Line one\\n"\n"Line two"\nmsgstr ""\n"Ligne un\\n"\n"Ligne deux"\n',
        encoding="utf-8",
    )
    pairs = _parse_po(po)
    assert any("Line one" in mid for mid, _, _ in pairs)


def test_parse_po_fuzzy_flag(tmp_path: Path) -> None:
    po = tmp_path / "test.po"
    po.write_text(
        '#, fuzzy\nmsgid "Hello"\nmsgstr "Bonjour"\n',
        encoding="utf-8",
    )
    pairs = _parse_po(po)
    assert any(is_fuzzy for _, _, is_fuzzy in pairs)


# ---------------------------------------------------------------------------
# Integration-style tests using temporary locale trees
# ---------------------------------------------------------------------------


def _write_pot(path: Path, entries: list[str]) -> None:
    lines = [
        'msgid ""\n',
        'msgstr ""\n',
        '"Content-Type: text/plain; charset=utf-8\\n"\n',
        "\n",
    ]
    for e in entries:
        lines.append(f'msgid "{e}"\n')
        lines.append('msgstr ""\n')
        lines.append("\n")
    path.write_text("".join(lines), encoding="utf-8")


def _write_po(path: Path, pairs: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        'msgid ""\n',
        'msgstr ""\n',
        '"Content-Type: text/plain; charset=utf-8\\n"\n',
        '"Language: test\\n"\n',
        "\n",
    ]
    for msgid, msgstr in pairs:
        lines.append(f'msgid "{msgid}"\n')
        lines.append(f'msgstr "{msgstr}"\n')
        lines.append("\n")
    path.write_text("".join(lines), encoding="utf-8")


def test_run_passes_with_no_po_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.tools.check_translation as ct

    pot = tmp_path / "quill.pot"
    _write_pot(pot, ["Hello"])
    babel_cfg = tmp_path / "babel.cfg"
    babel_cfg.write_text("[python: quill/**.py]\n", encoding="utf-8")

    monkeypatch.setattr(ct, "_POT_FILE", pot)
    monkeypatch.setattr(ct, "_LOCALE_DIR", tmp_path)
    monkeypatch.setattr(ct, "_BABEL_CFG", babel_cfg)

    assert run() == 0


def test_placeholder_mismatch_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import quill.tools.check_translation as ct

    pot = tmp_path / "quill.pot"
    _write_pot(pot, ["{count} items"])
    po_dir = tmp_path / "fr" / "LC_MESSAGES"
    _write_po(po_dir / "quill.po", [("{count} items", "éléments")])  # missing {count}

    monkeypatch.setattr(ct, "_POT_FILE", pot)
    monkeypatch.setattr(ct, "_LOCALE_DIR", tmp_path)
    monkeypatch.setattr(ct, "_BABEL_CFG", tmp_path / "babel.cfg")
    (tmp_path / "babel.cfg").write_text("[python: quill/**.py]\n", encoding="utf-8")

    result = run()
    out = capsys.readouterr().out
    assert result == 1
    assert "placeholder mismatch" in out


def test_mnemonic_mismatch_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import quill.tools.check_translation as ct

    pot = tmp_path / "quill.pot"
    _write_pot(pot, ["&Open"])
    po_dir = tmp_path / "de" / "LC_MESSAGES"
    _write_po(po_dir / "quill.po", [("&Open", "Oeffnen")])  # & dropped in translation

    monkeypatch.setattr(ct, "_POT_FILE", pot)
    monkeypatch.setattr(ct, "_LOCALE_DIR", tmp_path)
    monkeypatch.setattr(ct, "_BABEL_CFG", tmp_path / "babel.cfg")
    (tmp_path / "babel.cfg").write_text("[python: quill/**.py]\n", encoding="utf-8")

    result = run()
    out = capsys.readouterr().out
    assert result == 1
    assert "mnemonic count mismatch" in out


def test_min_coverage_threshold_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import quill.tools.check_translation as ct

    pot = tmp_path / "quill.pot"
    _write_pot(pot, ["Hello", "Goodbye", "Save", "Open"])
    po_dir = tmp_path / "es" / "LC_MESSAGES"
    # Only 1 of 4 strings translated = 25%
    _write_po(po_dir / "quill.po", [("Hello", "Hola"), ("Goodbye", ""), ("Save", ""), ("Open", "")])

    monkeypatch.setattr(ct, "_POT_FILE", pot)
    monkeypatch.setattr(ct, "_LOCALE_DIR", tmp_path)
    monkeypatch.setattr(ct, "_BABEL_CFG", tmp_path / "babel.cfg")
    (tmp_path / "babel.cfg").write_text("[python: quill/**.py]\n", encoding="utf-8")

    result = run(min_coverage=70.0)
    out = capsys.readouterr().out
    assert result == 1
    assert "below required" in out
