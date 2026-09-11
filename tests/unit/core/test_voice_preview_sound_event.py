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


def test_voice_preview_generating_is_labeled_and_reachable() -> None:
    """Asserted against the catalogue rather than a file's text: the checklist
    became the Sound Scheme window, and what matters is that the cue has a name
    and a group, so somebody can find it, hear it and switch it off."""
    from quill.ui.sound_event_labels import GROUP_FOR, LABELS

    assert LABELS["voice_preview_generating"]
    assert GROUP_FOR["voice_preview_generating"]


def test_voice_preview_has_a_sound_of_its_own() -> None:
    """It shared ai_start.wav with the assistant's thinking cue, so two
    different waits made one noise."""
    import json

    pack = _ROOT / "quill" / "assets" / "sound_packs" / "ink"
    events = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))["events"]
    assert events["voice_preview_generating"] != events["ai_thinking_started"]
