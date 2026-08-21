"""One transcript per episode, fetched or made at most once.

Three tiers read the same words -- the show-note anchors, the lexical
segmentation, and the fetch that feeds it -- so the thing worth testing is that
they share, and that the expensive ways of getting a transcript stay behind the
budget that authorises them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.podcasts.chapter_inference import TimedCue
from quill.core.podcasts.inference_budget import for_budget
from quill.ui.podcasts import chapter_cues as ui

_VTT = """WEBVTT

00:00:00.000 --> 00:00:05.000
welcome to the programme

00:10:00.000 --> 00:10:05.000
and now the interview
"""


def _evidence() -> dict[str, Any]:
    return {"cohesion_margin": 0.0, "examined": {}}


def test_the_timed_cache_is_what_chapters_read(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "quill.core.podcasts.transcripts.load_cached_transcript_vtt", lambda _s, _g: _VTT
    )
    monkeypatch.setattr(
        "quill.core.podcasts.transcripts.load_cached_transcript", lambda _s, _g: "flat words"
    )
    cues_for = ui._cue_source(None, None, "s", "g", for_budget("thorough"), _evidence(), False)
    cues = cues_for(allow_fetch=False)
    assert [cue.start_ms for cue in cues] == [0, 600_000]


def test_a_transcript_whose_timings_were_dropped_is_no_use_here(monkeypatch: Any) -> None:
    """The bug this cache exists to fix: flat text cannot be segmented."""
    monkeypatch.setattr(
        "quill.core.podcasts.transcripts.load_cached_transcript_vtt", lambda _s, _g: ""
    )
    monkeypatch.setattr(
        "quill.core.podcasts.transcripts.load_cached_transcript",
        lambda _s, _g: "welcome to the programme and now the interview",
    )
    cues_for = ui._cue_source(None, None, "s", "g", for_budget("thorough"), _evidence(), False)
    assert cues_for(allow_fetch=False) == []


def test_one_fetch_serves_every_tier(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "quill.core.podcasts.transcripts.load_cached_transcript_vtt", lambda _s, _g: ""
    )
    monkeypatch.setattr("quill.core.podcasts.transcripts.load_cached_transcript", lambda _s, _g: "")
    fetches: list[str] = []

    def _fetch(_show: Any, _episode: Any, _show_id: str, _guid: str, _safe: bool) -> list[TimedCue]:
        fetches.append("fetch")
        return [TimedCue(0, "one"), TimedCue(600_000, "two")]

    monkeypatch.setattr(ui, "_fetch_cues", _fetch)
    evidence = _evidence()
    cues_for = ui._cue_source(None, object(), "s", "g", for_budget("thorough"), evidence, False)
    assert len(cues_for(allow_fetch=True)) == 2
    assert len(cues_for(allow_fetch=True)) == 2
    assert len(cues_for(allow_fetch=False)) == 2
    assert fetches == ["fetch"]
    assert evidence["transcript"]["fetched"] is True


def test_a_tier_that_may_not_fetch_does_not(monkeypatch: Any) -> None:
    """Tier 3 is 'a transcript already here'. If it fetched, tier 3b could never run."""
    monkeypatch.setattr(
        "quill.core.podcasts.transcripts.load_cached_transcript_vtt", lambda _s, _g: ""
    )
    monkeypatch.setattr("quill.core.podcasts.transcripts.load_cached_transcript", lambda _s, _g: "")

    def _never(*_args: object, **_kwargs: object) -> list[TimedCue]:
        raise AssertionError("tier 3 must not fetch")

    monkeypatch.setattr(ui, "_fetch_cues", _never)
    cues_for = ui._cue_source(None, object(), "s", "g", for_budget("thorough"), _evidence(), False)
    assert cues_for(allow_fetch=False) == []


def test_thorough_never_transcribes_and_deep_does(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "quill.core.podcasts.transcripts.load_cached_transcript_vtt", lambda _s, _g: ""
    )
    monkeypatch.setattr("quill.core.podcasts.transcripts.load_cached_transcript", lambda _s, _g: "")
    monkeypatch.setattr(ui, "_fetch_cues", lambda *_a, **_k: [])
    made: list[str] = []

    def _transcribe(
        _path: Path | None, _show: str, _guid: str, _progress: object
    ) -> list[TimedCue]:
        made.append("transcribe")
        return [TimedCue(0, "one"), TimedCue(600_000, "two")]

    monkeypatch.setattr(ui, "_transcribe_cues", _transcribe)
    audio = tmp_path / "episode.mp3"
    audio.write_bytes(b"x")

    thorough = ui._cue_source(
        None,
        object(),
        "s",
        "g",
        for_budget("thorough"),
        _evidence(),
        False,
        audio_path=audio,
    )
    assert thorough(allow_fetch=True) == []
    assert made == []

    evidence = _evidence()
    deep = ui._cue_source(
        None, object(), "s", "g", for_budget("deep"), evidence, False, audio_path=audio
    )
    assert len(deep(allow_fetch=True)) == 2
    assert made == ["transcribe"]
    assert evidence["transcript"]["transcribed"] is True


def test_the_report_says_how_the_transcript_was_obtained() -> None:
    evidence = _evidence()
    cues = [TimedCue(0, "one"), TimedCue(600_000, "two")]
    ui._segment_cues(cues, for_budget("thorough"), 3_600_000, evidence)
    assert "transcript lines" in evidence["examined"]["transcript"]
    assert "fetched" not in evidence["examined"]["transcript"]

    evidence = _evidence()
    evidence["transcript"] = {"cues": cues, "fetched": True}
    ui._segment_cues(cues, for_budget("thorough"), 3_600_000, evidence)
    assert evidence["examined"]["transcript"].endswith(", fetched")

    evidence = _evidence()
    evidence["transcript"] = {"cues": cues, "transcribed": True}
    ui._segment_cues(cues, for_budget("thorough"), 3_600_000, evidence)
    assert evidence["examined"]["transcript"].endswith(", transcribed on this machine")
