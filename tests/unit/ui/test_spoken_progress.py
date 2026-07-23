"""Tests for the spoken download milestones (quill.ui.spoken_progress)."""

from __future__ import annotations

from quill.ui.spoken_progress import MilestoneSpeaker


def test_speaks_interior_milestones_once_each() -> None:
    speaker = MilestoneSpeaker(label="Downloading FFmpeg")
    # 0 and sub-milestone values stay silent.
    assert speaker.phrase_for(0) is None
    assert speaker.phrase_for(24) is None
    # First crossing of each interior boundary speaks once.
    assert speaker.phrase_for(25) == "Downloading FFmpeg 25 percent."
    assert speaker.phrase_for(26) is None  # same bucket -> silent
    assert speaker.phrase_for(50) == "Downloading FFmpeg 50 percent."
    assert speaker.phrase_for(75) == "Downloading FFmpeg 75 percent."
    # 100 is left to the caller's completion announcement.
    assert speaker.phrase_for(100) is None


def test_forward_jump_speaks_only_the_reached_bucket() -> None:
    speaker = MilestoneSpeaker(label="Installing Vosk")
    assert speaker.phrase_for(10) is None
    # Jumping 10 -> 60 speaks the highest bucket reached once, not a backlog.
    assert speaker.phrase_for(60) == "Installing Vosk 50 percent."
    assert speaker.phrase_for(70) is None  # still within the 50 bucket


def test_backward_and_indeterminate_updates_stay_silent() -> None:
    speaker = MilestoneSpeaker(label="X")
    assert speaker.phrase_for(50) == "X 50 percent."
    assert speaker.phrase_for(30) is None  # backward -> silent
    assert speaker.phrase_for(-1) is None  # indeterminate gauge -> silent


def test_without_a_label_speaks_a_bare_percent() -> None:
    speaker = MilestoneSpeaker()
    assert speaker.phrase_for(25) == "25 percent."


def test_custom_step_changes_the_milestones() -> None:
    speaker = MilestoneSpeaker(label="Y", step_percent=50)
    assert speaker.phrase_for(25) is None
    assert speaker.phrase_for(50) == "Y 50 percent."
    assert speaker.phrase_for(75) is None  # same 50 bucket under a 50% step
