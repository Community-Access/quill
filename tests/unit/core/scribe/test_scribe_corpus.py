"""Scribe for Documents on real Scribe output: Pneuma's test corpus, offline.

The fake server hands back the corpus files byte for byte, and every flow runs
on them: the family queue, the download, how a result is named (our stem,
never the document's title, F6) and with which extension (F1), where it is
saved, the result sentence, Open Result's order, and what each format opens
as -- the HTML and its pictures (F2), Word's styles, the tagged PDF's text,
the EPUB 2 with ``dc:language`` ``C`` (F5), MOBI, the BRF quirks (F4), and,
with ``QUILL_SCRIBE_CORPUS`` set, the MP3 and the DAISY book (F3). The
per-document settings carry exactly the README's names, with Scribe's own
email off (F8).
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pytest

from quill.core.scribe import queue as q
from quill.core.scribe import sentences as say
from quill.core.scribe.library import Library, saved_name
from quill.core.scribe.model import (
    FORMAT_IDS,
    ScribeSettings,
    extension_for_bytes,
    ordered_for_conversion,
)
from quill.core.scribe.options import ScribeOptions
from quill.core.scribe.results import (
    MOBI_NOTE,
    OFFLINE_PICTURES_NOTE,
    PICTURES_NOTE,
    ZIPPED_PICTURES_NOTE,
    browser_page,
    default_action,
    missing_pictures,
    open_order,
    opened_phrase,
    pictures_note,
    result_notes,
)
from quill.core.scribe.runner import QueueService, default_channel_opener
from tests.unit.core.scribe import corpus
from tests.unit.core.scribe.fake_scribe import BASE, FakeClock, FakeScribe, StaticTokens

pytestmark = corpus.needs_corpus

#: The scan's title as Scribe read it: a library stamp, then the real title.
STAMPED_TITLE = ".E. Touch HOW TEACHERS MAY USE FARMERS' BULLETIN 876"


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


def _run(
    tmp_path: Path,
    stem: str,
    formats: list[str],
    *,
    names: dict[str, str] | None = None,
    settings: ScribeSettings | None = None,
) -> tuple[FakeScribe, q.Job, list]:
    """Upload *stem*'s source, convert to *formats*, download the corpus bytes."""
    server = FakeScribe()
    server.serve_files(corpus.outputs(stem, formats), names)
    events: list = []
    service = _service(server, tmp_path, events)
    source = tmp_path / f"{stem}.pdf"
    source.write_bytes(b"%PDF-1.4 the source")
    job = q.Job(
        file_name=source.name,
        source_path=str(source),
        title=source.stem,
        formats=formats,
        settings=(settings or ScribeSettings()).to_dict(),
    )
    service.queue.add([job])
    assert service.tick()
    return server, service.queue.jobs()[0], events


# ----------------------------------------------------- F1: the offline page


def test_the_offline_page_that_arrives_as_html_is_saved_as_html(tmp_path: Path) -> None:
    # The fake server, like an older Scribe, calls it Notes.zip.
    _server, job, _events = _run(tmp_path, corpus.GARDEN, ["offline_html"])
    saved = Path(job.outputs["offline_html"])
    assert saved.suffix == ".html" and saved.name == f"{corpus.GARDEN}-offline.html"
    assert saved.read_bytes() == corpus.output("offline_html", corpus.GARDEN).read_bytes()


def test_an_offline_page_that_arrives_as_a_zip_is_saved_as_a_zip(tmp_path: Path) -> None:
    zipped = tmp_path / "page.zip"
    with zipfile.ZipFile(zipped, "w") as archive:
        archive.writestr("index.html", "<html><img src='a.png' alt='A'></html>")
        archive.writestr("a.png", b"\x89PNG")
    server = FakeScribe()
    server.serve_files({"offline_html": zipped})
    events: list = []
    service = _service(server, tmp_path, events)
    source = tmp_path / "Notes.pdf"
    source.write_bytes(b"%PDF")
    service.queue.add([q.Job(file_name="Notes.pdf", source_path=str(source), title="Notes",
                             formats=["offline_html"])])  # fmt: skip
    service.tick()
    saved = Path(service.queue.jobs()[0].outputs["offline_html"])
    assert saved.name == "Notes-offline.zip" and zipfile.is_zipfile(saved)


