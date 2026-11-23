"""Scribe for Documents in the rest of the family: the wx-free parts (PRD 8.3 to 8.8).

Linked documents (Cast and Social), the headings a Beacon place can point at,
chapter markers from the DAISY navigation (Studio), the result sentence's
note, the F1 purposes every app's catalogue merges, and Beacon's Scribe
places.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.scribe import queue as q
from quill.core.scribe import sentences as say
from quill.core.scribe.headings import (
    START,
    Heading,
    document_headings,
    heading_path,
    heading_rows,
    html_headings,
)
from quill.core.scribe.links import (
    documents_in_html,
    documents_in_text,
    is_document_link,
    list_label,
    none_sentence,
    row_labels,
)

# ------------------------------------------------------------ linked documents


def test_only_direct_links_to_files_scribe_takes_are_documents() -> None:
    assert is_document_link("https://example.org/papers/Notes.pdf")
    assert is_document_link("http://example.org/a/b/Report%20One.DOCX?x=1")
    assert not is_document_link("https://example.org/page.html")
    assert not is_document_link("https://example.org/episode/42")
    assert not is_document_link("ftp://example.org/Notes.pdf")
    assert not is_document_link("Notes.pdf")


def test_show_notes_give_their_document_links_once_in_order() -> None:
    html = (
        '<p>Read <a href="https://example.org/Notes.pdf">the transcript</a> and '
        '<a href="https://example.org/show">our site</a>. Slides: '
        "https://cdn.example.org/deck.pptx and again "
        '<a href="https://example.org/Notes.pdf">here</a>.</p>'
    )
    documents = documents_in_html(html)
    assert [d.url for d in documents] == [
        "https://example.org/Notes.pdf",
        "https://cdn.example.org/deck.pptx",
    ]
    assert documents[0].text == "the transcript"


def test_a_post_adds_its_own_link_and_media_to_its_text() -> None:
    documents = documents_in_text(
        "See https://a.org/x.epub", "https://a.org/post/1", "https://media.a.org/scan.jpg"
    )
    assert [d.file_name for d in documents] == ["x.epub", "scan.jpg"]


def test_rows_read_words_first_and_alike_rows_are_told_apart() -> None:
    documents = documents_in_html(
        '<a href="https://a.org/one.pdf">Download</a> '
        '<a href="https://b.org/two.pdf">Download</a> '
        '<a href="https://www.c.org/Map.png">https://www.c.org/Map.png</a> '
        '<a href="https://c.org/Guide.pdf">Guide.pdf</a>'
    )
    assert row_labels(documents) == [
        "Download (a.org)",
        "Download (b.org)",
        "Map.png on c.org",
        "Guide.pdf on c.org",
    ]
    same = documents_in_html(
        '<a href="https://a.org/one.pdf">Download</a> <a href="https://a.org/two.pdf">Download</a>'
    )
    assert row_labels(same) == ["Download (a.org), one.pdf", "Download (a.org), two.pdf"]


def test_the_list_label_carries_its_count_and_none_says_where() -> None:
    assert list_label(3, "this post") == "Linked documents in this post, 3:"
    assert none_sentence("this episode's show notes", verb="link") == (
        "This episode's show notes link no documents Scribe for Documents can convert."
    )


# -------------------------------------------------------------------- headings


def test_html_headings_and_rows_words_first() -> None:
    headings = html_headings(
        "<h1>Notes</h1><p>x</p><h2>Methods <em>used</em></h2><h2>Results</h2>"
        "<h3>Detail</h3><h2>Results</h2>"
    )
    assert headings == [
        Heading(1, "Notes"),
        Heading(2, "Methods used"),
        Heading(2, "Results"),
        Heading(3, "Detail"),
        Heading(2, "Results"),
    ]
    assert heading_rows(headings) == [
        START,
        "Notes, heading level 1",
        "Methods used, heading level 2",
        "Results, heading level 2, first",
        "Detail, heading level 3",
        "Results, heading level 2, second",
    ]
    assert heading_path(headings, 3) == ["Notes", "Results", "Detail"]
    assert heading_path(headings, 9) == []


def test_word_headings_are_read_from_their_styles(tmp_path: Path) -> None:
    import zipfile

    body = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        '<w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:r><w:t>Notes</w:t></w:r></w:p>'
        "<w:p><w:r><w:t>Plain text</w:t></w:r></w:p>"
        '<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>Meth</w:t></w:r>'
        "<w:r><w:t>ods</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    path = tmp_path / "Notes.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", body)
    assert document_headings(path) == [Heading(1, "Notes"), Heading(2, "Methods")]
    assert document_headings(tmp_path / "missing.docx") == []
    assert document_headings(tmp_path / "Notes.pdf") == []


# ------------------------------------------------------------- chapter markers

_NCX = """<?xml version="1.0"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><navMap>
  <navPoint id="n1" playOrder="1"><navLabel><text>Notes</text></navLabel>
    <content src="book.smil#s1"/></navPoint>
  <navPoint id="n2" playOrder="2"><navLabel><text>Methods</text></navLabel>
    <content src="book.smil#s2"/></navPoint>
