"""Paired earcons in the Ink pack must be genuine opposites.

on/off, start/stop, enter/exit, and expand/delete should sound like exact
opposites: the negative cue is the exact time-reversal of the positive cue,
and the two are never byte-identical or perceptually identical (a steady tone
reversed sounds the same, which is the bug this guards against).
"""

from __future__ import annotations

import struct
import wave
from pathlib import Path

import pytest

_INK = Path(__file__).resolve().parents[3] / "quill" / "assets" / "sound_packs" / "ink"

# (positive cue, negative cue) — the negative must be the time-reverse of the positive.
_OPPOSITE_PAIRS = [
    ("browse_on", "browse_off"),
    ("expand", "delete"),
    ("ai_start", "ai_done"),
    ("rec_start", "rec_stop"),
    ("connect", "disconnect"),
    ("sound_on", "sound_off"),
    ("compare_enter", "compare_exit"),
]


def _samples(name: str) -> list[int]:
    path = _INK / f"{name}.wav"
    with wave.open(str(path), "rb") as w:
        frames = w.readframes(w.getnframes())
    return list(struct.unpack(f"<{len(frames) // 2}h", frames))


@pytest.mark.parametrize(("positive", "negative"), _OPPOSITE_PAIRS)
def test_negative_cue_is_exact_time_reverse(positive: str, negative: str) -> None:
    pos = _samples(positive)
    neg = _samples(negative)
    assert neg == pos[::-1], f"{negative}.wav must be the exact time-reverse of {positive}.wav"


@pytest.mark.parametrize(("positive", "negative"), _OPPOSITE_PAIRS)
def test_pair_is_not_perceptually_identical(positive: str, negative: str) -> None:
    pos = _samples(positive)
    neg = _samples(negative)
    # Byte-identical is an outright failure; identical-when-reversed means the
    # source is a symmetric/steady tone whose reversal sounds the same (the
    # browse_on/off bug). Require the source to actually change over time.
    assert pos != neg, f"{positive} and {negative} are identical"
    assert pos != pos[::-1], (
        f"{positive}.wav is its own reverse (steady/symmetric); its opposite "
        "cue would sound identical. Give it directional pitch movement."
    )
