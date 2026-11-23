"""The F1-F8 quirks of Pneuma's corpus, on our own tiny files, in CI.

The corpus replay (``test_scribe_corpus*.py``) needs ``QUILL_SCRIBE_CORPUS``
and so never runs on GitHub. These tests rebuild each quirk from files we
write ourselves (:mod:`own_fixtures`) and drive the same code paths: the
fake server and the family queue (F1, F6, F8), the readers behind Open
(F2, F4, F5, F7), the DAISY unpacking and navigation (F3), the options
(F8) and the speaker (GATE-13). Nothing here reads the corpus.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pytest

from quill.core.scribe import queue as q
from quill.core.scribe import sentences as say
from quill.core.scribe.model import ScribeSettings
from quill.core.scribe.options import ScribeOptions, quill_base
from quill.core.scribe.results import (
    OFFLINE_PICTURES_NOTE,
    PICTURES_NOTE,
    ZIPPED_PICTURES_NOTE,
    browser_page,
    daisy_entry,
    missing_pictures,
    pictures_note,
)
from quill.core.scribe.runner import QueueService, default_channel_opener
from quill.io.open_read import read_open_document
from tests.unit.core.scribe import own_fixtures as own
from tests.unit.core.scribe.fake_scribe import BASE, FakeClock, FakeScribe, StaticTokens


def _service(server: FakeScribe, tmp_path: Path, events: list) -> QueueService:
    from quill.core.scribe.client import ScribeClient

    clock = FakeClock()
    server.clock = clock
    return QueueService(
        "QUILL",
        queue=q.FamilyQueue(tmp_path / "scribe", now=clock),
        client_factory=lambda: ScribeClient(
            StaticTokens(server), base_url=BASE, transport=server.transport, sleep=lambda _s: None
        ),
        channel_opener=default_channel_opener(server.connector),
        download_root=lambda: str(tmp_path / "out"),
        listener=lambda kind, job: events.append((kind, job)),
        sleep=clock.sleep,
        clock=clock,
    )


def _replay(
    tmp_path: Path,
    files: dict[str, Path],
    *,
    stem: str = "Garden",
    names: dict[str, str] | None = None,
    open_as: str = "",
    account: dict | None = None,
) -> tuple[FakeScribe, q.Job, list]:
    """Upload *stem*.docx, convert to the formats of *files*, download those bytes."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    server = FakeScribe()
    server.serve_files(files, names)
    if account is not None:
        server.account_defaults.update(account)
    events: list = []
    service = _service(server, tmp_path, events)
    source = tmp_path / f"{stem}.docx"
    source.write_bytes(b"PK our own docx")
    job = q.Job(
        file_name=source.name,
        source_path=str(source),
        title=stem,
        formats=list(files),
        settings={} if open_as == "watch" else ScribeSettings().to_dict(),
        open_as=open_as,
    )
    service.queue.add([job])
    assert service.tick()
    return server, service.queue.jobs()[0], events


@pytest.fixture
def made(tmp_path: Path) -> Path:
    folder = tmp_path / "made"
    folder.mkdir()
    return folder


# ------------------------------------------------- F1: the offline web page


def test_f1_an_offline_page_sent_as_one_html_file_is_saved_as_html(
    tmp_path: Path, made: Path
) -> None:
    page = own.offline_page(made / "page.bin")
    # The server still calls it .zip, as an older Scribe did.
    _server, job, _ = _replay(tmp_path, {"offline_html": page}, names={"offline_html": "G.zip"})
    saved = Path(job.outputs["offline_html"])
    assert saved.name == "Garden-offline.html" and saved.read_bytes() == page.read_bytes()
    assert missing_pictures(saved) == 0
    assert browser_page(job.outputs) == saved


def test_f1_an_offline_page_sent_as_a_zip_is_saved_as_a_zip(tmp_path: Path, made: Path) -> None:
    zipped = own.offline_zip(made / "page.bin")
    _server, job, _ = _replay(tmp_path, {"offline_html": zipped})
    saved = Path(job.outputs["offline_html"])
    assert saved.name == "Garden-offline.zip" and zipfile.is_zipfile(saved)
    assert browser_page(job.outputs) is None  # a zip is no page for the browser


# --------------------------------------------- F2: the HTML's missing pictures


def test_f2_the_accessible_html_opens_with_its_structure_and_says_where_pictures_are(
    tmp_path: Path, made: Path
) -> None:
    html = own.accessible_html(made / "Garden.html")
    doc, _book = read_open_document(html, ".html")
    for pattern in (r"<h1\b", r"<h2\b", r"<li\b", r"<th\b", r"<a\b[^>]*href", r"<table\b"):
        assert re.search(pattern, doc.text), pattern
    assert re.search(r'<img\b[^>]*alt="Rainfall chart"', doc.text)
    assert missing_pictures(html) == 1
    assert pictures_note({"html": str(html)}) == PICTURES_NOTE
    offline = own.offline_page(made / "Garden-offline.html")
    both = {"html": str(html), "offline_html": str(offline)}
    assert pictures_note(both) == OFFLINE_PICTURES_NOTE
    zipped = own.offline_zip(made / "Garden-offline.zip")
    assert pictures_note({"html": str(html), "offline_html": str(zipped)}) == ZIPPED_PICTURES_NOTE
    job = q.Job(file_name="Garden.docx", formats=["html"], outputs={"html": str(html)})
    sentence = say.result_sentence(job, app_name="QUILL", opened="x is open", after=PICTURES_NOTE)
    assert sentence.count(PICTURES_NOTE) == 1 and sentence.endswith(PICTURES_NOTE)


