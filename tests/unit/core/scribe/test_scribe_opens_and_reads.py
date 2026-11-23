"""Every returned file opens and reads in every QUILL product that receives it.

Priority 1 of the Scribe test plan (scribe-test-plan.md, 5.3): for each
format Scribe returns, the apps that receive it, and what "readable" means
there. One table, :data:`RECEIVERS`; one test, parametrised over every file
of that format in the folder ``QUILL_SCRIBE_CORPUS`` names -- Pneuma's
corpus or a live run's folder (``python -m quill.tools.scribe_check``).

Each reader is the one the app itself uses: QUILL's ``read_open_document``
(the editor, the braille view, EPUB reading), QUILL Lite's
``open_prepare.prepare``, Beacon's ``document_headings``, the Media
Player's ``open_daisy_zip`` and ``read_book``, Studio's ``daisy_chapters``,
and the browser Next Step's ``browser_page``. "Readable" is about shape, not
quality: the text and headings are there, BRF pages and cell width match the
file, DAISY has chapters with their audio, the MP3 has its length -- never
whether Scribe converted well.

Each case records ``scribe_app`` and ``scribe_format`` as junit properties,
which the live run's summary reads to say pass and fail per app and format.
"""

from __future__ import annotations

import re
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from quill.tools.scribe_live.facts import brf_facts, docx_facts, mp3_facts
from quill.tools.scribe_live.layout import FOLDERS
from tests.unit.core.scribe import corpus

pytestmark = corpus.needs_corpus

Reader = Callable[[Path, Path], None]


def _quill_text(path: Path) -> tuple[str, object, dict]:
    from quill.io.open_read import read_open_document

    doc, book = read_open_document(path, path.suffix.lower())
    meta = dict(getattr(doc, "source_metadata", {}) or {})
    if meta.get("extraction_pack_missing"):
        pytest.skip("needs the optional PDF and Office text extraction pack")
    return doc.text, book, meta


def quill_editor(path: Path, _tmp: Path) -> None:
    text, book, _meta = _quill_text(path)
    assert text.strip(), "QUILL opened it empty"
    suffix = path.suffix.lower()
    if suffix == ".html":
        raw = path.read_text(encoding="utf-8", errors="replace")
        wanted = len(re.findall(r"<h[1-6]\b", raw, re.IGNORECASE))
        assert len(re.findall(r"<h[1-6]\b", text, re.IGNORECASE)) == wanted, "headings lost"
    if suffix == ".docx" and docx_facts(path).get("headings"):
        assert re.search(r"^#{1,6} ", text, re.MULTILINE), "the Word headings did not arrive"
    if suffix == ".epub":
        assert getattr(book, "chapters", None), "the EPUB opened with no chapters"


def quill_braille(path: Path, _tmp: Path) -> None:
    raw = path.read_bytes()
    text, _book, meta = _quill_text(path)
    facts = brf_facts(raw)
    assert meta["source_kind"] == "brf"
    assert meta["brf_cell_width"] == facts["max_cells"], "opened at the wrong cell width"
    assert meta["brf_form_feed_count"] == facts["form_feeds"], "pages lost"
    assert text.encode("utf-8") == raw, "bytes were changed or dropped (F4)"


def lite_editor(path: Path, _tmp: Path) -> None:
    from quill.core.lite.open_prepare import prepare
    from quill.core.pdf_open import ENGINE_UNAVAILABLE

    mode = "rich" if path.suffix.lower() == ".docx" else "plain"
    prepared = prepare(path, mode)
    if prepared.pdf is not None and prepared.pdf.engine == ENGINE_UNAVAILABLE:
        pytest.skip("needs the optional PDF and Office text extraction pack")
    assert prepared.text.strip() or prepared.rtf, "QUILL Lite opened it empty"


def beacon_places(path: Path, _tmp: Path) -> None:
    from quill.core.scribe.headings import document_headings

    if path.suffix.lower() == ".zip":
        pytest.skip("Beacon reads headings from a web page or Word file, not a zip")
    raw = path.read_bytes()
    has = re.search(rb"<h[1-6]\b", raw, re.IGNORECASE) if path.suffix == ".html" else True
    if path.suffix.lower() == ".docx":
        has = bool(docx_facts(path).get("headings"))
    headings = document_headings(path)
    assert bool(headings) == bool(has), "Beacon found no headings to save a place at"


