"""Tests for the DAISY 2.02 text-only talking-book writer (#251)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from quill.io.daisy import (
    CONTENT_FILENAME,
    NCC_FILENAME,
    SMIL_FILENAME,
    write_daisy_textonly,
)

_XHTML_NS = "http://www.w3.org/1999/xhtml"


def _local(tag: str) -> str:
    """The local tag name, dropping any ``{namespace}`` prefix ElementTree adds."""
    return tag.rsplit("}", 1)[-1]


def _find_body(root: ET.Element) -> ET.Element:
    body = root.find(f"{{{_XHTML_NS}}}body")
    assert body is not None
    return body


_SAMPLE = """# Chapter One

The quick brown fox jumps over the lazy dog.

## A Section

More text here with **bold** and _italic_ words.

# Chapter Two

The end.
"""


def _write(tmp_path: Path, text: str = _SAMPLE, **kwargs: object) -> Path:
    out = tmp_path / "book"
    return write_daisy_textonly(text, out, title="My Book", **kwargs)  # type: ignore[arg-type]


def test_creates_three_book_files(tmp_path: Path) -> None:
    book = _write(tmp_path)
    assert (book / NCC_FILENAME).is_file()
    assert (book / CONTENT_FILENAME).is_file()
    assert (book / SMIL_FILENAME).is_file()


def test_files_are_well_formed_xml(tmp_path: Path) -> None:
    book = _write(tmp_path)
    for name in (NCC_FILENAME, CONTENT_FILENAME, SMIL_FILENAME):
        # parses without raising -> well-formed XML
        ET.fromstring((book / name).read_text(encoding="utf-8"))


def test_ncc_declares_daisy_text_only_metadata(tmp_path: Path) -> None:
    book = _write(tmp_path)
    ncc = (book / NCC_FILENAME).read_text(encoding="utf-8")
    assert 'content="Daisy 2.02"' in ncc
    assert 'name="ncc:multimediaType" content="textNCX"' in ncc
    assert 'name="dc:title" content="My Book"' in ncc


def test_inline_markup_is_stripped_from_content(tmp_path: Path) -> None:
    book = _write(tmp_path)
    content = (book / CONTENT_FILENAME).read_text(encoding="utf-8")
    assert "bold" in content and "italic" in content
    assert "**" not in content
    assert "_italic_" not in content


def test_headings_become_nav_links_into_smil(tmp_path: Path) -> None:
    book = _write(tmp_path)
    ncc = (book / NCC_FILENAME).read_text(encoding="utf-8")
    body = _find_body(ET.fromstring(ncc))
    headings = [el for el in body if _local(el.tag) in {f"h{n}" for n in range(1, 7)}]
    # Three headings in the sample: Chapter One, A Section, Chapter Two.
    assert len(headings) == 3
    smil_names = set()
    for heading in headings:
        link = heading.find(f"{{{_XHTML_NS}}}a")
        assert link is not None
        href = link.get("href", "")
        assert href.startswith(f"{SMIL_FILENAME}#")
        smil_names.add(href.split("#", 1)[1])
    # Each heading points at a distinct SMIL par.
    assert len(smil_names) == 3


def test_smil_pars_resolve_to_content_ids(tmp_path: Path) -> None:
    book = _write(tmp_path)
    content_ids = {
        el.get("id")
        for el in ET.fromstring((book / CONTENT_FILENAME).read_text(encoding="utf-8")).iter()
        if el.get("id")
    }
    smil_root = ET.fromstring((book / SMIL_FILENAME).read_text(encoding="utf-8"))
    text_refs = [el.get("src", "") for el in smil_root.iter("text")]
    assert text_refs, "expected at least one text reference in the SMIL"
    for ref in text_refs:
        file_part, _, fragment = ref.partition("#")
        assert file_part == CONTENT_FILENAME
        assert fragment in content_ids


def test_document_without_headings_gets_synthetic_title_heading(tmp_path: Path) -> None:
    book = write_daisy_textonly(
        "Just a paragraph with no headings at all.",
        tmp_path / "plain",
        title="Plain Doc",
    )
    body = _find_body(ET.fromstring((book / NCC_FILENAME).read_text(encoding="utf-8")))
    h1s = [el for el in body if _local(el.tag) == "h1"]
    assert len(h1s) == 1
    link = h1s[0].find(f"{{{_XHTML_NS}}}a")
    assert link is not None and (link.text or "") == "Plain Doc"


def test_first_heading_below_h1_is_promoted(tmp_path: Path) -> None:
    book = write_daisy_textonly(
        "## Starts at level two\n\nSome body text.",
        tmp_path / "h2first",
        title="Title Wins",
    )
    body = _find_body(ET.fromstring((book / NCC_FILENAME).read_text(encoding="utf-8")))
    first = list(body)[0]
    assert _local(first.tag) == "h1"


def test_author_metadata_included_when_provided(tmp_path: Path) -> None:
    book = _write(tmp_path, author="Jane Author")
    ncc = (book / NCC_FILENAME).read_text(encoding="utf-8")
    assert 'name="dc:creator" content="Jane Author"' in ncc


def test_identifier_defaults_to_uuid_urn(tmp_path: Path) -> None:
    book = _write(tmp_path)
    ncc = (book / NCC_FILENAME).read_text(encoding="utf-8")
    assert 'name="dc:identifier" content="urn:uuid:' in ncc
