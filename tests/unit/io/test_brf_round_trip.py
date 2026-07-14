"""#235 (BR-012): BRF/BRL save path round-trips byte-for-byte with a soft warning."""

from __future__ import annotations

from pathlib import Path

from quill.core.document import Document
from quill.io.open_read import read_open_document
from quill.io.text import set_save_warning_hook, write_text_document

_CORPUS = Path(__file__).resolve().parents[2] / "corpus" / "braille" / "one_crazy_night.brf"


def test_corpus_brf_round_trips_byte_for_byte(tmp_path: Path) -> None:
    original = _CORPUS.read_bytes()
    document, _book = read_open_document(_CORPUS, _CORPUS.suffix)

    out = tmp_path / "out.brf"
    write_text_document(document, out)

    # Form feeds, CRLF line endings, and trailing spaces must all survive.
    assert out.read_bytes() == original


def test_brf_save_does_not_normalize_mixed_line_endings(tmp_path: Path) -> None:
    text = "alpha\r\nbeta\ngamma\rdelta\x0c"  # CRLF, LF, CR, and a form feed
    document = Document(text=text, path=tmp_path / "m.brf", encoding="ascii")

    out = write_text_document(document, tmp_path / "m.brf")

    assert out.read_bytes() == text.encode("ascii")


def test_brf_unicode_braille_saves_unchanged_and_warns(tmp_path: Path) -> None:
    warnings: list[str] = []
    set_save_warning_hook(warnings.append)
    try:
        text = "hello⠀world\x0c"  # U+2800 BRAILLE PATTERN BLANK is non-NABCC
        document = Document(text=text, path=tmp_path / "u.brf", encoding="utf-8")

        out = write_text_document(document, tmp_path / "u.brf")

        assert out.read_bytes() == text.encode("utf-8")  # saved unchanged
        assert warnings, "a non-NABCC save must record a warning"
        assert "non-braille-ASCII" in warnings[0]
    finally:
        set_save_warning_hook(None)


def test_clean_brf_save_emits_no_warning(tmp_path: Path) -> None:
    warnings: list[str] = []
    set_save_warning_hook(warnings.append)
    try:
        document = Document(text="clean nabcc text\x0c", path=tmp_path / "c.brf", encoding="ascii")
        write_text_document(document, tmp_path / "c.brf")
        assert warnings == []
    finally:
        set_save_warning_hook(None)
