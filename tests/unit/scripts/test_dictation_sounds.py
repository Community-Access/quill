"""The four Windows Dictation earcons are generated, never hand-edited."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]


def _generator():
    spec = importlib.util.spec_from_file_location(
        "generate_dictation_sounds", _REPO / "scripts" / "generate_dictation_sounds.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_committed_earcons_match_the_generator() -> None:
    assert _generator().drifted() == []


def test_the_ink_pack_maps_every_dictation_event_to_its_file() -> None:
    from quill.ui.windows_dictation_commands import DICTATION_CUES

    manifest = json.loads(
        (_REPO / "quill/assets/sound_packs/ink/manifest.json").read_text(encoding="utf-8")
    )
    for event in DICTATION_CUES.values():
        assert manifest["events"][str(event)] == f"{event}.wav"


def test_the_phrase_cue_is_the_shortest_and_quietest() -> None:
    """Heard hundreds of times an hour, so it must be the least intrusive."""
    sounds = _generator().sounds()
    phrase = sounds["windows_dictation_phrase.wav"]
    for name, samples in sounds.items():
        if name != "windows_dictation_phrase.wav":
            assert len(phrase) < len(samples)
            assert max(map(abs, phrase)) < max(map(abs, samples))
