"""Captions for Video and Transcript for Audio, behaviourally, with the engines faked."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.speech.provider import TranscriptionResult, TranscriptionSegment
from quill.core.wordpress import local as lc
from quill.core.wordpress.listen_engines import Converted, ListenEngines

API = "/wp-json/wp/v2"
VIDEO_URL = "https://radio.example/wp-content/uploads/talk.mp4"
AUDIO_URL = "https://radio.example/wp-content/uploads/show.mp3"


def media(item_id: int, url: str, mime: str, title: str) -> dict:
    return {
        "id": item_id,
        "title": {"raw": title},
        "media_type": "file",
        "mime_type": mime,
        "source_url": url,
        "alt_text": "",
        "media_details": {"filesize": 2048},
        "date_gmt": "2026-11-01T10:00:00",
        "post": 0,
    }


VIDEO = media(12, VIDEO_URL, "video/mp4", "Spring Talk")
AUDIO = media(14, AUDIO_URL, "audio/mpeg", "Morning Show")
UPLOADED = media(30, "https://radio.example/wp-content/uploads/talk.en.vtt", "text/vtt", "Captions")

RESULT = TranscriptionResult(
    full_text="Welcome to the show. Thanks for coming.",
    segments=(
        TranscriptionSegment(0.0, 2.5, "Welcome to the show."),
        TranscriptionSegment(2.5, 4.0, "Thanks for coming."),
    ),
    language="en",
)


class Engines:
    def __init__(self, result: TranscriptionResult = RESULT) -> None:
        self.result = result
        self.transcribed: list[Path] = []

    def bundle(self) -> ListenEngines:
        def transcribe(path: Path) -> TranscriptionResult:
            assert path.read_bytes() == b"MEDIA"
            self.transcribed.append(path)
            return self.result

        return ListenEngines(
            transcribe=transcribe,
            speak=lambda _t, _h, _o: 0,
            convert=lambda _p: Converted(""),
            convert_ocr=lambda _p: Converted(""),
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
        remote_id=5,
        title="Spring Fair",
        text=text,
        text_format=text_format,
        properties={"islands": islands or {}},
    )
    wp.host.open_path(wp.local.write_document(copy))
    return copy


def serve_library(wp_site, *items: dict) -> None:
    wp_site.on("GET", f"{API}/media", list(items))
    wp_site.on("GET", "/wp-content/uploads/talk.mp4", b"MEDIA")
    wp_site.on("GET", "/wp-content/uploads/show.mp3", b"MEDIA")
    wp_site.on("POST", f"{API}/media", UPLOADED)
    wp_site.on("POST", f"{API}/media/30", UPLOADED)


VIDEO_BLOCK = (
    '<!-- wp:video {"id":12} -->\n<figure class="wp-block-video"><video controls '
    f'src="{VIDEO_URL}"></video></figure>\n<!-- /wp:video -->'
)
AUDIO_BLOCK = (
    '<!-- wp:audio {"id":14} -->\n<figure class="wp-block-audio"><audio controls '
    f'src="{AUDIO_URL}"></audio></figure>\n<!-- /wp:audio -->'
)


# --------------------------------------------------------------------------- #
# captions


def test_captions_outside_a_wordpress_document_says_so(wp, engines) -> None:
    wp.cmd_captions()
    assert "This is not a WordPress document" in wp.host.said
    assert engines.transcribed == []


def test_captions_with_no_video_in_the_library_says_so(wp, wp_site, engines) -> None:
    open_document(wp, "<p>Hi</p>")
    wp_site.on("GET", f"{API}/media", [])
    wp.cmd_captions()
    assert "There is no video in Community Radio's Media Library yet" in wp.host.said
    assert engines.transcribed == []


def test_cancelling_the_video_choice_transcribes_nothing(wp, wp_site, wp_dialogs, engines):
    open_document(wp, VIDEO_BLOCK)
    serve_library(wp_site, VIDEO)
    wp.cmd_captions()
    assert wp_dialogs.asked("ask_choice")[0]["title"] == "Captions for Video"
    assert engines.transcribed == []
    assert wp_site.sent("POST", f"{API}/media") == []


def test_captions_are_reviewed_uploaded_and_wired_to_the_video_block(
    wp, wp_site, wp_dialogs, engines
) -> None:
    open_document(wp, "<!-- wp:paragraph --><p>Hi</p><!-- /wp:paragraph -->\n\n" + VIDEO_BLOCK)
    serve_library(wp_site, VIDEO)
    edited = []

    def review(**kwargs):
        edited.append(kwargs["value"])
        return kwargs["value"].replace("Welcome to the show.", "Welcome to the show. [applause]")

    wp_dialogs.answer("ask_choice", 0).answer("ask_text", review)
    wp.cmd_captions()

    assert "00:00:00.000 --> 00:00:02.500 Welcome to the show." in edited[0]
    assert "Making captions for Spring Talk on this computer" in wp.host.said
    upload = wp_site.sent("POST", f"{API}/media")[0]
    assert upload.data.startswith(b"WEBVTT")
    assert b"[applause]" in upload.data
    assert upload.get_header("Content-type") == "text/vtt"
    assert 'filename="talk.en.vtt"' in upload.get_header("Content-disposition")
    text = wp.host.text
    assert '<track src="https://radio.example/wp-content/uploads/talk.en.vtt"' in text
    assert 'kind="captions"' in text and 'srclang="en"' in text
    opener = json.loads(text.split("<!-- wp:video ", 1)[1].split(" -->", 1)[0])
    assert opener["tracks"][0]["srcLang"] == "en"
    assert text.startswith("<!-- wp:paragraph --><p>Hi</p>")
    assert (
        "Captions uploaded to Community Radio and added to the video in this document"
        in (wp.host.announced[-1])
    )


def test_a_broken_caption_line_is_named_and_the_review_reopens(
    wp, wp_site, wp_dialogs, engines
) -> None:
    open_document(wp, VIDEO_BLOCK)
    serve_library(wp_site, VIDEO)
    wp_dialogs.answer("ask_choice", 0).answer("ask_text", "Welcome with no time\n")
    wp.cmd_captions()
    assert "Line 1 does not start with a time" in wp.host.said
    reviews = wp_dialogs.asked("ask_text")
    assert len(reviews) == 2
    assert reviews[1]["value"] == "Welcome with no time\n"
    assert wp_site.sent("POST", f"{API}/media") == []


def test_captions_in_markdown_change_the_videos_island_not_the_text(
    wp, wp_site, wp_dialogs, engines
) -> None:
    text = "Before\n\n::: block core/video island-1\n\nAfter\n"
    open_document(wp, text, text_format="markdown", islands={"island-1": VIDEO_BLOCK})
    serve_library(wp_site, VIDEO)
    wp_dialogs.answer("ask_choice", 0).answer("ask_text", lambda **kw: kw["value"])
    wp.cmd_captions()
    assert wp.host.text == text
    copy = wp.local.copy_for_path(wp.host.current_path())
    assert "<track " in copy.properties["islands"]["island-1"]


def test_captions_for_a_video_not_in_a_markdown_document_insert_it(
    wp, wp_site, wp_dialogs, engines
) -> None:
    open_document(wp, "Intro\n", text_format="markdown")
    wp.host.go_to_offset(len("Intro\n"))
    serve_library(wp_site, VIDEO)
    wp_dialogs.answer("ask_choice", 0).answer("ask_text", lambda **kw: kw["value"])
    wp.cmd_captions()
    assert "::: block core/video video video-1" in wp.host.text
    copy = wp.local.copy_for_path(wp.host.current_path())
    assert "<track " in copy.properties["islands"]["video-1"]
    assert "a new video block at the caret" in wp.host.announced[-1]


def test_captions_for_a_video_not_in_an_html_document_insert_its_block(
    wp, wp_site, wp_dialogs, engines
) -> None:
    open_document(wp, "<p>Hi</p>")
    serve_library(wp_site, VIDEO)
    wp_dialogs.answer("ask_choice", 0).answer("ask_text", lambda **kw: kw["value"])
    wp.cmd_captions()
    assert '<!-- wp:video {"id":12,"tracks"' in wp.host.text


def test_no_speech_means_no_captions(wp, wp_site, wp_dialogs) -> None:
    fake = Engines(TranscriptionResult(full_text=""))
    wp._listen_engines = fake.bundle()
    open_document(wp, VIDEO_BLOCK)
    serve_library(wp_site, VIDEO)
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_captions()
    assert "No speech was found in Spring Talk" in wp.host.said
    assert wp_dialogs.asked("ask_text") == []


def test_a_video_that_will_not_download_is_said_with_the_reason(
    wp, wp_site, wp_dialogs, engines
) -> None:
    open_document(wp, VIDEO_BLOCK)
    wp_site.on("GET", f"{API}/media", [VIDEO])
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_captions()
    assert engines.transcribed == []
    assert wp.host.announced[-1].startswith("QUILL could not download talk.mp4 from Community")


# --------------------------------------------------------------------------- #
# transcripts


def test_a_folded_transcript_goes_under_the_audio_player(wp, wp_site, wp_dialogs, engines):
    open_document(wp, AUDIO_BLOCK + "\n\n<!-- wp:paragraph --><p>End</p><!-- /wp:paragraph -->")
    serve_library(wp_site, AUDIO)
    wp_dialogs.answer("ask_choice", 0, 0).answer("ask_text", lambda **kw: kw["value"])
    wp.cmd_transcript()
    text = wp.host.text
    player_end = text.index("<!-- /wp:audio -->")
    details = text.index("<!-- wp:details -->")
    assert player_end < details < text.index("<p>End</p>")
    assert "<summary>Read the transcript</summary>" in text
    assert "Welcome to the show. Thanks for coming." in text
    assert wp_site.sent("POST", f"{API}/media") == []
    assert wp.host.announced[-1] == "Transcript of Morning Show added under its player."


def test_a_full_transcript_in_markdown_inserts_a_player_when_none_is_there(
    wp, wp_site, wp_dialogs, engines
) -> None:
    open_document(wp, "Intro\n", text_format="markdown")
    serve_library(wp_site, AUDIO)
    wp_dialogs.answer("ask_choice", 0, 1).answer("ask_text", lambda **kw: kw["value"])
    wp.cmd_transcript()
    assert "::: block core/audio audio audio-1" in wp.host.text
    assert "::: details" not in wp.host.text
    assert "Welcome to the show." in wp.host.text
    copy = wp.local.copy_for_path(wp.host.current_path())
    assert 'wp:audio {"id":14}' in copy.properties["islands"]["audio-1"]
    assert "under a new player" in wp.host.announced[-1]


def test_a_markdown_transcript_folds_under_the_audio_island(wp, wp_site, wp_dialogs, engines):
    text = "::: block core/audio island-2\n\nAfter\n"
    open_document(wp, text, text_format="markdown", islands={"island-2": AUDIO_BLOCK})
    serve_library(wp_site, AUDIO)
    wp_dialogs.answer("ask_choice", 0, 0).answer("ask_text", lambda **kw: kw["value"])
    wp.cmd_transcript()
    assert wp.host.text.index("island-2") < wp.host.text.index('::: details "Read the transcript"')
    assert wp.host.text.index("::: end details") < wp.host.text.index("After")


def test_cancelling_the_transcript_review_inserts_nothing(wp, wp_site, wp_dialogs, engines):
    open_document(wp, AUDIO_BLOCK)
    serve_library(wp_site, AUDIO)
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_transcript()
    assert wp.host.text == AUDIO_BLOCK


def test_cancelling_the_placement_inserts_nothing(wp, wp_site, wp_dialogs, engines) -> None:
    open_document(wp, AUDIO_BLOCK)
    serve_library(wp_site, AUDIO)
    wp_dialogs.answer("ask_choice", 0).answer("ask_text", lambda **kw: kw["value"])
    wp.cmd_transcript()
    assert wp.host.text == AUDIO_BLOCK


def test_speaker_turns_become_paragraphs(wp, wp_site, wp_dialogs) -> None:
    fake = Engines(
        TranscriptionResult(
            full_text="x",
            segments=(
                TranscriptionSegment(0, 1, "Hello.", "Speaker 1"),
                TranscriptionSegment(1, 2, "Again.", "Speaker 1"),
                TranscriptionSegment(2, 3, "Hi.", "Speaker 2"),
            ),
        )
    )
    wp._listen_engines = fake.bundle()
    open_document(wp, AUDIO_BLOCK)
    serve_library(wp_site, AUDIO)
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_transcript()
    assert (
        wp_dialogs.asked("ask_text")[0]["value"] == "Speaker 1: Hello. Again.\n\nSpeaker 2: Hi.\n"
    )


def test_no_speech_means_no_transcript(wp, wp_site, wp_dialogs) -> None:
    wp._listen_engines = Engines(TranscriptionResult(full_text=" ")).bundle()
    open_document(wp, AUDIO_BLOCK)
    serve_library(wp_site, AUDIO)
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_transcript()
    assert "so there is no transcript" in wp.host.said
