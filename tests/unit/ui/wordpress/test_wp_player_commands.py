"""Play in the Media Library, Play Media Here, and the other routes (wordpress.md 6.1a).

The player window is faked: ``pwin.play`` records what it was asked to play,
and a test drives its callbacks the way its buttons would.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core import app_launcher
from quill.core.wordpress import listening as ls
from quill.core.wordpress import local as lc
from quill.ui import wordpress_player_window as pwin

API = "/wp-json/wp/v2"
UPLOADS = "https://radio.example/wp-content/uploads/2026/11"
VTT = "WEBVTT\n\n00:00:00.000 --> 00:00:04.000\nWelcome to the station.\n"


def media(item_id: int, filename: str, mime: str) -> dict:
    return {
        "id": item_id,
        "title": {"raw": filename.rsplit(".", 1)[0].title()},
        "media_type": "image" if mime.startswith("image/") else "file",
        "mime_type": mime,
        "source_url": f"{UPLOADS}/{filename}",
        "alt_text": "",
        "caption": {"raw": ""},
        "description": {"raw": ""},
        "media_details": {"filesize": 4000},
        "date_gmt": "2026-11-01T10:00:00",
        "post": 0,
    }


LIBRARY = [
    media(1, "photo.jpg", "image/jpeg"),
    media(2, "tone.wav", "audio/wav"),
    media(3, "clip.mp4", "video/mp4"),
    media(4, "clip.en.vtt", "text/vtt"),
]


@pytest.fixture
def played(monkeypatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def fake_play(parent, show_modal, playable, **kwargs):
        calls.append({"playable": playable, **kwargs})

    monkeypatch.setattr(pwin, "play", fake_play)
    return calls


def open_library(wp, wp_site, wp_dialogs) -> None:
    wp_site.on("GET", f"{API}/media", LIBRARY)
    wp_site.on("GET", f"{API}/pages", [])
    wp_site.on("GET", f"{API}/posts", [])
    wp.cmd_media_library()
    assert wp_dialogs.window["title"] == "Media Library: Community Radio"


def open_document(wp, text: str, caret: int, fmt: str = "html", islands=None) -> None:
    copy = lc.WorkingCopy(
        site_id="radio",
        kind="post",
        local_id=lc.new_local_id(),
        remote_id=41,
        title="Our Schedule",
        text=text,
        text_format=fmt,
    )
    if islands:
        copy.properties["islands"] = islands
    wp.host.open_path(wp.local.write_document(copy))
    wp.host.caret = caret


# -- the Media Library ------------------------------------------------------------


def test_play_on_an_audio_row_opens_the_player(wp, wp_site, wp_dialogs, played) -> None:
    open_library(wp, wp_site, wp_dialogs)
    wp_dialogs.press("&Play...", 1)
    (call,) = played
    assert call["playable"].url == f"{UPLOADS}/tone.wav"
    assert call["playable"].kind == "audio"
    assert call["site_name"] == "Community Radio"


def test_play_on_a_picture_says_why_not(wp, wp_site, wp_dialogs, played) -> None:
    open_library(wp, wp_site, wp_dialogs)
    wp_dialogs.press("&Play...", 0)
    assert played == []
    assert "not audio or video" in wp.host.announced[-1]


def test_a_video_reads_its_captions_on_request(wp, wp_site, wp_dialogs, played) -> None:
    wp_site.on("GET", "/wp-content/uploads/2026/11/clip.en.vtt", VTT.encode())
    open_library(wp, wp_site, wp_dialogs)
    wp_dialogs.press("&Play...", 2)
    (call,) = played
    playable = call["playable"]
    assert [t.srclang for t in playable.captions] == ["en"]
    # Nothing is read until Captions is pressed.
    assert wp_site.sent("GET", "/wp-content/uploads/2026/11/clip.en.vtt") == []
    got: list[Any] = []
    call["read_captions"](playable.captions[0], got.append)
    assert got[0][0].text == "Welcome to the station."
    assert len(wp_site.sent("GET", "/wp-content/uploads/2026/11/clip.en.vtt")) == 1


def test_captions_that_fail_say_why(wp, wp_site, wp_dialogs, played) -> None:
    open_library(wp, wp_site, wp_dialogs)
    wp_dialogs.press("&Play...", 2)
    call = played[0]
    got: list[Any] = []
    call["read_captions"](call["playable"].captions[0], got.append)
    assert got == []
    assert "captions could not be read" in wp.host.announced[-1]


def test_open_in_browser_is_the_hosts_browser(wp, wp_site, wp_dialogs, played) -> None:
    open_library(wp, wp_site, wp_dialogs)
    wp_dialogs.press("&Play...", 1)
    played[0]["open_in_browser"](f"{UPLOADS}/tone.wav")
    assert wp.host.browsed == [f"{UPLOADS}/tone.wav"]


def test_open_in_quill_media_player(wp, wp_site, wp_dialogs, played, monkeypatch) -> None:
    launched: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setattr(app_launcher, "is_app_released", lambda key: True)
    monkeypatch.setattr(
        app_launcher,
        "launch_app",
        lambda key, extra_args=(): launched.append((key, extra_args)) or True,
    )
    open_library(wp, wp_site, wp_dialogs)
    wp_dialogs.press("&Play...", 1)
    playable = played[0]["playable"]
    played[0]["open_in_player"](playable)
    assert launched == [("player", (f"{UPLOADS}/tone.wav",))]
    assert "Quill Media Player" in wp.host.announced[-1]


def test_open_in_quill_media_player_when_it_is_not_there(
    wp, wp_site, wp_dialogs, played, monkeypatch
) -> None:
    monkeypatch.setattr(app_launcher, "is_app_released", lambda key: True)
    monkeypatch.setattr(app_launcher, "launch_app", lambda key, extra_args=(): False)
    open_library(wp, wp_site, wp_dialogs)
    wp_dialogs.press("&Play...", 1)
    played[0]["open_in_player"](played[0]["playable"])
    assert "not installed" in wp.host.announced[-1]


def test_open_in_quill_media_player_before_its_release(
    wp, wp_site, wp_dialogs, played, monkeypatch
) -> None:
    monkeypatch.setattr(app_launcher, "is_app_released", lambda key: False)
    monkeypatch.setattr(app_launcher, "launch_app", lambda *a, **k: pytest.fail("must not launch"))
    open_library(wp, wp_site, wp_dialogs)
    wp_dialogs.press("&Play...", 1)
    played[0]["open_in_player"](played[0]["playable"])
    assert "not part of this release" in wp.host.announced[-1]


# -- Play Media Here ----------------------------------------------------------------


def test_play_media_here_plays_the_video_block(wp, played) -> None:
    block = ls.video_block(
        3, f"{UPLOADS}/clip.mp4", track=(f"{UPLOADS}/clip.en.vtt", "English", "en")
    )
    text = "<!-- wp:paragraph -->\n<p>Watch.</p>\n<!-- /wp:paragraph -->\n\n" + block
    open_document(wp, text, text.index("<video"))
    wp.cmd_play_media_here()
    (call,) = played
    assert call["playable"].url == f"{UPLOADS}/clip.mp4"
    assert call["playable"].captions[0].src == f"{UPLOADS}/clip.en.vtt"


def test_play_media_here_in_a_markdown_island(wp, played) -> None:
    islands = {"audio-1": ls.audio_block(2, f"{UPLOADS}/tone.wav", "The tone")}
    text = "Listen.\n\n" + ls.island_fence("core/audio", "audio-1") + "\n"
    open_document(wp, text, text.index(":::") + 1, fmt="markdown", islands=islands)
    wp.cmd_play_media_here()
    assert played[0]["playable"].title == "The tone"


def test_play_media_here_with_nothing_at_the_caret(wp, played) -> None:
    open_document(wp, "<!-- wp:paragraph -->\n<p>Words.</p>\n<!-- /wp:paragraph -->", 5)
    wp.cmd_play_media_here()
    assert played == []
    assert "no audio or video block at the caret" in wp.host.announced[-1]


def test_play_media_here_outside_wordpress(wp, played) -> None:
    wp.cmd_play_media_here()
    assert played == []
    assert wp.host.announced[-1].startswith("Play Media Here works in a WordPress page or post")


def test_play_media_here_refuses_plain_http(wp, played) -> None:
    text = '<figure class="wp-block-audio"><audio controls src="http://radio.example/t.mp3"></audio></figure>'
    open_document(wp, text, 10)
    wp.cmd_play_media_here()
    assert played == []
    assert "not HTTPS" in wp.host.announced[-1]
