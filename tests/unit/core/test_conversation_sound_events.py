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


def test_cues_are_labeled_and_grouped_for_the_scheme_window() -> None:
    """The catalogue moved out of the dialog into ``sound_event_labels`` when
    the checklist became the Sound Scheme window, so this asserts against the
    data rather than against a file's text -- which also means it now checks
    that the cue is *reachable* (in a group) rather than merely mentioned."""
    from quill.ui.sound_event_labels import GROUP_FOR, LABELS

    for cue in _CUES:
        assert cue in LABELS, f"{cue} has no label"
        assert cue in GROUP_FOR, f"{cue} is in no group, so the window cannot show it"