# ------------------------------------------------------------- F3: DAISY 3


def test_f3_a_daisy_book_with_missing_pictures_and_a_2002_label_opens(made: Path) -> None:
    from quill.core.media.daisy import parse_ncx, resolve_heading_times

    book = own.daisy3_zip(made / "Garden.zip")
    ncx = daisy_entry(book)
    assert ncx is not None and ncx.name == "dtb.ncx"
    assert book.with_suffix("") in ncx.parents  # unpacked into its own folder
    assert "Z39.86-2002" in (ncx.parent / "dtb.opf").read_text(encoding="utf-8")
    assert not (ncx.parent / "pic1.png").exists()  # named by dtbook.xml, not in the zip
    headings = parse_ncx(ncx.read_text(encoding="utf-8"))
    assert [h.title for h in headings] == list(own.DAISY_SECTIONS)

    def smil(name: str) -> str | None:
        found = ncx.parent / name
        return found.read_text(encoding="utf-8") if found.is_file() else None

    timed = resolve_heading_times(headings, smil)
    assert all(h.time_ms == 0 and (ncx.parent / h.audio_src).is_file() for h in timed)
    assert len({h.audio_src for h in timed}) == 3  # split audio, one MP3 a section


def test_f3_the_runner_unpacks_a_downloaded_daisy_zip(tmp_path: Path, made: Path) -> None:
    book = own.daisy3_zip(made / "book.bin")
    _server, job, _ = _replay(tmp_path, {"daisy": book})
    saved = Path(job.outputs["daisy"])
    assert saved.name == "Garden.zip"
    assert (saved.with_suffix("") / "garden_handbook" / "dtb.ncx").is_file()


# --------------------------------------------------------------- F4: BRF


def test_f4_a_brf_with_a_tab_utf8_bytes_and_a_trailing_form_feed_opens_whole(
    made: Path,
) -> None:
    from quill.core.brf_validator import KIND_NON_BRF_ASCII, validate_brf

    path = own.brf_with_quirks(made / "Garden.brf")
    doc, _book = read_open_document(path, ".brf")
    meta = doc.source_metadata
    assert meta["source_kind"] == "brf"
    assert doc.text.encode("utf-8") == own.BRF_BYTES  # nothing dropped, byte for byte
    assert meta["brf_tab_count"] == 1
    assert meta["brf_form_feed_count"] == 2
    flagged = [w for w in validate_brf(doc.text) if w.kind == KIND_NON_BRF_ASCII]
    assert meta["brf_unshown_count"] == len(flagged) >= 2  # the tab and the accent
    assert any("U+00B4" in w.message for w in flagged)


def test_f4_form_feeds_end_the_pages_and_the_last_one_makes_no_empty_page(made: Path) -> None:
    from quill.core.brf_document import BRFDocument
    from quill.core.brf_page_map import build_page_map

    doc, _book = read_open_document(own.brf_with_quirks(made / "G.brf"), ".brf")
    text = doc.text
    pages = build_page_map(BRFDocument.from_text_and_suffix(text, "brf"), mode="form_feed").pages
    with_text = [p for p in pages if text[p.start_offset : p.end_offset].strip()]
    assert len(with_text) == 2 and all(p.has_form_feed for p in with_text)


def test_f4_scribes_braille_code_is_named_ebae() -> None:
    from quill.core.braille_detect import CANDIDATE_TABLES

    label = dict(CANDIDATE_TABLES)["en-us-g2"]
    assert "EBAE" in label and "UEB" not in label


# ------------------------------------------------------------ F5: EPUB 2


def test_f5_an_epub_2_with_language_c_imports_in_its_own_language(made: Path) -> None:
    path = own.epub2_language_c(made / "Garden.epub")
    doc, book = read_open_document(path, ".epub")
    assert book.chapters and doc.text.startswith("# EPUB: ")
    assert "Water early" in doc.text
    assert book.language == "en" == doc.source_metadata["language"]


# --------------------------------------------------- F6: our names, not titles


