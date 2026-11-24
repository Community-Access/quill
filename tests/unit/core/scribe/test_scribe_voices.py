"""The starting dialect and the voice list (quill.core.scribe.voices).

Jeff's QUILL Lite test, 2026-11-23: with Dialect on Scribe's default the Voice
list was only "Scribe's default". A dialect is now suggested from the
document's language or Windows', exactly first and then by language alone,
and with no dialect the list has every dialect's voices.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from quill.core.scribe import voices as v

ENGLISH = [
    ("English (Australia)", "en-AU"),
    ("English (United States)", "en-US"),
    ("English (United Kingdom)", "en-GB"),
]
VOICES = {
    "en-US": [("Jenny", "en-US-JennyNeural", True), ("Guy", "en-US-GuyNeural", False)],
    "en-GB": [("Sonia", "en-GB-SoniaNeural", True)],
}


@pytest.mark.parametrize(
    ("raw", "tag"),
    [
        ("en_US.UTF-8", "en-US"),
        ("EN-gb", "en-GB"),
        ("zh-hant-tw", "zh-Hant-TW"),
        ("English_United States", ""),
        ("", ""),
        (None, ""),
    ],
)
def test_tags_are_normalised(raw: object, tag: str) -> None:
    assert v.normalise_tag(raw) == tag


def test_an_exact_match_wins() -> None:
    assert v.suggest_dialect(ENGLISH, ["en-GB"], "en") == "en-GB"


def test_a_later_exact_match_beats_a_language_only_one() -> None:
    # The document says only "en", Windows says en-GB: Windows' exact match wins.
    assert v.suggest_dialect(ENGLISH, ["en", "en-GB"], "en") == "en-GB"


def test_a_region_scribe_lacks_falls_back_to_the_language() -> None:
    assert v.suggest_dialect(ENGLISH, ["en-NZ"], "en") == "en-AU"  # Scribe's first English


def test_no_hint_in_the_language_is_no_suggestion() -> None:
    assert v.suggest_dialect(ENGLISH, ["fr-FR", "de-DE"], "en") == ""
    assert v.suggest_dialect([], ["en-US"], "en") == ""


def test_detect_guesses_the_first_hinted_language_scribe_has() -> None:
    dialects = {"en": ENGLISH, "fr": [("French (France)", "fr-FR")], "de": []}
    assert v.guess_language(dialects, ["de-DE", "fr-CA", "en-US"]) == "fr"
    assert v.guess_language(dialects, ["ja-JP"]) == ""


def test_the_os_tags_are_tags(monkeypatch: pytest.MonkeyPatch) -> None:
    tags = v.os_language_tags()
    assert all(v.normalise_tag(tag) == tag for tag in tags)


def test_a_dialect_lists_its_own_voices_marking_those_without_a_sample() -> None:
    items = v.voice_items("en-US", ENGLISH, VOICES)
    assert [item.label for item in items] == ["Jenny", "Guy, no sample"]
    assert {item.locale for item in items} == {"en-US"}


def test_without_a_dialect_every_dialects_voices_carry_their_dialect() -> None:
    items = v.voice_items("", ENGLISH, VOICES)
    assert [item.label for item in items] == [
        "Jenny, English (United States)",
        "Guy, English (United States), no sample",
        "Sonia, English (United Kingdom)",
    ]
    assert [item.locale for item in items] == ["en-US", "en-US", "en-GB"]
    assert items[1].name == "Guy" and not items[1].has_sample


def _docx(path: Path, core: str = "", styles: str = "") -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        if core:
            archive.writestr("docProps/core.xml", core)
        if styles:
            archive.writestr("word/styles.xml", styles)
        archive.writestr("word/document.xml", "<w:document/>")
    return path


def test_a_word_documents_language(tmp_path: Path) -> None:
    core = "<cp:coreProperties><dc:language>en-GB</dc:language></cp:coreProperties>"
    assert v.document_language(_docx(tmp_path / "a.docx", core=core)) == "en-GB"
    styles = '<w:styles><w:rPr><w:lang w:val="fr-CA" w:eastAsia="zh-CN"/></w:rPr></w:styles>'
    assert v.document_language(_docx(tmp_path / "b.docx", styles=styles)) == "fr-CA"
    assert v.document_language(_docx(tmp_path / "c.docx")) == ""


def test_a_web_page_and_a_book(tmp_path: Path) -> None:
    page = tmp_path / "a.html"
    page.write_text('<!doctype html><html lang="es-MX"><body>Hola</body></html>')
    assert v.document_language(page) == "es-MX"
    book = tmp_path / "b.epub"
    with zipfile.ZipFile(book, "w") as archive:
        archive.writestr("OEBPS/content.opf", "<package><dc:language>de</dc:language></package>")
    assert v.document_language(book) == "de"


def test_a_pdf_lang(tmp_path: Path) -> None:
    pypdf = pytest.importorskip("pypdf")
    writer = pypdf.PdfWriter()
    writer.add_blank_page(72, 72)
    writer._root_object[pypdf.generic.NameObject("/Lang")] = pypdf.generic.TextStringObject("en-AU")
    path = tmp_path / "a.pdf"
    with path.open("wb") as handle:
        writer.write(handle)
    assert v.document_language(path) == "en-AU"


def test_anything_unreadable_is_no_language(tmp_path: Path) -> None:
    broken = tmp_path / "broken.docx"
    broken.write_bytes(b"not a zip")
    assert v.document_language(broken) == ""
    assert v.document_language(tmp_path / "missing.pdf") == ""
    assert v.document_language(None) == ""
    (tmp_path / "a.txt").write_text("plain")
    assert v.document_language(tmp_path / "a.txt") == ""
