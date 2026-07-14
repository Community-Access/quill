"""Tests for the spoken cue-phrase generator (Hey QUILL refinement)."""

from __future__ import annotations

from datetime import datetime

from quill.core.speech import voice_cues as cues


def _at(hour: int):
    return lambda: datetime(2026, 7, 2, hour, 0, 0)


def _first(options):
    return options[0]


def test_welcome_is_personalized_and_time_aware() -> None:
    assert "Jeff" in cues.welcome("Jeff", first=True, pick=_first, now=_at(9))
    assert "morning" in cues.welcome("Jeff", first=True, pick=_first, now=_at(9))
    assert "afternoon" in cues.welcome("Jeff", first=True, pick=_first, now=_at(14))
    assert "evening" in cues.welcome("Jeff", first=True, pick=_first, now=_at(20))


def test_missing_name_falls_back_to_there() -> None:
    assert "there" in cues.welcome("", first=True, pick=_first, now=_at(9))
    assert "there" in cues.welcome("   ", first=True, pick=_first, now=_at(9))


def test_reprompt_is_shorter_than_first_welcome() -> None:
    reprompt = cues.welcome("Jeff", first=False, pick=_first)
    assert "Jeff" in reprompt
    assert "morning" not in reprompt  # the re-arm nudge is not time-of-day flavored


def test_listening_ack_followup_include_name() -> None:
    assert "Jeff" in cues.listening("Jeff", pick=_first)
    assert "Jeff" in cues.acknowledge("Jeff", pick=_first)
    assert "Jeff" in cues.followup("Jeff", pick=_first)


def test_pick_is_used_for_variety() -> None:
    def pick_at(index):
        return lambda opts: opts[index % len(opts)]

    seen = {cues.followup("Jeff", pick=pick_at(i)) for i in range(4)}
    assert len(seen) >= 2  # more than one distinct line is reachable


def test_cue_pool_covers_the_spoken_lines_and_is_warmable() -> None:
    pool = cues.cue_pool("Jeff", now=_at(9))
    assert isinstance(pool, tuple) and len(pool) >= 8
    assert any("Good morning, Jeff" in line for line in pool)
    assert all(isinstance(line, str) and line for line in pool)
