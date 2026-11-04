"""Listening versions, Name Embeds, documents as pages, and the family apps' flows."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.speech.provider import TranscriptionResult, TranscriptionSegment
from quill.core.wordpress import local as lc
from quill.core.wordpress.episode import Chapter, Episode
from quill.core.wordpress.listen_engines import Converted, ListenEngines
from quill.ui import wordpress_family as fam
from quill.ui import wordpress_listen_dialogs as ldlg

API = "/wp-json/wp/v2"
MP3_URL = "https://radio.example/wp-content/uploads/spring-fair-listen.mp3"


def media(item_id: int, url: str, mime: str, title: str, size: int = 0) -> dict:
    return {
        "id": item_id,
        "title": {"raw": title},
        "mime_type": mime,
        "source_url": url,
        "media_details": {"filesize": size},
        "post": 0,
    }


class Engines:
    def __init__(self) -> None:
        self.spoken: list[tuple[str, str]] = []
        self.converted: list[str] = []
        self.transcribed: list[Path] = []
        self.convert_answer = Converted("# Annual report\n\nWe grew.\n", pages=2)
        self.ocr_answer = Converted("Scanned words.\n", pages=1)

    def bundle(self) -> ListenEngines:
        def speak(title: str, html: str, out: Path) -> int:
            self.spoken.append((title, html))
            out.write_bytes(b"ID3MP3")
            return 6 * 60_000

        def convert(path: Path) -> Converted:
            self.converted.append("text")
            return self.convert_answer

        def convert_ocr(path: Path) -> Converted:
            self.converted.append("ocr")
            return self.ocr_answer

        def transcribe(path: Path) -> TranscriptionResult:
            self.transcribed.append(path)
            return TranscriptionResult(
                full_text="Hello.", segments=(TranscriptionSegment(0, 1, "Hello."),)
            )

        return ListenEngines(
            transcribe=transcribe, speak=speak, convert=convert, convert_ocr=convert_ocr
        )


@pytest.fixture
def engines(wp) -> Engines:
    fake = Engines()
    wp._listen_engines = fake.bundle()
    return fake


def open_document(wp, text: str, *, text_format: str = "html", islands: dict | None = None):
    copy = lc.WorkingCopy(
        site_id="radio",
        kind="post",
        local_id=lc.new_local_id(),
        title="Spring Fair",
        text=text,
        text_format=text_format,
        properties={"islands": islands or {}},
    )
    wp.host.open_path(wp.local.write_document(copy))


def working(wp) -> lc.WorkingCopy:
    return wp.local.copy_for_path(wp.host.current_path())


PARAGRAPH = "<!-- wp:paragraph --><p>The fair is on Saturday.</p><!-- /wp:paragraph -->"


def serve_upload(wp_site, item: dict) -> None:
    wp_site.on("GET", f"{API}/media", [])
    wp_site.on("POST", f"{API}/media", item)
    wp_site.on("POST", f"{API}/media/{item['id']}", item)


# --------------------------------------------------------------------------- #
# Make a Listening Version


def test_an_empty_document_has_nothing_to_read(wp, engines) -> None:
    open_document(wp, "")
    wp.cmd_listening_version()
    assert "There is nothing to read yet" in wp.host.said
    assert engines.spoken == []


def test_listening_version_outside_a_document_says_so(wp, engines) -> None:
    wp.cmd_listening_version()
    assert "This is not a WordPress document" in wp.host.said


def test_listening_version_is_recorded_uploaded_and_put_at_the_top(wp, wp_site, engines):
    open_document(wp, PARAGRAPH)
    serve_upload(wp_site, media(40, MP3_URL, "audio/mpeg", "Listen"))
    wp.cmd_listening_version()
    assert engines.spoken[0][0] == "Spring Fair"
    assert "The fair is on Saturday." in engines.spoken[0][1]
    upload = wp_site.sent("POST", f"{API}/media")[0]
    assert upload.data == b"ID3MP3"
    assert upload.get_header("Content-type") == "audio/mpeg"
    assert wp.host.text.startswith('<!-- wp:audio {"id":40,"className":"quill-listening-version"}')
    assert "Listen to this post (6 minutes)" in wp.host.text
    assert wp.host.text.endswith(PARAGRAPH)
    assert working(wp).properties["listening_version"]["media_id"] == 40
    assert wp.host.announced[-1] == (
        "Listening version uploaded to Community Radio, 6 minutes. It is at the top of the "
        "post, labelled Listen to this post (6 minutes)."
    )


def test_asking_again_when_up_to_date_offers_to_remake_and_cancel_keeps_it(
    wp, wp_site, wp_dialogs, engines
) -> None:
    open_document(wp, PARAGRAPH)
    serve_upload(wp_site, media(40, MP3_URL, "audio/mpeg", "Listen"))
    wp.cmd_listening_version()
    before = wp.host.text
    wp.cmd_listening_version()
    assert "up to date" in wp_dialogs.asked("confirm")[0]["message"]
    assert wp.host.text == before
    assert len(engines.spoken) == 1


def test_a_changed_post_is_out_of_date_and_the_new_recording_replaces_the_old(
    wp, wp_site, wp_dialogs, engines
) -> None:
    open_document(wp, PARAGRAPH)
    serve_upload(wp_site, media(40, MP3_URL, "audio/mpeg", "Listen"))
    wp.cmd_listening_version()
    wp.host.text = wp.host.text.replace("Saturday", "Sunday")
    wp_dialogs.answer("confirm", True)
    wp.cmd_listening_version()
    assert "out of date" in wp_dialogs.asked("confirm")[0]["message"]
    assert wp.host.text.count("wp:audio {") == 1
    assert "Sunday" in engines.spoken[1][1]
    assert "quill-listening-version" not in engines.spoken[1][1]


def test_a_markdown_listening_version_is_an_island_at_the_top(wp, wp_site, engines) -> None:
    open_document(wp, "The fair is on Saturday.\n", text_format="markdown")
    serve_upload(wp_site, media(40, MP3_URL, "audio/mpeg", "Listen"))
    wp.cmd_listening_version()
    assert wp.host.text.startswith("::: block core/audio listen listen-1\n\nThe fair")
    assert "quill-listening-version" in working(wp).properties["islands"]["listen-1"]


# --------------------------------------------------------------------------- #
# Name Embeds

OEMBED = {"title": "Spring Fair 2026", "author_name": "Community Radio", "provider_name": "YouTube"}
EMBED = (
    '<!-- wp:embed {"url":"https://youtu.be/abc"} -->\n<figure class="wp-block-embed">'
    '<div class="wp-block-embed__wrapper">\nhttps://youtu.be/abc\n</div></figure>\n'
    "<!-- /wp:embed -->"
)


def test_no_embeds_is_said(wp, engines) -> None:
    open_document(wp, PARAGRAPH)
    wp.cmd_name_embeds()
    assert wp.host.announced[-1] == "This document has no embeds to name."


def test_a_markdown_embed_gets_a_caption_from_oembed(wp, wp_site, wp_dialogs, engines) -> None:
    open_document(wp, "Watch:\n\n::: embed https://youtu.be/abc\n\nEnd\n", text_format="markdown")
    wp_site.on("GET", "/wp-json/oembed/1.0/proxy", OEMBED)
    wp.cmd_name_embeds()
    asked = wp_site.sent("GET", "/wp-json/oembed/1.0/proxy")[0]
    assert "url=https%3A%2F%2Fyoutu.be%2Fabc" in asked.full_url
    assert "::: block core/embed https://youtu.be/abc embed-1" in wp.host.text
    island = working(wp).properties["islands"]["embed-1"]
    assert '<figcaption class="wp-element-caption">Spring Fair 2026</figcaption>' in island
    report = wp_dialogs.reports[-1]["text"]
    assert report.startswith("1 of 1 embeds named.")
    assert "YouTube: Spring Fair 2026, by Community Radio. Caption added." in report


def test_html_embeds_are_named_and_failures_say_why(wp, wp_site, wp_dialogs, engines) -> None:
    other = EMBED.replace("abc", "zzz")
    captioned = EMBED.replace("</div></figure>", "</div><figcaption>Old</figcaption></figure>")
    captioned = captioned.replace("abc", "old")
    open_document(wp, EMBED + "\n\n" + other + "\n\n" + captioned)

    def answer(_request, query):
        if query["url"] == ["https://youtu.be/abc"]:
            return OEMBED
        return {"title": ""}

    wp_site.on("GET", "/wp-json/oembed/1.0/proxy", answer)
    wp.cmd_name_embeds()
    assert wp.host.text.count("<figcaption") == 2
    assert "Spring Fair 2026</figcaption>" in wp.host.text
    report = wp_dialogs.reports[-1]["text"]
    assert report.startswith("1 of 2 embeds named; 1 already had a caption.")
    assert "https://youtu.be/zzz: Community Radio could not say what this is" in report


def test_an_oembed_refusal_is_reported_per_embed(wp, wp_site, wp_dialogs, engines) -> None:
    open_document(wp, EMBED)
    wp.cmd_name_embeds()
    report = wp_dialogs.reports[-1]["text"]
    assert report.startswith("0 of 1 embeds named.")
    assert "https://youtu.be/abc: not named." in report
    assert "<figcaption" not in wp.host.text


def test_every_embed_already_captioned_is_said(wp, engines) -> None:
    open_document(wp, EMBED.replace("</div></figure>", "</div><figcaption>A</figcaption></figure>"))
    wp.cmd_name_embeds()
    assert wp.host.announced[-1] == "Every embed in this document already has a caption."


# --------------------------------------------------------------------------- #
# Publish a Document as a Page

PDF_URL = "https://radio.example/wp-content/uploads/annual-report.pdf"


@pytest.fixture
def report_pdf(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "annual-report.pdf"
    path.write_bytes(b"%PDF-1.7 report")
    monkeypatch.setattr(ldlg, "pick_file", lambda *_a, **_k: path)
    return path


def test_cancelling_the_file_choice_converts_nothing(wp, monkeypatch, engines) -> None:
    monkeypatch.setattr(ldlg, "pick_file", lambda *_a, **_k: None)
    wp.cmd_document_as_page()
    assert engines.converted == []


def test_a_document_becomes_a_page_draft_linked_to_its_upload(
    wp, wp_site, wp_dialogs, engines, report_pdf
) -> None:
    serve_upload(wp_site, media(50, PDF_URL, "application/pdf", "Annual report", 15))
    wp_dialogs.answer("ask_text", lambda **kw: kw["value"])
    wp.cmd_document_as_page()
    assert wp_dialogs.asked("ask_text")[0]["value"] == "Annual report"
    upload = wp_site.sent("POST", f"{API}/media")[0]
    assert upload.data == b"%PDF-1.7 report"
    assert upload.get_header("Content-type") == "application/pdf"
    copy = working(wp)
    assert copy.kind == "page" and copy.title == "Annual report"
    assert copy.properties["source_document"] == 50
    assert wp.host.text.startswith(f"[Download the original PDF document, 15 bytes]({PDF_URL})")
    assert "We grew." in wp.host.text
    assert "Nothing is published until you choose Publish." in wp.host.announced[-1]


def test_a_scanned_document_is_read_by_ocr_after_a_yes(
    wp, wp_site, wp_dialogs, engines, report_pdf
) -> None:
    engines.convert_answer = Converted("", needs_ocr=True)
    serve_upload(wp_site, media(50, PDF_URL, "application/pdf", "Annual report"))
    wp_dialogs.answer("ask_text", "Report").answer("confirm", True)
    wp.cmd_document_as_page()
    assert engines.converted == ["text", "ocr"]
    assert "Scanned words." in wp.host.text


def test_a_document_with_no_text_uploads_nothing(wp, wp_site, wp_dialogs, engines, report_pdf):
    engines.convert_answer = Converted("", needs_ocr=True)
    wp_dialogs.answer("ask_text", "Report")
    wp.cmd_document_as_page()
    assert "has no text QUILL could read" in wp.host.announced[-1]
    assert wp_site.requests == []


def test_a_document_already_in_the_library_can_be_reused(
    wp, wp_site, wp_dialogs, engines, report_pdf
) -> None:
    wp_site.on("GET", f"{API}/media", [media(51, PDF_URL, "application/pdf", "Old", 15)])
    wp_dialogs.answer("ask_text", "Report").answer("confirm", True)
    wp.cmd_document_as_page()
    assert wp_site.sent("POST", f"{API}/media") == []
    assert working(wp).properties["source_document"] == 51


def test_an_empty_title_converts_nothing(wp, wp_dialogs, engines, report_pdf) -> None:
    wp_dialogs.answer("ask_text", "  ")
    wp.cmd_document_as_page()
    assert engines.converted == []


# --------------------------------------------------------------------------- #
# the family apps: Post This Episode, Upload to WordPress


@pytest.fixture
def episode_audio(tmp_path) -> Path:
    path = tmp_path / "episode-12.mp3"
    path.write_bytes(b"ID3EPISODE")
    return path


EPISODE_URL = "https://radio.example/wp-content/uploads/episode-12.mp3"


def test_post_this_episode_without_audio_says_so(wp, engines) -> None:
    wp.post_episode(Episode(title="Episode 12"))
    assert "has no audio file on this computer yet" in wp.host.said


def test_post_this_episode_uploads_and_drafts_the_post(wp, wp_site, engines, episode_audio):
    serve_upload(wp_site, media(60, EPISODE_URL, "audio/mpeg", "Episode 12"))
    wp.post_episode(
        Episode(
            title="Episode 12",
            audio_path=episode_audio,
            show_notes="<p>Guests <b>Ann</b> and Bo.</p>",
            chapters=(Chapter(0, "Welcome"), Chapter(75, "News")),
            transcript="Hello and welcome.",
        )
    )
    assert wp_site.sent("POST", f"{API}/media")[0].data == b"ID3EPISODE"
    copy = working(wp)
    assert copy.kind == "post" and copy.title == "Episode 12"
    assert EPISODE_URL in copy.properties["islands"]["episode-player-1"]
    text = wp.host.text
    assert text.startswith("::: block core/audio player episode-player-1")
    assert "**Ann**" in text
    assert "- 0:00 Welcome\n- 1:15 News" in text
    assert '::: details "Read the transcript"' in text
    assert engines.transcribed == []
    assert "its post is a local draft" in wp.host.said


def test_post_this_episode_offers_a_transcript_when_there_is_none(
    wp, wp_site, wp_dialogs, engines, episode_audio
) -> None:
    serve_upload(wp_site, media(60, EPISODE_URL, "audio/mpeg", "Episode 12"))
    wp_dialogs.answer("confirm", True)
    wp.post_episode(Episode(title="Episode 12", audio_path=episode_audio))
    assert engines.transcribed == [episode_audio]
    assert "Hello." in wp.host.text


def test_post_this_episode_without_a_transcript_when_declined(
    wp, wp_site, engines, episode_audio
) -> None:
    serve_upload(wp_site, media(60, EPISODE_URL, "audio/mpeg", "Episode 12"))
    wp.post_episode(Episode(title="Episode 12", audio_path=episode_audio))
    assert engines.transcribed == []
    assert "::: details" not in wp.host.text


def test_upload_to_wordpress_copies_the_address(wp, wp_site, engines, episode_audio) -> None:
    serve_upload(wp_site, media(60, EPISODE_URL, "audio/mpeg", "Episode 12"))
    wp.upload_file(episode_audio)
    assert wp.host.clipboard == EPISODE_URL
    assert wp.host.announced[-1] == (
        "episode-12.mp3 is in Community Radio's Media Library. Its address is copied."
    )


def test_upload_to_wordpress_of_a_missing_file_says_so(wp, wp_site, tmp_path, engines) -> None:
    wp.upload_file(tmp_path / "gone.mp3")
    assert "is not on this computer any more" in wp.host.said
    assert wp_site.requests == []


def test_upload_to_wordpress_sends_several_and_copies_every_address(
    wp, wp_site, engines, tmp_path
) -> None:
    first, second = tmp_path / "one.mp3", tmp_path / "two.mp3"
    first.write_bytes(b"1")
    second.write_bytes(b"2")
    serve_upload(wp_site, media(60, EPISODE_URL, "audio/mpeg", "x"))
    wp.upload_files([first, second, tmp_path / "gone.mp3"])
    assert [r.data for r in wp_site.sent("POST", f"{API}/media")] == [b"1", b"2"]
    assert wp.host.clipboard == f"{EPISODE_URL}\n{EPISODE_URL}"
    assert "Uploading 2 of 2: two.mp3." in wp.host.said
    assert wp.host.announced[-1].startswith("2 files are in Community Radio's Media Library.")


class FakeTasks:
    def submit(self, name, func, *, on_success, on_failure):
        try:
            result = func()
        except BaseException as exc:  # noqa: BLE001
            on_failure(None, exc)
            return
        on_success(None, result)


class FakeApp:
    def __init__(self) -> None:
        self.frame = object()
        self.said: list[str] = []
        self.modals: list[str] = []
        self._task_manager = FakeTasks()

    def _announce(self, text: str) -> None:
        self.said.append(text)

    def _show_modal_dialog(self, _dialog, label: str) -> int:
        self.modals.append(label)
        return 5


def test_the_family_host_runs_tasks_and_speaks_through_the_app() -> None:
    app = FakeApp()
    host = fam.FamilyWordPressHost(app, launch=lambda _p: True)
    got: list[object] = []
    host.run_task("x", lambda: 3, got.append, got.append)
    host.run_task("y", lambda: 1 / 0, lambda _r: None, got.append)
    assert got[0] == 3 and isinstance(got[1], ZeroDivisionError)
    assert host.show_modal(object(), "Pick") == 5 and app.modals == ["Pick"]
    assert host.parent is app.frame
    assert host.current_path() is None and host.current_text() == ""


def test_the_family_host_says_where_the_draft_is_when_quill_cannot_open() -> None:
    app = FakeApp()
    opened: list[Path] = []
    fam.FamilyWordPressHost(app, launch=lambda p: opened.append(p) or True).open_path(Path("a.md"))
    assert app.said == []
    fam.FamilyWordPressHost(app, launch=lambda _p: False).open_path(Path("a.md"))
    assert app.said == [fam.WHERE_THE_DRAFT_IS]
    assert opened == [Path("a.md")]


def test_family_entry_points_need_a_choice_first() -> None:
    app = FakeApp()
    fam.post_episode(app, None)
    fam.upload_to_wordpress(app, [])
    assert app.said == [
        "Choose an episode first, then Post This Episode.",
        "Choose a file first, then Upload to WordPress.",
    ]


def test_family_entry_points_reach_the_shared_commands(monkeypatch) -> None:
    app = FakeApp()
    calls: list[tuple[str, object]] = []

    class Commands:
        def post_episode(self, episode):
            calls.append(("post", episode))

        def upload_files(self, paths):
            calls.append(("upload", paths))

    app._wordpress_family_commands = Commands()
    episode = Episode(title="E")
    fam.post_episode(app, episode)
    fam.upload_to_wordpress(app, [Path("f.pdf")])
    assert calls == [("post", episode), ("upload", [Path("f.pdf")])]


def test_family_entry_points_are_off_in_safe_mode() -> None:
    app = FakeApp()
    app._safe_mode = True
    fam.post_episode(app, Episode(title="E"))
    fam.upload_to_wordpress(app, [Path("f.pdf")])
    assert app.said == [fam.SAFE_MODE_SENTENCE] * 2


def test_commands_for_builds_the_shared_commands_once() -> None:
    app = FakeApp()
    first = fam.commands_for(app)
    assert fam.commands_for(app) is first
    assert isinstance(first.host, fam.FamilyWordPressHost)
