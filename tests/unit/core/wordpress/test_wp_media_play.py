"""Listening and watching: what to play, captions, and the HTTPS rule (wordpress.md 6.1a)."""

from __future__ import annotations

import pytest

from quill.core.wordpress import listening as ls
from quill.core.wordpress import media_play as mp
from quill.core.wordpress.site_media import MediaItem

UPLOADS = "https://radio.example/wp-content/uploads/2026/11"


def item(item_id: int, filename: str, mime: str, title: str = "") -> MediaItem:
    return MediaItem(
        id=item_id,
        title=title,
        media_type="file",
        mime_type=mime,
        source_url=f"{UPLOADS}/{filename}",
        alt_text="",
        caption="",
        description="",
        width=0,
        height=0,
        filesize=0,
        date_gmt="2026-11-01T10:00:00",
        post=0,
        filename=filename,
    )


# -- addresses ---------------------------------------------------------------


def test_https_streams_and_plain_http_does_not() -> None:
    assert mp.stream_problem(f"{UPLOADS}/tone.wav") == ""
    assert mp.stream_problem("http://wp.test/tone.wav") == ""  # a loopback test site
    assert "not HTTPS" in mp.stream_problem("http://radio.example/tone.wav")
    assert "no web address" in mp.stream_problem("")


# -- from the library -----------------------------------------------------------


def test_a_picture_is_not_playable() -> None:
    assert mp.from_library(item(1, "a.jpg", "image/jpeg")) is None
    assert mp.from_library(item(2, "a.pdf", "application/pdf")) is None


def test_audio_plays_by_its_title_and_address() -> None:
    playable = mp.from_library(item(3, "tone.wav", "audio/wav", "Test Tone"))
    assert playable == mp.Playable("Test Tone", f"{UPLOADS}/tone.wav", "audio", 3)


def test_a_video_finds_captions_named_for_it() -> None:
    video = item(4, "clip.mp4", "video/mp4")
    items = [
        video,
        item(5, "clip.en.vtt", "text/vtt"),
        item(6, "clip.es.vtt", "text/vtt"),
        item(7, "other.en.vtt", "text/vtt"),
        item(8, "clipboard.en.vtt", "text/vtt"),
    ]
    playable = mp.from_library(video, items)
    assert playable is not None
    assert playable.title == "clip.mp4"
    assert [(t.src.rsplit("/", 1)[-1], t.label, t.srclang) for t in playable.captions] == [
        ("clip.en.vtt", "English", "en"),
        ("clip.es.vtt", "Spanish", "es"),
    ]


# -- from the document -----------------------------------------------------------


def test_the_video_block_at_the_caret_with_its_track() -> None:
    block = ls.video_block(
        9, f"{UPLOADS}/clip.mp4", track=(f"{UPLOADS}/clip.en.vtt", "English", "en")
    )
    text = "<!-- wp:paragraph -->\n<p>Before.</p>\n<!-- /wp:paragraph -->\n\n" + block
    playable = mp.media_at(text, "html", text.index("<video"))
    assert playable is not None
    assert (playable.kind, playable.url, playable.media_id) == ("video", f"{UPLOADS}/clip.mp4", 9)
    assert playable.captions == (mp.CaptionTrack(f"{UPLOADS}/clip.en.vtt", "English", "en"),)
    assert mp.media_at(text, "html", 5) is None  # in the paragraph


def test_an_audio_block_names_itself_by_its_caption() -> None:
    text = ls.audio_block(3, f"{UPLOADS}/tone.wav", "A test tone")
    playable = mp.media_at(text, "html", 10)
    assert playable is not None
    assert (playable.kind, playable.title, playable.captions) == ("audio", "A test tone", ())


def test_an_island_in_a_markdown_document() -> None:
    token = "video-1"
    islands = {token: ls.video_block(9, f"{UPLOADS}/clip.mp4")}
    text = "Intro.\n\n" + ls.island_fence("core/video", token) + "\n\nAfter.\n"
    playable = mp.media_at(text, "markdown", text.index(":::") + 3, islands)
    assert playable is not None
    assert playable.url == f"{UPLOADS}/clip.mp4"


def test_a_bare_tag_from_insert_from_library() -> None:
    tag = f'<audio controls src="{UPLOADS}/t.mp3"></audio>'
    text = f'Intro.\n\n<figure class="wp-block-audio">{tag}</figure>\n'
    playable = mp.media_at(text, "markdown", text.index("<audio") + 2)
    assert playable is not None
    assert (playable.kind, playable.title) == ("audio", "t.mp3")


# -- captions -------------------------------------------------------------------

VTT = """WEBVTT

NOTE a note is skipped

1
00:00:01.000 --> 00:00:03.500 align:start
Hello <b>there</b>.

00:03.500 --> 00:05.000
Second line
goes on.
"""


def test_webvtt_reads_into_cues() -> None:
    cues = mp.parse_webvtt(VTT)
    assert [(c.start, c.end, c.text) for c in cues] == [
        (1.0, 3.5, "Hello there."),
        (3.5, 5.0, "Second line goes on."),
    ]
    assert mp.caption_at(cues, 2000) == "Hello there."
    assert mp.caption_at(cues, 3500) == "Second line goes on."
    assert mp.caption_at(cues, 9000) == ""


class _Response:
    def __init__(self, raw: bytes) -> None:
        self.raw = raw

    def read(self) -> bytes:
        return self.raw

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False


class _Api:
    timeout = 5

    def __init__(self, raw: bytes = VTT.encode()) -> None:
        self.raw = raw
        self.asked: list[str] = []

    def _opener(self, request, timeout=None, context=None):  # noqa: ANN001 - urllib's shape
        self.asked.append(request.full_url)
        return _Response(self.raw)


def test_captions_are_read_only_from_the_site_itself() -> None:
    api = _Api()
    track = mp.CaptionTrack(f"{UPLOADS}/clip.en.vtt", "English", "en")
    assert len(mp.fetch_captions(api, track, "https://radio.example")) == 2
    with pytest.raises(mp.MediaPlayError, match="another site"):
        mp.fetch_captions(
            api, mp.CaptionTrack("https://elsewhere.example/c.vtt", "English", "en"), UPLOADS
        )
    assert api.asked == [f"{UPLOADS}/clip.en.vtt"]


def test_an_empty_captions_file_says_so() -> None:
    track = mp.CaptionTrack(f"{UPLOADS}/clip.en.vtt", "English", "en")
    with pytest.raises(mp.MediaPlayError, match="no captions"):
        mp.fetch_captions(_Api(b"WEBVTT\n"), track, "https://radio.example")
