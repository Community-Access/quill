"""The voice browser's voice lists and per-engine rate and speed (GATE-11 extract).

Kept beside :mod:`quill.ui.voice_browser_dialog`, which owns the controls:
these functions only decide which engine a control's value belongs to, so
the dialog stays one shape while engines with different ranges share a spin.
"""

from __future__ import annotations

from typing import Any

#: engine -> (label, minimum, maximum, step, settings attribute) for the speed spin.
#: Phonon holds together only between 0.85 and 1.3 times normal speed, so its
#: range says so rather than offering speeds the model breaks up at.
SPEED_RANGES: dict[str, tuple[str, float, float, float, str]] = {
    "kokoro": ("Speed (0.5-2.0):", 0.5, 2.0, 0.1, "read_aloud_kokoro_speed"),
    "phonon": ("Speed (0.85-1.3):", 0.85, 1.3, 0.05, "read_aloud_phonon_speed"),
}

#: engine -> (settings attribute, default) for engines on the shared rate spin.
_RATE_ATTRS: dict[str, tuple[str, int]] = {
    "dectalk": ("read_aloud_dectalk_rate", 200),
    "espeak": ("read_aloud_espeak_rate", 175),
    "macos": ("read_aloud_macos_rate", 175),
}


def configure_speed(label: Any, spin: Any, eng: str, settings: object) -> None:
    """Point the shared speed spin at *eng*'s range and saved value."""
    text, low, high, step, attr = SPEED_RANGES[eng]
    label.SetLabel(text)
    spin.SetRange(low, high)
    spin.SetIncrement(step)
    spin.SetValue(getattr(settings, attr, 1.0))


def store_speed(eng: str, settings: object, value: float) -> None:
    """Write the speed spin's *value* to the setting *eng* owns."""
    _label, low, high, _step, attr = SPEED_RANGES.get(eng, SPEED_RANGES["kokoro"])
    setattr(settings, attr, max(low, min(high, float(value))))


def collect(
    eng: str, settings: object, *, rate: int, volume: int, pitch: int, speed: float
) -> dict:
    """The result fields: the live controls for *eng*, saved values for the rest."""
    values: dict[str, Any] = {"rate": rate, "volume": volume, "pitch": pitch}
    for engine, (attr, default) in _RATE_ATTRS.items():
        values[f"{engine}_rate"] = rate if eng == engine else getattr(settings, attr, default)
    for engine, (_label, _lo, _hi, _step, attr) in SPEED_RANGES.items():
        values[f"{engine}_speed"] = speed if eng == engine else getattr(settings, attr, 1.0)
    return values


def engine_voices(eng: str, *, piper_model_dir: Any = None, elevenlabs_api_key: str = "") -> list:
    """The voices *eng* offers, shared by the voice browser and the batch wizard."""
    from quill.core import read_aloud as ra

    listers = {
        "dectalk": ra.list_dectalk_voices,
        "piper": lambda: ra.list_piper_catalog_voices(piper_model_dir),
        "kokoro": ra.list_kokoro_voices,
        "phonon": ra.list_phonon_voices,
        "espeak": ra.list_espeak_voices,
        "macos": ra.list_macos_voices,
        "elevenlabs": lambda: ra.list_elevenlabs_voices(elevenlabs_api_key),
    }
    # sapi5: every installed system voice, whatever its language (#813 follow-on).
    return listers.get(eng, ra.list_voices)()
