"""Tests for transcript import/export, search, and sync (PRD 19.5)."""

from quill_social.services.transcripts import (
    Cue,
    Transcript,
    cue_at,
    from_srt,
    from_vtt,
    load_transcript,
    make_clip,
    quote_timepoint,
    save_transcript,
    search,
    to_markdown,
    to_srt,
    to_txt,
    to_vtt,
)

SRT = """1
00:00:01,000 --> 00:00:03,000
Hello world

2
00:00:03,500 --> 00:00:06,000
Second line here
"""

VTT = """WEBVTT

00:00:01.000 --> 00:00:03.000
Hello world

00:00:03.500 --> 00:00:06.000
Second line here
"""


def test_from_srt_parses_cues():
    t = from_srt(SRT, resource_id="media:1")
    assert len(t.cues) == 2
    assert t.cues[0].start_ms == 1000
    assert t.cues[0].end_ms == 3000
    assert t.cues[0].text == "Hello world"
    assert t.cues[1].start_ms == 3500


def test_srt_round_trip():
    t = from_srt(SRT)
    again = from_srt(to_srt(t))
    assert [c.to_dict() for c in again.cues] == [c.to_dict() for c in t.cues]


def test_vtt_round_trip():
    t = from_vtt(VTT)
    assert len(t.cues) == 2
    again = from_vtt(to_vtt(t))
    assert [c.to_dict() for c in again.cues] == [c.to_dict() for c in t.cues]


def test_vtt_output_has_header():
    t = from_srt(SRT)
    out = to_vtt(t)
    assert out.startswith("WEBVTT")
    assert "-->" in out
    assert "." in out.split("\n")[2]  # dot separator, not comma


def test_txt_and_markdown_export():
    t = from_srt(SRT)
    txt = to_txt(t)
    assert "Hello world" in txt
    assert "-->" not in txt
    md = to_markdown(t)
    assert "# Transcript" in md
    assert "[00:01]" in md


def test_search_case_insensitive():
    t = from_srt(SRT)
    hits = search(t, "HELLO")
    assert len(hits) == 1
    assert hits[0].text == "Hello world"
    assert search(t, "") == []


def test_cue_at_boundaries():
    t = from_srt(SRT)
    assert cue_at(t, 0) is None  # before first cue
    assert cue_at(t, 1000).text == "Hello world"  # inclusive start
    assert cue_at(t, 2999).text == "Hello world"
    assert cue_at(t, 3000) is None  # exclusive end, in gap
    assert cue_at(t, 3500).text == "Second line here"


def test_quote_timepoint_formatting():
    t = from_srt(SRT)
    q = quote_timepoint(t, 1500)
    assert q == "Hello world @ 00:01"
    # a gap falls back to the nearest earlier cue
    gap = quote_timepoint(t, 3200)
    assert gap == "Hello world @ 00:01"


def test_make_clip_rebases_times():
    t = from_srt(SRT)
    clip = make_clip(t, 2000, 4000)
    assert len(clip.cues) == 2
    # first cue overlaps [2000,4000): rebased to start at 0
    assert clip.cues[0].start_ms == 0
    assert clip.cues[0].end_ms == 1000  # 3000-2000
    assert clip.cues[1].start_ms == 1500  # 3500-2000


def test_make_clip_excludes_outside():
    t = from_srt(SRT)
    clip = make_clip(t, 4000, 6000)
    assert len(clip.cues) == 1
    assert clip.cues[0].text == "Second line here"


def test_persistence_round_trip(store):
    t = Transcript(
        resource_id="media:xyz",
        lang="en",
        cues=[Cue(0, 1000, "hi"), Cue(1000, 2000, "there")],
    )
    save_transcript(store, t)
    loaded = load_transcript(store, "media:xyz")
    assert loaded is not None
    assert loaded.resource_id == "media:xyz"
    assert loaded.lang == "en"
    assert len(loaded.cues) == 2
    assert loaded.cues[1].text == "there"


def test_load_missing_returns_none(store):
    assert load_transcript(store, "nope") is None
