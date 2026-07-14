"""The voice-preview 'generating' cue must exist as a SoundEvent and ship in the pack."""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.sound_events import SoundEvent

_ROOT = Path(__file__).resolve().parents[3]


def test_voice_preview_generating_is_a_registered_sound_event() -> None:
    valid = {e.value for e in SoundEvent}
    assert "voice_preview_generating" in valid


def test_ink_pack_maps_voice_preview_generating() -> None:
    pack = _ROOT / "quill" / "assets" / "sound_packs" / "ink"
    events = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))["events"]
    assert "voice_preview_generating" in events
    assert (pack / events["voice_preview_generating"]).is_file()


def test_voice_preview_generating_is_labeled_in_the_sound_events_dialog() -> None:
    src = (_ROOT / "quill" / "ui" / "sound_events_dialog.py").read_text(encoding="utf-8")
    assert '"voice_preview_generating"' in src
