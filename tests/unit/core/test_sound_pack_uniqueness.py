"""No two events may sound the same.

Reported by ear, 2026-09-10: "shouldn't all sounds be unique, I think I heard
one repeated." They were not. Three pairs in the bundled pack were the same
sound in two places, and none of them was a copy-paste mistake -- each was a
plausible design choice made twice by different people at different times:

* ``app_exiting`` was ``_bell_seq([659, 523, 392])``, which is note for note
  what ``conversation_off`` had been playing for months.
* ``question`` was ``_bell_seq([587, 880])``, which is ``conversation_wake``.
* ``voice_preview_generating`` had no file of its own at all; the manifest
  pointed it at ``ai_start.wav``, so the assistant thinking and a voice engine
  warming up were one sound.

That is exactly the failure an earcon set cannot survive, and exactly the one
nobody notices while writing the code: you hear each sound as you make it, in
isolation, and never next to the one it collides with. So it needs a gate.

**Three checks, coarsest first.** No two files byte-identical; no two events
pointing at one file; and no two sounds *perceptually* alike -- measured on a
crude loudness-and-pitch contour, which is enough to catch two cues built from
the same notes even when the bytes differ.

Deliberately exempt: the **ladders**. Progress at five-percent steps, the twelve
copy-tray slots, the ten bookmark slots and the indent depths are meant to be
neighbours -- adjacent rungs of one scale, where "almost the same, one step up"
is the whole design. A gate that failed them would be measuring the wrong thing.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import struct
import wave
from collections import defaultdict
from pathlib import Path

import pytest

_PACK = Path(__file__).resolve().parents[3] / "quill" / "assets" / "sound_packs" / "ink"

#: Families whose members are *supposed* to be neighbours: one scale, stepped.
_LADDERS = ("progress_", "copy_slot_", "bookmark_slot_", "indent_")

#: Below this, two sounds are alike enough that a listener would have to think
#: about which one they just heard -- which is the whole cost an earcon exists
#: to avoid. Calibrated against the three real collisions above, which scored
#: 0.50, 0.62 and 0.83, and against the closest surviving legitimate pair.
_TOO_ALIKE = 0.75

#: Windows in the contour. Eight is enough to tell a rise from a fall and a
#: single note from a pair, and coarse enough not to fail on a re-render.
_WINDOWS = 8


def _is_ladder(name: str) -> bool:
    return any(name.startswith(prefix) for prefix in _LADDERS)


def _contour(path: Path) -> tuple[float, list[tuple[float, float]]]:
    with wave.open(str(path), "rb") as handle:
        frames = handle.getnframes()
        rate = handle.getframerate()
        samples = struct.unpack(f"<{frames}h", handle.readframes(frames))
    window = max(1, frames // _WINDOWS)
    shape: list[tuple[float, float]] = []
    for index in range(_WINDOWS):
        chunk = samples[index * window : (index + 1) * window] or (0,)
        rms = math.sqrt(sum(value * value for value in chunk) / len(chunk)) / 32768
        crossings = sum(1 for a, b in zip(chunk, chunk[1:], strict=False) if (a < 0) != (b < 0))
        shape.append((rms, crossings / max(1, len(chunk)) * rate / 2))
    return frames / rate, shape


@pytest.fixture(scope="module")
def contours() -> dict[str, tuple[float, list[tuple[float, float]]]]:
    return {path.name: _contour(path) for path in sorted(_PACK.glob("*.wav"))}


def _distance(contours, first: str, second: str) -> float:
    length_a, shape_a = contours[first]
    length_b, shape_b = contours[second]
    longest = max(length_a, length_b)
    if longest > 0 and abs(length_a - length_b) / longest > 0.25:
        return 999.0  # a quarter apart in length is already tellable
    return sum(
        abs(rms_a - rms_b) * 6 + abs(hz_a - hz_b) / max(1.0, hz_a, hz_b)
        for (rms_a, hz_a), (rms_b, hz_b) in zip(shape_a, shape_b, strict=True)
    )


def test_no_two_sound_files_are_byte_identical() -> None:
    """The coarsest check, and the one a copy-paste would trip."""
    by_hash: dict[str, list[str]] = defaultdict(list)
    for path in sorted(_PACK.glob("*.wav")):
        by_hash[hashlib.sha256(path.read_bytes()).hexdigest()].append(path.name)
    duplicates = [names for names in by_hash.values() if len(names) > 1]
    assert duplicates == [], f"identical sound files: {duplicates}"


def test_no_two_events_share_one_sound_file() -> None:
    """Two events making one noise is two events the listener cannot tell apart,
    however good that noise is. ``voice_preview_generating`` shared the
    assistant's thinking cue until this gate existed."""
    events = json.loads((_PACK / "manifest.json").read_text(encoding="utf-8"))["events"]
    by_file: dict[str, list[str]] = defaultdict(list)
    for event, filename in events.items():
        by_file[filename].append(event)
    shared = {name: sorted(evs) for name, evs in by_file.items() if len(evs) > 1}
    assert shared == {}, f"one file, several events: {shared}"


def test_no_two_cues_are_perceptually_alike(contours) -> None:
    """The check the other two cannot make: different bytes, same sound.

    All three real collisions were this shape -- the same notes, written twice,
    months apart, by somebody who had no way to hear them side by side.
    """
    names = [name for name in contours if not _is_ladder(name)]
    alike = [
        (round(_distance(contours, a, b), 2), a, b)
        for a, b in itertools.combinations(sorted(names), 2)
        if _distance(contours, a, b) < _TOO_ALIKE
    ]
    assert alike == [], f"cues too alike to tell apart: {alike}"


def test_the_ladders_are_still_ladders(contours) -> None:
    """The exemption has to be earned: adjacent rungs should be *close*.

    If the progress steps stopped being neighbours the exemption would be
    hiding a real problem rather than describing a real design.
    """
    steps = [f"progress_{n}.wav" for n in range(5, 101, 5)]
    present = [name for name in steps if name in contours]
    assert len(present) > 4, "the progress ladder has gone missing"
    neighbours = [_distance(contours, a, b) for a, b in zip(present, present[1:], strict=False)]
    assert min(neighbours) < _TOO_ALIKE, "the progress ladder is no longer a ladder"


def test_every_mapped_file_exists(contours) -> None:
    """A manifest can outlive its files, and the event then silently does
    nothing -- which is indistinguishable from an event nobody set."""
    events = json.loads((_PACK / "manifest.json").read_text(encoding="utf-8"))["events"]
    missing = sorted(name for name in events.values() if name not in contours)
    assert missing == [], f"manifest names files that are not there: {missing}"