</navMap></ncx>"""

_SMIL = """<?xml version="1.0"?>
<smil xmlns="http://www.w3.org/2001/SMIL20/"><body><seq>
  <par id="s1"><audio src="book.mp3" clipBegin="npt=0s"/></par>
  <par id="s2"><audio src="{second}" clipBegin="npt=30s"/></par>
</seq></body></smil>"""


def _daisy(folder: Path, second: str = "book.mp3") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "book.smil").write_text(_SMIL.format(second=second), encoding="utf-8")
    (folder / "book.mp3").write_bytes(b"ID3")
    ncx = folder / "book.ncx"
    ncx.write_text(_NCX, encoding="utf-8")
    return ncx


def test_daisy_headings_become_chapters_of_its_one_audio_file(tmp_path: Path) -> None:
    from quill.core.scribe.narration import daisy_chapters

    chapters, files = daisy_chapters(_daisy(tmp_path / "one"))
    assert files == ["book.mp3"]
    assert [(c.title, c.start_ms, c.end_ms) for c in chapters] == [
        ("Notes", 0, 30_000),
        ("Methods", 30_000, 30_000),
    ]
    chapters, files = daisy_chapters(_daisy(tmp_path / "two", second="book2.mp3"))
    assert chapters == [] and files == ["book.mp3", "book2.mp3"]


def _fake_book(monkeypatch: pytest.MonkeyPatch, total_ms: int, daisy_ms: int) -> list:
    from quill.core.speech import book_file, ffmpeg
    from quill.core.speech.chapters import Chapter

    saved: list = []

    class Book:
        def __init__(self, path: Path) -> None:
            self.path = path
            self.total_ms = total_ms
            self.chapters = [Chapter(index=0, title="x", start_ms=0, end_ms=total_ms)]

    monkeypatch.setattr(book_file, "read_book", Book)
    monkeypatch.setattr(book_file, "save_mp3_book", saved.append)
    monkeypatch.setattr(ffmpeg, "probe_duration_ms", lambda _path, **_k: daisy_ms)
    return saved


def test_markers_are_written_when_the_daisy_audio_matches_the_mp3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.scribe.narration import mark_narration

    saved = _fake_book(monkeypatch, total_ms=60_000, daisy_ms=60_500)
    markers = mark_narration(tmp_path / "Notes.mp3", _daisy(tmp_path / "d"))
    assert markers.count == 2 and markers.phrase == "with 2 chapter markers"
    assert [(c.title, c.end_ms) for c in saved[0].chapters] == [
        ("Notes", 30_000),
        ("Methods", 60_000),
    ]


def test_no_markers_say_why_in_the_one_sentence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.scribe.narration import mark_narration

    saved = _fake_book(monkeypatch, total_ms=60_000, daisy_ms=90_000)
    markers = mark_narration(tmp_path / "Notes.mp3", _daisy(tmp_path / "d"))
    assert saved == []
    assert (
        markers.phrase == "with no chapter markers, because the DAISY timings do not match the MP3"
    )
    # Split audio whose lengths cannot be read: no markers rather than wrong ones.
    several = mark_narration(tmp_path / "Notes.mp3", _daisy(tmp_path / "e", second="b2.mp3"))
    assert (
        several.phrase == "with no chapter markers, because the DAISY timings do not match the MP3"
    )


_SPLIT_NCX = """<?xml version="1.0"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><navMap>
  <navPoint id="n0" playOrder="1"><navLabel><text>Notes</text></navLabel>
    <content src="0.smil#t"/></navPoint>
  <navPoint id="n1" playOrder="2"><navLabel><text>Intro</text></navLabel>
    <content src="0.smil#a"/></navPoint>
  <navPoint id="n2" playOrder="3"><navLabel><text>Methods</text></navLabel>
    <content src="1.smil#c"/></navPoint>
  <navPoint id="n3" playOrder="4"><navLabel><text>Results</text></navLabel>
    <content src="1.smil#e"/></navPoint>
