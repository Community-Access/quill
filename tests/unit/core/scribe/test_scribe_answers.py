"""Pneuma's answers of 2026-11-21, against the fake server (PRD 3.1-3.6, 7.4, 8.3, 10).

The approved batch exception (strictly one file after another, a failure not
stopping the rest), the 23 input types and the 500 MB limit, the family's
pace under Scribe's 10 actions a minute and the minute's wait after
``rate_limited``, the website's setting ranges, per-document settings sent
whole at upload, organization credits, free repeat formats, DAISY 3 zips
unpacked to their ``.ncx``, the privacy wording, and per-user storage.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from quill.core.scribe import errors as e
from quill.core.scribe import inputs
from quill.core.scribe import queue as q
from quill.core.scribe import sentences as say
from quill.core.scribe.consent import ABOUT_TEXT, PRIVACY_LINES, consent_text, pages_text
from quill.core.scribe.model import (
    Account,
    DocumentSummary,
    Output,
    ScribeSettings,
)
from quill.core.scribe.options import ScribeOptions
from quill.core.scribe.results import daisy_entry
from quill.core.scribe.runner import QueueService, default_channel_opener
from tests.unit.core.scribe.fake_scribe import BASE, FakeClock, FakeScribe, StaticTokens


@pytest.fixture
def server() -> FakeScribe:
    return FakeScribe()


def _service(server: FakeScribe, tmp_path: Path, events: list) -> tuple[QueueService, FakeClock]:
    from quill.core.scribe.client import ScribeClient

    clock = FakeClock()
    server.clock = clock
    service = QueueService(
        "QUILL",
        queue=q.FamilyQueue(tmp_path / "scribe", now=clock),
        client_factory=lambda: ScribeClient(
            StaticTokens(server), base_url=BASE, transport=server.transport, sleep=clock.sleep
        ),
        channel_opener=default_channel_opener(server.connector),
        download_root=lambda: str(tmp_path / "out"),
        listener=lambda kind, job: events.append((kind, job.file_name if job else "")),
        sleep=clock.sleep,
        clock=clock,
    )
    return service, clock


def _job(tmp_path: Path, name: str = "Notes.pdf", formats: tuple = ("docx",), **kw) -> q.Job:
    source = tmp_path / name
    source.write_bytes(b"%PDF fake")
    return q.Job(file_name=name, source_path=str(source), formats=list(formats), **kw)


def _run_all(service: QueueService) -> None:
    for _ in range(10):
        if not service.tick():
            break


# ------------------------------------------------------------ batch (7.4)


def test_a_batch_goes_strictly_one_after_another(server: FakeScribe, tmp_path: Path) -> None:
    events: list = []
    service, _clock = _service(server, tmp_path, events)
    service.queue.add([_job(tmp_path, "a.pdf"), _job(tmp_path, "b.pdf")])
    _run_all(service)
    assert [j.state for j in service.queue.jobs()] == [q.DONE, q.DONE]
    order = [(kind, name) for kind, name in events if kind in ("started", "done")]
    assert order == [
        ("started", "a.pdf"),
        ("done", "a.pdf"),
        ("started", "b.pdf"),
        ("done", "b.pdf"),
    ]
    # b's upload only after a's last download
    paths = [r[1] for r in server.requests]
    first_download = max(i for i, url in enumerate(paths) if "doc1" in url)
    second_upload = [
        i
        for i, r in enumerate(server.requests)
        if r[0] == "POST" and r[1].endswith("/api/documents")
    ][1]
    assert second_upload > first_download


def test_a_failed_file_does_not_stop_the_rest_and_the_last_sentence_says_both(
    server: FakeScribe, tmp_path: Path
) -> None:
    events: list = []
    service, _clock = _service(server, tmp_path, events)
    page = tmp_path / "Page.html"
    page.write_text("<p>web</p>")
    bad = q.Job(file_name="Page.html", source_path=str(page), formats=["docx"])
    service.queue.add([bad, _job(tmp_path, "b.pdf")])
    _run_all(service)
    jobs = service.queue.jobs()
    assert [j.state for j in jobs] == [q.FAILED, q.DONE]
    assert jobs[0].error_code == "QUILL-SCRIBE-NOTDOC"
    assert not [r for r in server.requests if b"Page.html" in r[3]]  # never sent
    assert say.batch_sentence(service.queue.batch_jobs(jobs[0].batch)) == (
        "Scribe for Documents finished 2 files. Made: b.pdf. Not made: Page.html; "
        "Scribe Conversions has the details."
    )


# ------------------------------------------------------------ inputs (3.1)


def test_exactly_the_23_types_and_never_html() -> None:
    assert len(inputs.ACCEPTED_TYPES) == 23
    for name in ("a.pdf", "a.JPG", "a.jp2", "a.djvu", "a.dcx", "a.pcx", "a.bmp", "a.mobi"):
        assert inputs.is_accepted(name), name
    for name in ("a.html", "a.htm", "a.md", "a.zip"):
        assert not inputs.is_accepted(name), name


def test_refusals_before_upload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    page = tmp_path / "Site.htm"
    page.write_text("x")
    code, sentence = inputs.refusal(page)
    assert code == "QUILL-SCRIBE-NOTDOC"
    assert sentence == (
        "Site.htm: Scribe for Documents does not take web pages. Save it as Word or PDF first."
    )
    other = tmp_path / "notes.md"
    other.write_text("x")
    assert inputs.refusal(other)[1] == (
        "Scribe for Documents cannot convert notes.md: it takes PDF, pictures, Office, "
        "OpenDocument, text, EPUB and MOBI files, not web pages."
    )
    big = tmp_path / "Big.pdf"
    big.write_bytes(b"x" * 2048)
    monkeypatch.setattr(inputs, "MAX_UPLOAD_BYTES", 1024)
    assert inputs.refusal(big) == (
        "QUILL-SCRIBE-TOOBIG",
        "Big.pdf is 2 KB. Scribe for Documents takes files up to 500 MB.",
    )
    assert inputs.url_refusal("https://example.com/news/story.html").startswith("story.html:")
    assert inputs.url_refusal("https://example.com/files/report.pdf") == ""


def test_too_big_is_checked_by_the_runner_too_and_nothing_is_sent(
    server: FakeScribe, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(inputs, "MAX_UPLOAD_BYTES", 4)
    events: list = []
    service, _clock = _service(server, tmp_path, events)
    service.queue.add([_job(tmp_path)])
    service.tick()
    job = service.queue.jobs()[0]
    assert job.error_code == "QUILL-SCRIBE-TOOBIG" and server.requests == []


def test_the_servers_not_a_document_gets_its_own_code_and_sentence(
    server: FakeScribe, tmp_path: Path
) -> None:
    server.not_a_document = True
    events: list = []
    service, _clock = _service(server, tmp_path, events)
    service.queue.add([q.Job(file_name="article", source_url="https://x.test/article")])
    service.tick()
    job = service.queue.jobs()[0]
    assert job.error_code == "QUILL-SCRIBE-NOTDOC"
    assert job.message == inputs.not_a_document_sentence("article")
    assert isinstance(e.error_from_server("not_a_document"), e.ScribeNotDocumentError)


# -------------------------------------------------------------- pace (3.5)


def test_the_family_keeps_under_eight_actions_a_minute(server: FakeScribe, tmp_path: Path) -> None:
    server.rate_limit = 10
    events: list = []
    service, _clock = _service(server, tmp_path, events)
    formats = ("html", "docx", "pdf", "epub", "mobi", "offline_html", "brf", "mp3", "daisy")
    service.queue.add([_job(tmp_path, formats=formats), _job(tmp_path, "b.pdf", formats=formats)])
    _run_all(service)
    assert [j.state for j in service.queue.jobs()] == [q.DONE, q.DONE]
    assert server.rate_limited_count == 0
    times = sorted(server.actions)
    assert len(times) == 20  # 2 uploads + 18 start_conversion
    for index in range(len(times) - 8):
        assert times[index + 8] - times[index] >= 59.9  # never 9 in a rolling minute


def test_the_pace_is_shared_by_every_app(tmp_path: Path) -> None:
    clock = FakeClock()
    first = q.FamilyQueue(tmp_path / "scribe", now=clock)
    second = q.FamilyQueue(tmp_path / "scribe", now=clock)
    for _ in range(4):
        assert first.reserve_action() == 0.0
        assert second.reserve_action() == 0.0
    assert first.reserve_action() > 0 and second.reserve_action() > 0


def test_rate_limited_waits_a_minute_and_says_so_once(server: FakeScribe, tmp_path: Path) -> None:
    server.rate_limited_once = True
    events: list = []
    service, clock = _service(server, tmp_path, events)
    service.queue.add([_job(tmp_path)])
    before = clock.now
    service.tick()
    assert service.queue.jobs()[0].state == q.DONE
    assert [k for k, _ in events].count("busy") == 1
    assert clock.now - before >= 60.0
    assert say.busy_sentence("QUILL Lite") == (
        "Scribe for Documents asked QUILL Lite to slow down; trying again in a minute."
    )


def test_rate_limited_on_upload_waits_and_retries(server: FakeScribe, tmp_path: Path) -> None:
    server.rate_limit = 0  # the person used the website: no room this minute
    events: list = []
    service, clock = _service(server, tmp_path, events)
    service.queue.add([_job(tmp_path)])

    def lift(seconds: float) -> None:
        clock.now += max(seconds, 0.01)
        if clock.now > 1030:
            server.rate_limit = None

    service._sleep = lift
    service.tick()
    assert service.queue.jobs()[0].state == q.DONE
    assert "busy" in [k for k, _ in events]


# ---------------------------------------------------------- settings (3.3)


def test_settings_are_clamped_to_the_websites_ranges() -> None:
    wild = ScribeSettings.from_mapping({
        "tts_rate": 9,
        "braille_cells_per_line": 5,
        "braille_lines_per_page": 99,
    })
    assert (wild.tts_rate, wild.braille_cells_per_line, wild.braille_lines_per_page) == (
        4.0,
        20,
        30,
    )
    assert ScribeSettings.from_mapping({"tts_rate": 1.4}).tts_rate == 1.5
    assert ScribeSettings.from_mapping({"braille_cells_per_line": 50}).braille_cells_per_line == 42


def test_the_full_set_goes_with_the_upload_and_nothing_is_patched(
    server: FakeScribe, tmp_path: Path
) -> None:
    events: list = []
    service, _clock = _service(server, tmp_path, events)
    chosen = ScribeSettings(language="fr", math=True, large_print=True, tts_rate=1.5)
    service.queue.add([_job(tmp_path, settings=chosen.to_dict())])
    service.tick()
    doc = next(iter(server.documents.values()))
    assert doc.upload_settings["language"] == "fr"
    assert doc.upload_settings["math"] == "true" and doc.upload_settings["large_print"] == "true"
    assert doc.upload_settings["tts_rate"] == "1.5"
    assert doc.upload_settings["add_image_descriptions"] == "true"
    assert server.settings_patches == [] and server.default_patches == []


def test_a_reused_document_patches_only_what_its_upload_did_not_fix(
    server: FakeScribe, tmp_path: Path
) -> None:
    doc = server.add_document(outputs={"html": "complete"})
    events: list = []
    service, _clock = _service(server, tmp_path, events)
    chosen = ScribeSettings(language="fr", tts_rate=2.0)
    service.queue.add([
        q.Job(
            title="Notes",
            document_id=doc.id,
            reuse=True,
            formats=["mp3"],
            settings=chosen.to_dict(),
        )
    ])
    service.tick()
    ((patched_id, patch),) = server.settings_patches
    assert patched_id == doc.id and patch["tts_rate"] == 2.0
    assert not {"language", "math", "large_print", "add_image_descriptions"} & set(patch)


def test_account_defaults_change_only_when_asked(server: FakeScribe, tmp_path: Path) -> None:
    events: list = []
    service, _clock = _service(server, tmp_path, events)
    chosen = ScribeSettings(tts_rate=2.0).to_dict()
    service.queue.add([_job(tmp_path, settings=chosen, save_as_defaults=True)])
    service.tick()
    assert server.default_patches and server.default_patches[0]["tts_rate"] == 2.0


def test_starting_values_are_the_account_defaults_then_this_apps_choices() -> None:
    options = ScribeOptions()
    account = ScribeSettings(language="de", tts_rate=1.5)
    assert options.starting_settings(account, "QUILL").language == "de"
    options.remember_choice("QUILL", ScribeSettings(language="de", tts_rate=2.0), account)
    assert options.last_settings == {"QUILL": {"tts_rate": 2.0}}
    later = options.starting_settings(ScribeSettings(language="es", tts_rate=1.5), "QUILL")
    assert (later.language, later.tts_rate) == ("es", 2.0)  # the website's change shows
    assert options.starting_settings(account, "QUILL Lite").tts_rate == 1.5


# -------------------------------------------------------- pages (3.4, 3.6)


def test_organization_credits_are_named(server: FakeScribe) -> None:
    from quill.core.scribe.client import ScribeClient

    server.organization_name = "Acme Library"
    server.pages_remaining = 1240
    account = ScribeClient(
        StaticTokens(server), base_url=BASE, transport=server.transport
    ).account()
    assert account.pages_phrase() == "1,240 pages left, using credits from Acme Library."
    assert Account(pages_remaining=3).pages_phrase() == "3 pages left."
    assert pages_text(34, 1240, organization="Acme Library") == (
        "This uses about 34 of the 1,240 pages left in Acme Library's credits."
    )


def test_a_second_format_uses_no_pages() -> None:
    doc = DocumentSummary(id="d", outputs=(Output(format="html", stage="complete"),))
    assert doc.charged
    preview = DocumentSummary(
        id="d", outputs=(Output(format="html_stream", stage="complete", is_preview=True),)
    )
    assert not preview.charged
    assert pages_text(0, 50, free=True) == (
        "No pages used: this document is already in your Scribe account. You have 50 pages left."
    )


# -------------------------------------------------------------- DAISY (8.3)


def test_a_daisy_zip_is_unpacked_and_its_ncx_opened(server: FakeScribe, tmp_path: Path) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("book/speechgen.ncx", "<ncx/>")
        archive.writestr("book/speechgen.opf", "<package/>")
        archive.writestr("book/part1.mp3", b"ID3")
    server.file_bytes["daisy"] = buffer.getvalue()
    events: list = []
    service, _clock = _service(server, tmp_path, events)
    service.queue.add([_job(tmp_path, formats=("daisy",))])
    service.tick()
    saved = Path(service.queue.jobs()[0].outputs["daisy"])
    unpacked = saved.with_suffix("")
    assert (unpacked / "book" / "speechgen.ncx").exists()  # unpacked at download
    assert daisy_entry(saved) == unpacked / "book" / "speechgen.ncx"


# ----------------------------------------------------- privacy (7.3, 10.1)


def test_the_consent_says_where_and_that_documents_never_train_ai(tmp_path: Path) -> None:
    source = tmp_path / "Notes.pdf"
    source.write_bytes(b"x" * 100)
    text = consent_text([source], first_upload=True)
    assert (
        "will be sent to Scribe for Documents (Pneuma Solutions) and converted in the "
        "United States" in text
    )
    assert "(30 days unless you changed it)" in text
    assert "Pneuma does not use documents to train AI." in text
    joined = "\n".join(PRIVACY_LINES) + ABOUT_TEXT
    for words in ("AWS in Ohio", "Azure (East US)", "Mathpix", "Gemini through OpenRouter"):
        assert words in joined
    assert "Pneuma is reviewing its picture-description provider" in joined
    assert "72" not in joined and "hour" not in joined
    assert inputs.size_words(600 * 1024 * 1024) == "600 MB"  # never "600.0"


def test_several_files_are_said_to_go_one_after_another(tmp_path: Path) -> None:
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    a.write_bytes(b"x")
    b.write_bytes(b"x")
    assert "2 files, sent one after another without asking again" in consent_text([a, b])


def test_reusing_a_document_says_which_settings_are_fixed() -> None:
    text = consent_text([], existing_title="Notes")
    assert "No file is sent." in text
    assert (
        "The language, picture descriptions, mathematics and large print settings were fixed "
        "when Notes was uploaded" in text
    )


# ------------------------------------------------------- per user (10.2.7)


def test_scribe_storage_is_this_windows_users_own(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.core.paths as paths

    shared = Path(tmp_path.anchor) / "shared-quill-data-for-test"
    monkeypatch.setattr(paths, "app_data_dir", lambda: shared)
    monkeypatch.setenv("USERNAME", "pat")
    assert q.queue_dir() == shared / "scribe" / "pat"
    from quill.core.scribe.library import library_path
    from quill.core.scribe.options import options_path

    assert library_path().parent == options_path().parent == q.queue_dir()
    inside = Path.home() / "AppData" / "Roaming" / "QUILL"
    monkeypatch.setattr(paths, "app_data_dir", lambda: inside)
    assert q.queue_dir() == inside / "scribe"


# ------------------------------------------------- the issued client ID


def test_the_issued_client_id_switches_scribe_on_in_release_builds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quill.core.paths as paths
    from quill.core import scribe

    assert len(scribe.CLIENT_ID) == 64  # Pneuma's public PKCE client ID, 2026-11-21
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setenv("QUILL_SCRIBE_CLIENT_ID", "dev-client")
    monkeypatch.setattr(paths, "_DEV_BUILD", False)
    assert scribe.client_id() == scribe.CLIENT_ID  # a release build ignores the override
    assert scribe.unavailable_reason() == ""
    monkeypatch.setattr(paths, "_DEV_BUILD", True)
    assert scribe.client_id() == "dev-client"  # the development override still works
    monkeypatch.setattr(scribe, "CLIENT_ID", "")
    monkeypatch.delenv("QUILL_SCRIBE_CLIENT_ID")
    assert "not available in this build of QUILL yet" in scribe.unavailable_reason()