def test_the_extension_comes_from_the_bytes() -> None:
    assert extension_for_bytes("offline_html", b"<!DOCTYPE html>") == ".html"
    assert extension_for_bytes("offline_html", b"PK\x03\x04rest") == ".zip"
    assert extension_for_bytes("offline_html", b"") == ".html"
    assert extension_for_bytes("daisy", b"PK\x03\x04") == ".zip"
    assert extension_for_bytes("brf", b"PK\x03\x04") == ".brf"  # only the offline page varies
    assert extension_for_bytes("newformat", b"", ".abc") == ".abc"


# ------------------------------------------------ F6: our names, not titles


def test_names_and_the_sentence_use_our_stem_never_the_documents_title(tmp_path: Path) -> None:
    formats = ["html", "docx", "epub", "mobi", "brf", "offline_html"]
    names = {f: f"{STAMPED_TITLE}.{f}" for f in formats}  # a server naming by title
    _server, job, _events = _run(tmp_path, corpus.SCAN, formats, names=names)
    stems = {Path(path).stem.removesuffix("-offline") for path in job.outputs.values()}
    assert stems == {corpus.SCAN}  # and no "(2)": the offline page has its own name
    assert Path(job.folder).name == corpus.SCAN
    sentence = say.result_sentence(job, app_name="QUILL")
    assert "Touch" not in sentence and f"{corpus.SCAN}.docx" in sentence
    assert say.start_sentence(job) == (
        f"Scribe for Documents: sending {corpus.SCAN}.pdf, for Accessible HTML, Word, EPUB, "
        "Kindle (MOBI), Braille (BRF) and Web page for offline reading."
    )
    assert Library(tmp_path / "scribe" / "library.json").title_for(job.document_id) == corpus.SCAN


def test_without_a_stem_the_servers_name_is_made_safe(tmp_path: Path) -> None:
    downloaded = tmp_path / "part"
    downloaded.write_bytes(b"<html></html>")
    assert saved_name("offline_html", downloaded, server_name="Notes.zip") == "Notes-offline.html"
    assert saved_name("docx", downloaded, server_name='a/b:"c".docx') == "a_b__c_.docx"
    assert saved_name("pdf", downloaded, fallback="doc1") == "doc1.pdf"
    assert saved_name("docx", downloaded, stem="Report 1.2") == "Report 1.2.docx"


# ------------------------------------------------- every format, real bytes


def test_every_format_replays_through_the_queue_on_real_bytes(tmp_path: Path) -> None:
    at_hand = list(corpus.outputs(corpus.GARDEN))  # mp3 and daisy with the full corpus
    server, job, events = _run(tmp_path, corpus.GARDEN, at_hand)
    assert job.state == q.DONE and set(job.outputs) == set(at_hand)
    for format_id, path in job.outputs.items():
        saved = Path(path)
        assert saved.parent == tmp_path / "out" / corpus.GARDEN
        assert saved.read_bytes() == corpus.output(format_id, corpus.GARDEN).read_bytes()
    extensions = {f: Path(p).suffix for f, p in job.outputs.items()}
    assert extensions["offline_html"] == ".html" and extensions["brf"] == ".brf"
    # One conversion at a time, in Scribe's dependency order.
    started = [
        frame[4]["format"]
        for sock in server.sockets
        for frame in sock.sent
        if frame[3] == "start_conversion"
    ]
    assert started == ordered_for_conversion(at_hand)
    kinds = [kind for kind, _job in events]
    assert kinds.count("started") == 1 and kinds.count("done") == 1
    recorded = Library(tmp_path / "scribe" / "library.json").files_for(job.document_id)
    assert {f for f, _p in recorded} == set(at_hand)
    sentence = say.result_sentence(job, app_name="QUILL", opened="Word is open in QUILL")
    assert sentence.count("Scribe for Documents made") == 1
    assert f" in {say.friendly_folder(job.folder)}" in sentence


