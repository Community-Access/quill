"""Tests for the QUILL Ecosystem Bridge intents (PRD 20)."""

import pytest

from quill_social.model import Media, SocialItem
from quill_social.services.ecosystem import (
    BEACON_KINDS,
    add_radio_stream,
    audio_studio_clip,
    beacon_target,
    send_to_quill,
    share_cast,
    thread_to_markdown,
)


def _thread():
    return [
        SocialItem(
            item_id="i1",
            author_display="Ada Lovelace",
            author_handle="@ada@example.social",
            text="First post in the thread.",
        ),
        SocialItem(
            item_id="i2",
            author_display="Ada Lovelace",
            author_handle="@ada@example.social",
            text="A reply with a picture.",
            media=[Media(kind="image", alt_text="a diagram")],
        ),
    ]


def test_thread_to_markdown_preserves_attribution():
    md = thread_to_markdown(_thread(), title="My Thread")
    assert "# My Thread" in md
    assert "## Ada Lovelace (@ada@example.social)" in md
    assert "First post in the thread." in md
    assert "[image: a diagram]" in md
    assert "---" in md  # separator between posts


def test_thread_to_markdown_flags_missing_alt():
    items = [SocialItem(text="hi", media=[Media(kind="image", alt_text="")])]
    md = thread_to_markdown(items)
    assert "no alt text" in md


def test_send_to_quill_single_item():
    intent = send_to_quill(_thread()[0], title="One")
    assert intent.kind == "quill.document"
    assert intent.source_item_ids == ["i1"]
    assert "Ada Lovelace" in intent.attribution[0]
    assert "First post" in intent.markdown
    assert "One" in intent.describe()


def test_send_to_quill_thread_dedups_attribution():
    intent = send_to_quill(_thread())
    assert intent.source_item_ids == ["i1", "i2"]
    assert len(intent.attribution) == 1  # same author, de-duplicated
    d = intent.to_dict()
    assert d["kind"] == "quill.document"


def test_beacon_target_kinds():
    for kind in BEACON_KINDS:
        t = beacon_target(kind, ref="r", label=f"lbl-{kind}")
        assert t.kind == kind
        assert t.to_dict()["target_kind"] == kind
        assert kind in t.describe()


def test_beacon_target_rejects_unknown():
    with pytest.raises(ValueError):
        beacon_target("nonsense", ref="r")


def test_beacon_audio_timepoint():
    t = beacon_target("audio-timepoint", ref="media:1#42000", label="key moment")
    assert t.kind == "audio-timepoint"
    assert "key moment" in t.describe()


def test_add_radio_stream():
    intent = add_radio_stream("Jazz FM", "https://stream.example/jazz", now=lambda: 123)
    assert intent.kind == "radio.add_stream"
    assert intent.created == 123
    assert "Jazz FM" in intent.describe()
    assert intent.to_dict()["url"] == "https://stream.example/jazz"


def test_share_cast_with_and_without_chapter():
    plain = share_cast("Episode 5", now=lambda: 1)
    assert plain.chapter_ms is None
    assert "Episode 5" in plain.describe()
    chaptered = share_cast("Episode 5", chapter_ms=65_000, now=lambda: 1)
    assert "1:05" in chaptered.describe()
    assert chaptered.to_dict()["chapter_ms"] == 65_000


def test_audio_studio_clip_preserves_attribution():
    media = Media(kind="audio", uri="clip.mp3")
    intent = audio_studio_clip(
        media, 10_000, 25_000, source_item_id="i9", attribution="Ada", now=lambda: 7
    )
    assert intent.kind == "audio_studio.clip"
    assert intent.media_uri == "clip.mp3"
    assert intent.duration_ms == 15_000
    assert intent.attribution == "Ada"
    assert intent.created == 7
    assert "Ada" in intent.describe()
    assert intent.to_dict()["duration_ms"] == 15_000


def test_audio_studio_clip_accepts_plain_uri():
    intent = audio_studio_clip("plain.mp3", 0, 1000)
    assert intent.media_uri == "plain.mp3"