</navMap></ncx>"""

_SPLIT_SMILS = {
    "0.smil": [("t", "0.mp3", "0:00:02.000"), ("a", "1.mp3", "0:00:10.000"),
               ("b", "2.mp3", "0:00:20.000")],
    "1.smil": [("c", "3.mp3", "0:00:05.000"), ("d", "4.mp3", "0:00:15.000"),
               ("e", "5.mp3", "0:00:08.000")],
}  # fmt: skip


def _split_daisy(folder: Path, *, spine: tuple[str, ...] = ("0.smil", "1.smil")) -> Path:
    """Scribe's shape: one MP3 per paragraph, a spoken title first (F3)."""
    folder.mkdir(parents=True, exist_ok=True)
    for name, clips in _SPLIT_SMILS.items():
        pars = "".join(
            f'<par id="{par}"><audio src="{src}" clipBegin="0:00:00.000" clipEnd="{end}"/></par>'
            for par, src, end in clips
        )
        smil = f'<smil xmlns="http://www.w3.org/2001/SMIL20/"><body><seq>{pars}</seq></body></smil>'
        (folder / name).write_text(smil, encoding="utf-8")
    items = "".join(f'<item id="s{i}" href="{n}" media-type="application/smil"/>'
                    for i, n in enumerate(spine))  # fmt: skip
    refs = "".join(f'<itemref idref="s{i}"/>' for i in range(len(spine)))
    (folder / "dtb.opf").write_text(
        f'<package xmlns="http://openebook.org/namespaces/oeb-package/1.0/"><manifest>{items}'
        f"</manifest><spine>{refs}</spine></package>",
        encoding="utf-8",
    )
    ncx = folder / "dtb.ncx"
    ncx.write_text(_SPLIT_NCX, encoding="utf-8")
    return ncx


@pytest.mark.parametrize(
    ("total_ms", "title_ms"),
    [(58_000, 0), (60_000, 2_000)],  # the MP3 without the spoken title, then with it
)
def test_split_daisy_audio_places_a_marker_at_each_section_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, total_ms: int, title_ms: int
) -> None:
    """Each heading starts after every audio file before its own (F3 follow-up)."""
    from quill.core.scribe.narration import mark_narration

    saved = _fake_book(monkeypatch, total_ms=total_ms, daisy_ms=0)
    markers = mark_narration(tmp_path / "Notes.mp3", _split_daisy(tmp_path / "d"))
    # Without the spoken title, the title and Intro start together: one chapter,
    # named by Intro. With it, the title is a chapter of its own.
    title = [("Notes", 0, title_ms)] if title_ms else []
    assert markers.count == len(title) + 3
    assert [(c.title, c.start_ms, c.end_ms) for c in saved[0].chapters] == [
        *title,
        ("Intro", title_ms, title_ms + 30_000),
        ("Methods", title_ms + 30_000, title_ms + 50_000),
        ("Results", title_ms + 50_000, total_ms),
    ]