# --------------------------------------------- F8: the per-document settings


def _readme_setting_names() -> list[str]:
    text = (corpus.require_full() / "README.md").read_text(encoding="utf-8")
    block = text.split("The defaults on the day were:", 1)[1].split("Variants", 1)[0]
    return re.findall(r"\b([a-z_]+):", block)


def test_the_upload_carries_exactly_the_readmes_setting_names(tmp_path: Path) -> None:
    names = _readme_setting_names()
    assert len(names) == 11 and "notify_when_complete" in names
    chosen = ScribeSettings(
        language="en", tts_gender="female", braille_translation_table="en-us-g2.ctb"
    )
    server, job, _events = _run(tmp_path, corpus.GARDEN, ["docx"], settings=chosen)
    sent = server.documents[job.document_id].upload_settings
    assert sorted(sent) == sorted(names)
    assert sent["notify_when_complete"] == "false"


def test_scribes_own_email_is_never_inherited_from_the_account() -> None:
    account = ScribeSettings(notify_when_complete=True, tts_rate=1.5)  # Scribe's default: on
    options = ScribeOptions()
    start = options.starting_settings(account, "QUILL")
    assert start.notify_when_complete is False and start.tts_rate == 1.5
    # Checked by the person, it is remembered as their choice and sent.
    options.remember_choice("QUILL", ScribeSettings(notify_when_complete=True), account)
    assert options.starting_settings(account, "QUILL").notify_when_complete is True


def test_a_watch_folder_file_sends_no_email_either(tmp_path: Path) -> None:
    server = FakeScribe()
    server.account_defaults["notify_when_complete"] = True
    server.serve_files(corpus.outputs(corpus.GARDEN, ["docx"]))
    service = _service(server, tmp_path, [])
    source = tmp_path / "Notes.docx"
    source.write_bytes(b"PK docx")
    service.queue.add([q.Job(file_name="Notes.docx", source_path=str(source), title="Notes",
                             formats=["docx"], open_as="watch")])  # fmt: skip
    service.tick()
    doc = next(iter(server.documents.values()))
    assert doc.upload_settings["notify_when_complete"] == "false"


def test_the_variants_settings_reach_the_upload() -> None:
    large = dict(ScribeSettings(large_print=True, braille_cells_per_line=32).to_upload_fields())
    assert large["document[settings][large_print]"] == "true"
    assert large["document[settings][braille_cells_per_line]"] == "32"
    maths = dict(ScribeSettings(math=True).to_upload_fields())
    assert maths["document[settings][math]"] == "true"


# ------------------------------------------------- HTML and its pictures (F2)


@pytest.mark.parametrize("stem", corpus.SOURCES)
def test_the_html_opens_with_its_structure_and_alt_text(stem: str) -> None:
    from quill.io.open_read import read_open_document

    path = corpus.output("html", stem)
    doc, _book = read_open_document(path, ".html")
    facts = corpus.validation("html", stem)
    text, raw = doc.text, path.read_text(encoding="utf-8")
    assert len(re.findall(r"<h[1-6]\b", text)) == facts["headings"]
    assert len(re.findall(r"<table\b", text)) == facts["tables"]
    # Lists, table headers and links: all kept, as many as the file has.
    for pattern in (r"<(?:ul|ol)\b", r"<li\b", r"<th\b", r"<a\b[^>]*href"):
        assert len(re.findall(pattern, text)) == len(re.findall(pattern, raw))
    assert bool(re.findall(r"<(?:ul|ol)\b", text)) == bool(facts["lists"])
    assert bool(re.findall(r"<a\b[^>]*href", text)) == bool(facts["links"])
    images = re.findall(r"<img\b[^>]*>", text)
    assert len(images) == facts["imgs"] and all(re.search(r'\balt="[^"]+', i) for i in images)
    assert missing_pictures(path) == facts["external_img_refs"] > 0