def test_f6_files_and_the_sentence_use_our_stem_not_the_title_scribe_read(
    tmp_path: Path, made: Path
) -> None:
    files = {
        "html": own.accessible_html(made / "a"),
        "brf": own.brf_with_quirks(made / "b"),
        "offline_html": own.offline_page(made / "c"),
    }
    names = {f: f"{own.STAMPED_TITLE}.{f}" for f in files}  # a server naming by title
    _server, job, _ = _replay(tmp_path, files, names=names)
    assert {Path(p).name for p in job.outputs.values()} == {
        "Garden.html",
        "Garden.brf",
        "Garden-offline.html",
    }
    assert Path(job.folder).name == "Garden"
    sentence = say.result_sentence(job, app_name="QUILL")
    assert "Stamp" not in sentence and "Garden.html" in sentence


# -------------------------------------------------------- F7: mathematics


def test_f7_an_equation_comes_as_a_picture_with_its_alt_text_kept(made: Path) -> None:
    path = own.math_html(made / "Rows.html")
    doc, _book = read_open_document(path, ".html")
    assert "<math" not in path.read_text(encoding="utf-8")
    assert own.EQUATION_ALT in doc.text


def test_f7_the_math_setting_still_reaches_the_upload(tmp_path: Path, made: Path) -> None:
    server = FakeScribe()
    server.serve_files({"html": own.math_html(made / "m")})
    service = _service(server, tmp_path, [])
    source = tmp_path / "Rows.pdf"
    source.write_bytes(b"%PDF-1.4 ours")
    maths = ScribeSettings(math=True).to_dict()
    job = q.Job(file_name="Rows.pdf", source_path=str(source), title="Rows", formats=["html"])
    job.settings = maths
    service.queue.add([job])
    service.tick()
    doc = next(iter(server.documents.values()))
    assert doc.upload_settings["math"] == "true"


def test_f7_the_guide_promises_no_mathml() -> None:
    repo = Path(__file__).resolve().parents[4]
    guide = repo / "docs" / "user guide" / "quill-guide" / "quill-guide-19-scribe-for-documents.md"
    text = re.sub(r"\s+", " ", guide.read_text(encoding="utf-8"))
    assert "**Mathematics (beta)**" in text
    assert "does not make MathML in any format" in text


# ------------------------------------------------- F8: Scribe's own email


def test_f8_the_email_is_never_inherited_from_the_account_defaults() -> None:
    account = ScribeSettings(notify_when_complete=True, tts_rate=1.5)
    assert quill_base(account)["notify_when_complete"] is False
    options = ScribeOptions()
    start = options.starting_settings(account, "QUILL")
    assert start.notify_when_complete is False and start.tts_rate == 1.5
    # Checked by the person, it is their choice, remembered and sent.
    options.remember_choice("QUILL", ScribeSettings(notify_when_complete=True), account)
    assert options.starting_settings(account, "QUILL").notify_when_complete is True


def test_f8_a_convert_upload_and_a_watch_folder_upload_both_send_no_email(
    tmp_path: Path, made: Path
) -> None:
    files = {"docx": made / "w.docx"}
    files["docx"].write_bytes(b"PK ours")
    server, job, _ = _replay(tmp_path / "convert", files)
    assert server.documents[job.document_id].upload_settings["notify_when_complete"] == "false"
    watched, wjob, _ = _replay(
        tmp_path / "watch", files, open_as="watch", account={"notify_when_complete": True}
    )
    sent = watched.documents[wjob.document_id].upload_settings
    assert sent["notify_when_complete"] == "false"


# --------------------------------------------- GATE-13: each stage once


def _job(state: str, fmt: str, stage: str, progress: float) -> q.Job:
    return q.Job(id="j", file_name="Garden.docx", state=state, format=fmt, stage=stage,
                 progress=progress)  # fmt: skip


def test_gate13_each_stage_is_said_once_per_job() -> None:
    speaker = say.Speaker(speak_stages="always")
    steps = [
        _job(q.UPLOADING, "", "", 0.0),
        _job(q.CONVERTING, "html", "queue", 0.05),
        _job(q.CONVERTING, "html", "convert", 0.1),
        _job(q.CONVERTING, "docx", "queue", 0.12),  # the same words again: silent
        _job(q.CONVERTING, "docx", "convert", 0.15),  # also the same words
    ]
    said = [speaker.on_change(job, app_in_front=True) for job in steps]
    spoken = [s for s in said if s]
    assert len(spoken) == len(set(spoken)) == 3
    assert said[3] == said[4] == ""


def test_gate13_the_same_change_again_says_nothing() -> None:
    speaker = say.Speaker(speak_stages="always")
    job = _job(q.CONVERTING, "html", "convert", 0.1)
    assert speaker.on_change(job, app_in_front=True)
    # The row is refreshed in place while focused: the same state, nothing new to say.
    for _ in range(3):
        assert speaker.on_change(job, app_in_front=True) == ""


def test_gate13_stages_wait_for_the_app_in_front_unless_asked_always() -> None:
    behind = say.Speaker(speak_stages="front")
    job = _job(q.CONVERTING, "html", "convert", 0.1)
    assert behind.on_change(job, app_in_front=False) == ""
    assert say.Speaker(speak_stages="never").on_change(job, app_in_front=True) == ""