def test_split_daisy_audio_that_does_not_add_up_writes_no_markers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.scribe.narration import mark_narration

    saved = _fake_book(monkeypatch, total_ms=90_000, daisy_ms=0)
    markers = mark_narration(tmp_path / "Notes.mp3", _split_daisy(tmp_path / "d"))
    assert saved == []
    assert (
        markers.phrase == "with no chapter markers, because the DAISY timings do not match the MP3"
    )


def test_split_daisy_audio_follows_the_spine_not_the_file_names(tmp_path: Path) -> None:
    from quill.core.scribe.narration import _timed_headings, split_offsets

    ncx = _split_daisy(tmp_path / "d", spine=("1.smil", "0.smil"))
    offsets = split_offsets(ncx, _timed_headings(ncx), 60_000)
    assert offsets is not None
    assert offsets["3.mp3"] == 0 and offsets["0.mp3"] == 28_000


def test_the_result_sentence_carries_the_note_before_the_folder() -> None:
    job = q.Job(
        file_name="Notes.pdf",
        outputs={"mp3": "C:/x/Notes.mp3"},
        formats=["mp3"],
        folder="C:/x",
    )
    text = say.result_sentence(job, app_name="QUILL Studio", note="with 12 chapter markers")
    assert text == (
        "Scribe for Documents made Notes.mp3 in C:/x, with 12 chapter markers. "
        "Open it from Scribe Conversions."
    )


# -------------------------------------------------------------------- F1 help


@pytest.mark.parametrize(
    "module",
    [
        "quill.core.media.surface_help",
        "quill.core.converter_surface_help",
        "quill.core.audio_studio.surface_help",
        "quill.core.podcasts.surface_help",
        "quill.apps.beacon.surface_help",
    ],
)
def test_every_app_catalogue_explains_the_scribe_windows(module: str) -> None:
    import importlib

    from quill.core.scribe.surface_help import SCRIBE_PURPOSES

    catalogue = importlib.import_module(module)
    for title in (*SCRIBE_PURPOSES, "Password for Notes.pdf"):
        assert catalogue.is_known_title(title), (module, title)
    assert "Scribe" in catalogue.purpose_for_title("Scribe Conversions")


# -------------------------------------------------------------- Beacon places


@pytest.fixture
def beacon_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("QUILLBEACON_DATA", str(tmp_path / "beacon"))
    from quill.apps.beacon.scribe_places import open_store

    store = open_store()
    yield store
    store.close()


def test_a_place_in_a_scribe_result_remembers_the_document_and_heading(
    beacon_store, tmp_path: Path
) -> None:
    from quill.apps.beacon.scribe_places import document_id_of, save_place, scribe_places

    path = tmp_path / "Notes.docx"
    path.write_bytes(b"docx")
    beacon = save_place(
        beacon_store,
        document_id="doc-1",
        title="Notes",
        path=path,
        format_id="docx",
        heading_path=["Notes", "Methods"],
    )
    assert beacon.title == "Notes, Methods" and beacon.capture_source == "scribe"
    places = scribe_places(beacon_store)
    assert [p.beacon_id for p in places] == [beacon.beacon_id]
    assert places[0].locations[0].heading_path == ["Notes", "Methods"]
    resource = beacon_store.get_resource(places[0].resource_id)
    assert document_id_of(resource) == "doc-1" and resource.primary_uri == str(path)
    # A second place in the same document shares its resource.
    again = save_place(
        beacon_store, document_id="doc-1", title="Notes", path=path, format_id="docx"
    )
    assert again.resource_id == beacon.resource_id and again.title == "Notes"


def test_the_library_becomes_places_once_each(beacon_store, tmp_path: Path) -> None:
    from quill.apps.beacon.scribe_places import add_library, scribe_places

    path = tmp_path / "A.docx"
    path.write_bytes(b"docx")
    added, already = add_library(
        beacon_store, [("a", "A"), ("b", "B"), ("", "nothing")], {"a": ("docx", path)}
    )
    assert (added, already) == (2, 0)
    assert add_library(beacon_store, [("a", "A"), ("c", "C")], {}) == (1, 1)
    titles = sorted(p.title for p in scribe_places(beacon_store))
    assert titles == ["A", "B", "C"]