@pytest.mark.parametrize("stem", corpus.SOURCES)
def test_the_offline_page_has_every_picture_inside(stem: str) -> None:
    path = corpus.output("offline_html", stem)
    facts = corpus.validation("offline_html", stem)
    assert missing_pictures(path) == 0
    text = path.read_text(encoding="utf-8")
    assert text.count('src="data:') == facts["data_uri_imgs"] == facts["imgs"]


def test_the_accessible_html_stays_the_html_and_the_offline_page_is_saved(
    tmp_path: Path,
) -> None:
    html, offline = tmp_path / "N.html", tmp_path / "N-offline.html"
    outputs = {"html": str(html), "offline_html": str(offline), "brf": str(tmp_path / "N.brf")}
    assert open_order(outputs) == [
        ("html", html),
        ("brf", tmp_path / "N.brf"),
        ("offline_html", offline),
    ]
    assert default_action("offline_html") == "save"
    assert browser_page(outputs) is None  # not there yet
    offline.write_text("<html></html>")
    assert browser_page(outputs) == offline
    assert browser_page({"offline_html": str(tmp_path / "N-offline.zip")}) is None


def test_the_sentence_says_once_where_the_pictures_are(tmp_path: Path) -> None:
    html = tmp_path / "N.html"
    html.write_bytes(corpus.output("html", corpus.NIST).read_bytes())
    alone = pictures_note({"html": str(html)})
    assert (
        alone
        == PICTURES_NOTE
        == (
            "The accessible HTML came without its pictures; Download Formats in My Scribe "
            "Documents can add the Web page for offline reading, which has them."
        )
    )
    offline = tmp_path / "N-offline.html"
    offline.write_text("<html></html>")
    both = pictures_note({"html": str(html), "offline_html": str(offline)})
    assert (
        both
        == OFFLINE_PICTURES_NOTE
        == (
            "Its pictures are in the Web page for offline reading; Next Steps opens that in "
            "your browser."
        )
    )
    # A zipped offline page has no browser Next Step, so the note must not promise one.
    zipped = pictures_note({"html": str(html), "offline_html": str(tmp_path / "N.zip")})
    assert (
        zipped
        == ZIPPED_PICTURES_NOTE
        == (
            "Its pictures are in the Web page for offline reading, saved as a zip; "
            "Open Folder in Scribe Conversions shows it."
        )
    )
    job = q.Job(file_name="N.pdf", formats=["html"], outputs={"html": str(html)})
    sentence = say.result_sentence(job, app_name="QUILL", opened="x is open", after=alone)
    assert sentence.count(alone) == 1 and sentence.endswith(alone)
    # A picture beside it is not missing; a web or embedded picture never is.
    page = tmp_path / "P.html"
    page.write_text('<img src="a.png"><img src="data:image/png;base64,AA"><img src="https://x/y">')
    (tmp_path / "a.png").write_bytes(b"\x89PNG")
    assert missing_pictures(page) == 0
    assert pictures_note({"html": str(page)}) == ""


# --------------------------------------------------------- Word and the PDF


@pytest.mark.parametrize("stem", [*corpus.SOURCES, f"{corpus.NIST}-large-print"])
def test_word_opens_with_its_headings_and_table_header(stem: str) -> None:
    from quill.io.open_read import read_open_document

    base = stem.removesuffix("-large-print")
    doc, _book = read_open_document(corpus.output("docx", stem), ".docx")
    headings = re.findall(r"^#{1,6} ", doc.text, re.MULTILINE)
    facts = corpus.validation("docx", base if stem == base else stem)
    assert len(headings) == facts["headings"]
    if facts["tables"]:
        assert re.search(r"^\| .+ \|\n\| (?:--- \| )*--- \|$", doc.text, re.MULTILINE)
    assert "[Image:" in doc.text  # the picture, with its alt text


