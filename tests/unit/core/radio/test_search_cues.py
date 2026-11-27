"""Find Streams cues and live titles: the pure rules."""

from __future__ import annotations

import json
import wave
from pathlib import Path

from quill.core.radio import live_check, search_cues
from quill.core.sound_events import SoundEvent

MP3 = (Path(__file__).parent / "fixtures" / "live_check" / "mp3_prefix.bin").read_bytes()
PACK = Path(__file__).resolve().parents[4] / "quill" / "assets" / "sound_packs" / "ink"


def test_a_failed_search_and_an_empty_one_have_different_cues() -> None:
    failed = search_cues.outcome_cue(failed=True, found=0, enabled=True)
    empty = search_cues.outcome_cue(failed=False, found=0, enabled=True)
    assert failed == SoundEvent.RADIO_SEARCH_FAILED and empty == SoundEvent.RADIO_SEARCH_EMPTY
    assert failed != empty


def test_no_cue_when_streams_were_found_or_the_switch_is_off() -> None:
    assert search_cues.outcome_cue(failed=False, found=3, enabled=True) == ""
    assert search_cues.outcome_cue(failed=True, found=0, enabled=False) == ""
    assert search_cues.outcome_cue(failed=False, found=0, enabled=False) == ""


def test_the_working_cue_repeats_every_two_seconds() -> None:
    assert search_cues.CUE_INTERVAL_MS == 2000


def test_titles_are_spoken_at_most_once_per_gap_and_never_twice() -> None:
    now = [100.0]
    announcer = search_cues.TitleAnnouncer(clock=lambda: now[0])
    assert announcer.report("KEXP") == ("Checking KEXP.", True)
    now[0] += 0.5
    assert announcer.report("WFMU") == ("Checking WFMU.", False)  # shown, not spoken
    assert announcer.report("kexp") == ("", False)  # a mirror's repeat is ignored
    assert announcer.report("   ") == ("", False)
    now[0] += 2.0
    assert announcer.report("NTS") == ("Checking NTS.", True)
    announcer.reset()
    assert announcer.report("KEXP")[1] is True


def test_a_long_or_messy_name_is_made_one_short_sentence() -> None:
    sentence = search_cues.checking_sentence("A  very\n" + "long " * 40)
    assert sentence.startswith("Checking A very long") and len(sentence) <= 100
    assert "\n" not in sentence and "tick" not in sentence.lower()


def test_check_urls_reports_each_verdict_and_survives_a_bad_callback() -> None:
    seen: list[tuple[str, str]] = []

    def get(url: str, _timeout: float) -> live_check.HttpReply:
        return live_check.HttpReply(
            200, {"Content-Type": "audio/mpeg", "icy-name": f"Name of {url[-1]}"}, MP3, url
        )

    def on_verdict(url: str, verdict: live_check.Verdict) -> None:
        seen.append((url, verdict.name))
        raise RuntimeError("a window that failed to draw")

    urls = ["http://a.example/1", "http://a.example/2"]
    verdicts = live_check.check_urls(urls, get, on_verdict=on_verdict)
    assert sorted(seen) == [
        ("http://a.example/1", "Name of 1"),
        ("http://a.example/2", "Name of 2"),
    ]
    assert all(v.state == live_check.LIVE for v in verdicts.values())


def test_the_three_cues_are_in_the_pack_as_short_distinct_clips() -> None:
    manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
    names = {}
    for event in (
        SoundEvent.RADIO_SEARCH_EMPTY,
        SoundEvent.RADIO_SEARCH_FAILED,
        SoundEvent.RADIO_SEARCH_WORKING,
    ):
        wav = PACK / manifest["events"][str(event)]
        assert wav.is_file()
        with wave.open(str(wav)) as handle:
            assert handle.getnframes() / handle.getframerate() < 0.5  # short
        names[event] = wav.read_bytes()
    assert len(set(names.values())) == 3  # three different sounds
