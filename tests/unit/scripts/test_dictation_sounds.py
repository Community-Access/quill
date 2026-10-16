"""The five Windows Dictation earcons are generated, never hand-edited."""

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


def test_the_phrase_cue_has_no_attack_to_hear_as_a_letter() -> None:
    """A cue at full volume within a few milliseconds is heard as a consonant:
    the first one was reported as a spoken "c" before every read-back."""
    generator = _generator()
    phrase = generator.sounds()["windows_dictation_phrase.wav"]
    peak = max(map(abs, phrase))
    ten_ms = generator.SAMPLE_RATE // 100
    # Ten milliseconds in, it is still well under half of where it is going.
    assert max(map(abs, phrase[:ten_ms])) < peak * 0.5
    assert generator.PHRASE_ATTACK_MS >= 20


_TICK = "windows_dictation_working.wav"


def test_the_phrase_cue_is_the_shortest_and_quietest() -> None:
    """Heard hundreds of times an hour, so it must be the least intrusive of
    the session cues. Only the working tick, which repeats every second, is
    smaller (the next test)."""
    sounds = _generator().sounds()
    phrase = sounds["windows_dictation_phrase.wav"]
    for name, samples in sounds.items():
        if name not in ("windows_dictation_phrase.wav", _TICK):
            assert len(phrase) < len(samples)
            assert max(map(abs, phrase)) < max(map(abs, samples))


def test_the_working_tick_is_shorter_and_quieter_than_everything() -> None:
    """Once a second while a phrase is recognised, and the microphone is not
    listened to while it plays: the least of all, and still a tone."""
    generator = _generator()
    sounds = generator.sounds()
    tick = sounds[_TICK]
    for name, samples in sounds.items():
        if name != _TICK:
            assert len(tick) < len(samples)
            assert max(map(abs, tick)) < max(map(abs, samples))
    ten_ms = generator.SAMPLE_RATE // 100
    assert max(map(abs, tick[:ten_ms])) < max(map(abs, tick)) * 0.5
    assert len(tick) <= generator.SAMPLE_RATE // 10  # a tenth of a second at most