def test_the_word_garden_table_keeps_its_header_row() -> None:
    from quill.io.open_read import read_open_document

    doc, _book = read_open_document(corpus.output("docx", corpus.GARDEN), ".docx")
    assert "| Day | Morning | Evening |\n| --- | --- | --- |" in doc.text
    assert "[Image: Rainfall chart]" in doc.text


@pytest.mark.parametrize("stem", [corpus.NIST, corpus.GARDEN, corpus.MATH])
def test_the_tagged_pdf_text_is_readable(stem: str) -> None:
    from quill.io.open_read import read_open_document

    doc, _book = read_open_document(corpus.output("pdf", stem), ".pdf")
    if doc.source_metadata.get("extraction_pack_missing"):
        pytest.skip("needs the optional PDF and Office text extraction pack")
    assert len(doc.text) > 1000


def test_the_scans_ocr_layer_is_readable() -> None:
    from quill.io.open_read import read_open_document

    folder = corpus.require_full()
    doc, _book = read_open_document(folder / "pdf" / f"{corpus.SCAN}.pdf", ".pdf")
    if doc.source_metadata.get("extraction_pack_missing"):
        pytest.skip("needs the optional PDF and Office text extraction pack")
    assert "BUTTER ON THE FARM" in doc.text and "SHINN" in doc.text


# ------------------------------------------------------------ EPUB (F5), MOBI


@pytest.mark.parametrize("stem", [*corpus.SOURCES, f"{corpus.MATH}-math-on"])
def test_the_epub_2_imports_with_its_own_language_never_c(stem: str) -> None:
    from quill.io.open_read import read_open_document

    path = corpus.output("epub", stem)
    with zipfile.ZipFile(path) as archive:
        opf = next(n for n in archive.namelist() if n.endswith(".opf"))
        assert "<dc:language>C</dc:language>" in archive.read(opf).decode()
    doc, book = read_open_document(path, ".epub")
    assert book.chapters and doc.text.startswith("# EPUB: ")
    assert book.language == "en" == doc.source_metadata["language"]


def test_a_language_is_only_kept_when_it_is_one() -> None:
    from quill.core.epub import book_language

    assert book_language("C", ['<html lang="fr">']) == "fr"
    assert book_language("en-GB", ['<html lang="fr">']) == "en-GB"
    assert book_language("C", ["<html>"]) == ""
    assert book_language("und", ['<html xml:lang="de">']) == "de"


def test_mobi_opens_in_the_editor_and_says_where_else_it_goes(tmp_path: Path) -> None:
    _server, job, _events = _run(tmp_path, corpus.MATH, ["mobi"])
    saved = Path(job.outputs["mobi"])
    assert saved.read_bytes()[60:68] == b"BOOKMOBI" and saved.suffix == ".mobi"
    # QUILL and QUILL Lite read a Kindle book (2026-11-23): Open Result opens it.
    assert default_action("mobi") == "editor"
    assert opened_phrase("mobi", "QUILL") == "The Kindle book is open in QUILL"
    sentence = say.result_sentence(
        job,
        app_name="QUILL",
        opened=opened_phrase("mobi", "QUILL"),
        after=result_notes(job.outputs),
    )
    assert sentence == (
        f"Scribe for Documents made {corpus.MATH}.mobi in {say.friendly_folder(job.folder)}. "
        f"The Kindle book is open in QUILL. {MOBI_NOTE}"
    )
    assert MOBI_NOTE == (
        "A Kindle (MOBI) book is for older Kindles: copy it to the Kindle's documents folder "
        "over USB. Amazon's Send to Kindle takes the EPUB instead."
    )


def test_every_format_id_has_a_corpus_file() -> None:
    assert set(corpus.outputs(corpus.GARDEN)) | {"mp3", "daisy"} == set(FORMAT_IDS)
