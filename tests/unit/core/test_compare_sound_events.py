"""Tests for compare-mode sound event constants and Ink pack mapping (#186).

Pure constants/manifest checks; no wx dependency.
"""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.sound_events import SoundEvent

_COMPARE_EVENTS = (
    SoundEvent.COMPARE_ENTER_MODE,
    SoundEvent.COMPARE_EXIT_MODE,
    SoundEvent.COMPARE_NEXT_DIFFERENCE,
    SoundEvent.COMPARE_PREVIOUS_DIFFERENCE,
    SoundEvent.COMPARE_NO_MORE_DIFFERENCES,
)

_EXPECTED_IDS = {
    "compare_enter_mode",
    "compare_exit_mode",
    "compare_next_difference",
    "compare_previous_difference",
    "compare_no_more_differences",
}


def test_compare_events_exist_with_expected_ids() -> None:
    assert {str(e) for e in _COMPARE_EVENTS} == _EXPECTED_IDS


def test_compare_event_ids_are_unique() -> None:
    ids = [str(e) for e in _COMPARE_EVENTS]
    assert len(ids) == len(set(ids)) == 5


def test_bundled_ink_pack_maps_every_compare_event_uniquely() -> None:
    manifest_path = (
        Path(__file__).resolve().parents[3]
        / "quill"
        / "assets"
        / "sound_packs"
        / "ink"
        / "manifest.json"
    )
    events = json.loads(manifest_path.read_text(encoding="utf-8"))["events"]
    # Every compare event is mapped...
    for eid in _EXPECTED_IDS:
        assert eid in events, f"Ink pack missing compare event {eid}"
    # ...to a distinct WAV (no two compare events share a sound).
    compare_files = [events[eid] for eid in _EXPECTED_IDS]
    assert len(set(compare_files)) == len(compare_files)
