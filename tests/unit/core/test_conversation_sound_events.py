"""The nine conversation cues must exist as SoundEvents and ship in the pack."""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.sound_events import SoundEvent
from quill.core.speech import conversation as conv

_ROOT = Path(__file__).resolve().parents[3]

_CUES = (
    conv.CUE_ON,
    conv.CUE_OFF,
    conv.CUE_WAKE,
    conv.CUE_LISTEN,
    conv.CUE_REVIEW,
    conv.CUE_READY,
    conv.CUE_IDLE,
    conv.CUE_TICK,
    conv.CUE_ERROR,
)


def test_every_cue_is_a_registered_sound_event() -> None:
    valid = {e.value for e in SoundEvent}
    for cue in _CUES:
        assert cue in valid, f"{cue} missing from SoundEvent"


def test_ink_pack_maps_and_ships_every_cue() -> None:
    pack = _ROOT / "quill" / "assets" / "sound_packs" / "ink"
    events = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))["events"]
    for cue in _CUES:
        assert cue in events, f"{cue} not mapped in ink manifest"
        assert (pack / events[cue]).is_file(), f"missing WAV for {cue}"


def test_cues_are_labeled_in_the_sound_events_dialog() -> None:
    src = (_ROOT / "quill" / "ui" / "sound_events_dialog.py").read_text(encoding="utf-8")
    for cue in _CUES:
        assert f'"{cue}"' in src, f"{cue} not labeled/ordered in the dialog"