def browser_next_step(path: Path, _tmp: Path) -> None:
    import zipfile

    from quill.core.scribe.results import browser_page, missing_pictures

    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            assert any(n.lower().endswith((".html", ".htm")) for n in archive.namelist())
        return
    assert browser_page({"offline_html": str(path)}) == path, "Next Steps cannot open it"
    assert missing_pictures(path) == 0, "the offline page is missing pictures"


def kept_for_kindle(path: Path, _tmp: Path) -> None:
    assert path.read_bytes()[60:68] == b"BOOKMOBI", "not a MOBI book"


def player_audio(path: Path, _tmp: Path) -> None:
    from quill.core.speech.book_file import BookReadError, read_book

    try:
        book = read_book(path)
    except BookReadError as error:
        pytest.skip(f"this computer cannot read MP3 lengths: {error}")
    assert book.total_ms > 0, "the MP3 has no length"
    seconds = mp3_facts(path).get("seconds")
    if seconds:
        assert abs(book.total_ms / 1000 - seconds) <= 1.0


def _unpacked(path: Path, tmp: Path) -> Path:
    from quill.apps.player_scribe import open_daisy_zip

    copy = tmp / path.name
    shutil.copyfile(path, copy)
    ncx = open_daisy_zip(copy)
    assert ncx is not None and ncx.name.lower().endswith(".ncx"), "no dtb.ncx to open"
    assert copy.with_suffix("") in ncx.parents, "unpacked outside its own folder"
    return ncx


def player_daisy(path: Path, tmp: Path) -> None:
    from quill.core.media import parse_ncx, resolve_heading_times

    ncx = _unpacked(path, tmp)
    headings = parse_ncx(ncx.read_text(encoding="utf-8"))
    assert headings, "the book has no chapters to move between"

    def smil(name: str) -> str | None:
        found = ncx.parent / name
        return found.read_text(encoding="utf-8") if found.is_file() else None

    timed = resolve_heading_times(headings, smil)
    assert all(h.time_ms is not None and (ncx.parent / h.audio_src).is_file() for h in timed)


def studio_daisy(path: Path, tmp: Path) -> None:
    from quill.core.scribe.narration import daisy_chapters

    chapters, files = daisy_chapters(_unpacked(path, tmp))
    assert chapters or files, "Studio found neither chapters nor audio in the book"


#: format -> the QUILL products that receive it, and what readable means there.
RECEIVERS: dict[str, tuple[tuple[str, Reader], ...]] = {
    "html": (("QUILL", quill_editor), ("QUILL Lite", lite_editor), ("Beacon", beacon_places)),
    "offline_html": (("Browser, from Next Steps", browser_next_step), ("Beacon", beacon_places)),
    "docx": (("QUILL", quill_editor), ("QUILL Lite", lite_editor), ("Beacon", beacon_places)),
    "pdf": (("QUILL", quill_editor), ("QUILL Lite", lite_editor)),
    "epub": (("QUILL", quill_editor),),
    "mobi": (("Kept for a Kindle", kept_for_kindle),),
    "brf": (("QUILL braille view", quill_braille), ("QUILL Lite", lite_editor)),
    "mp3": (("Media Player", player_audio), ("Studio", player_audio)),
    "daisy": (("Media Player", player_daisy), ("Studio", studio_daisy)),
}


def _cases() -> list[object]:
    folder = corpus.full_corpus()
    if folder is None:
        return []
    cases = []
    for format_id, receivers in RECEIVERS.items():
        place = folder / FOLDERS[format_id]
        files = sorted(p for p in place.iterdir() if p.is_file()) if place.is_dir() else []
        for path in files:
            for app, reader in receivers:
                cases.append(pytest.param(format_id, app, reader, path, id=f"{app}-{path.name}"))
    return cases


def test_every_format_has_a_receiver() -> None:
    from quill.core.scribe.model import FORMAT_IDS

    assert set(RECEIVERS) == set(FORMAT_IDS)


@pytest.mark.parametrize(("format_id", "app", "reader", "path"), _cases())
def test_it_opens_and_reads(
    format_id: str,
    app: str,
    reader: Reader,
    path: Path,
    tmp_path: Path,
    record_property: Callable[[str, object], None],
) -> None:
    record_property("scribe_app", app)
    record_property("scribe_format", format_id)
    reader(path, tmp_path)
