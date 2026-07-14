"""Tests for the .po -> .mo compile tool behind installed translations."""

from __future__ import annotations

import gettext
from pathlib import Path

from quill.tools import compile_translations as ct

_PO = """\
msgid ""
msgstr ""
"Language: fr\\n"
"Content-Type: text/plain; charset=UTF-8\\n"

msgid "Open file"
msgstr "Ouvrir le fichier"
"""


def _make_catalog(root: Path, lang: str) -> Path:
    po = root / lang / "LC_MESSAGES" / "quill.po"
    po.parent.mkdir(parents=True)
    po.write_text(_PO, encoding="utf-8")
    return po


def test_compile_writes_loadable_mo(tmp_path: Path, monkeypatch) -> None:
    _make_catalog(tmp_path, "fr")
    monkeypatch.setattr(ct, "_LOCALE_DIR", tmp_path)

    assert ct.compile_all(check=False) == 0
    mo = tmp_path / "fr" / "LC_MESSAGES" / "quill.mo"
    assert mo.is_file()

    # The compiled catalog must be a real gettext .mo that translates strings.
    trans = gettext.translation("quill", localedir=str(tmp_path), languages=["fr"])
    assert trans.gettext("Open file") == "Ouvrir le fichier"


def test_check_mode_does_not_write(tmp_path: Path, monkeypatch) -> None:
    _make_catalog(tmp_path, "fr")
    monkeypatch.setattr(ct, "_LOCALE_DIR", tmp_path)

    assert ct.compile_all(check=True) == 0
    assert not (tmp_path / "fr" / "LC_MESSAGES" / "quill.mo").exists()


def test_no_catalogs_is_a_clean_noop(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(ct, "_LOCALE_DIR", tmp_path)
    assert ct.compile_all(check=False) == 0
    assert ct.po_files() == []
