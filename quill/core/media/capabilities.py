"""Backend capability matrix (``player.md`` Section 12).

A pure description of what each playback backend can do, so the UI can enable or
disable DSP controls (with a spoken reason) instead of letting a feature silently
no-op. ``libmpv`` is the bundled default and supports the rich DSP path; the
``wx.media`` fallback is transport-only.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class EngineCapabilities:
    """What a backend supports beyond core transport/seek/chapters."""

    backend: str
    pitch_preserving_speed: bool
    equalizer: bool
    volume_boost: bool
    skip_silence: bool
    gapless: bool
    crossfade: bool


_MPV = EngineCapabilities(
    backend="libmpv",
    pitch_preserving_speed=True,
    equalizer=True,
    volume_boost=True,
    skip_silence=True,
    gapless=True,
    crossfade=True,
)

_WX = EngineCapabilities(
    backend="wx.media",
    pitch_preserving_speed=False,
    equalizer=False,
    volume_boost=False,
    skip_silence=False,
    gapless=False,
    crossfade=False,
)

_BY_BACKEND = {_MPV.backend: _MPV, _WX.backend: _WX}


def capabilities_for(backend: str) -> EngineCapabilities:
    """Return the capability set for ``backend`` (``"libmpv"`` or ``"wx.media"``).

    An unknown backend gets the conservative ``wx.media`` set, so a feature is
    never assumed available.
    """
    known = _BY_BACKEND.get(backend)
    return known if known is not None else replace(_WX, backend=backend)


__all__ = ["EngineCapabilities", "capabilities_for"]
