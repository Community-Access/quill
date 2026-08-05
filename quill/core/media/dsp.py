"""DSP model: equalizer, boost/normalize, skip-silence (PRD Sections 7.4-7.6).

Pure data + the ffmpeg/libmpv audio-filter strings they compile to, so the whole
DSP chain is unit-tested without an audio device. The UI hands the resulting
filter list to the libmpv backend (``af=...``); on the ``wx.media`` fallback these
features are unavailable and the settings simply aren't applied.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: The ten graphic-EQ band centre frequencies (Hz).
EQ_BANDS_HZ: tuple[int, ...] = (31, 62, 125, 250, 500, 1_000, 2_000, 4_000, 8_000, 16_000)

_MAX_GAIN_DB = 12.0
_MAX_BOOST_DB = 12.0

#: Named EQ presets: a gain (dB) per band, in ``EQ_BANDS_HZ`` order.
EQ_PRESETS: dict[str, tuple[float, ...]] = {
    "flat": (0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    "voice": (-3, -2, 0, 2, 3, 3, 2, 1, 0, -1),
    "bass": (6, 5, 4, 2, 0, 0, 0, 0, 0, 0),
    "treble": (0, 0, 0, 0, 0, 1, 2, 4, 5, 6),
    "night": (-2, -1, 0, 1, 2, 2, 0, -2, -4, -6),
    "podcast": (-6, -4, -1, 2, 3, 3, 2, 0, -2, -3),
}


def _clamp(value: float, limit: float) -> float:
    return max(-limit, min(limit, float(value)))


@dataclass(frozen=True, slots=True)
class Equalizer:
    """A 10-band graphic EQ: a gain in dB per band (clamped to +/-12)."""

    gains: tuple[float, ...] = field(default=(0.0,) * len(EQ_BANDS_HZ))
    name: str = "flat"

    def __post_init__(self) -> None:
        clamped = tuple(_clamp(g, _MAX_GAIN_DB) for g in self.gains[: len(EQ_BANDS_HZ)])
        clamped = clamped + (0.0,) * (len(EQ_BANDS_HZ) - len(clamped))
        object.__setattr__(self, "gains", clamped)

    @classmethod
    def preset(cls, name: str) -> Equalizer:
        """Build an equalizer from a named preset (unknown name -> flat)."""
        gains = EQ_PRESETS.get(name, EQ_PRESETS["flat"])
        resolved = name if name in EQ_PRESETS else "flat"
        return cls(gains=tuple(float(g) for g in gains), name=resolved)

    @property
    def is_flat(self) -> bool:
        return all(abs(g) < 0.01 for g in self.gains)


@dataclass(frozen=True, slots=True)
class DspSettings:
    """The full DSP chain state for the Audio panel."""

    equalizer: Equalizer | None = None
    boost_db: float = 0.0
    normalize: bool = False
    skip_silence: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "boost_db", max(0.0, _clamp(self.boost_db, _MAX_BOOST_DB)))


def build_audio_filters(settings: DspSettings) -> list[str]:
    """Compile ``settings`` into an ordered list of ffmpeg/libmpv filter strings.

    Order: equalizer -> boost -> normalize -> skip-silence. An all-flat EQ, zero
    boost, and the disabled toggles contribute nothing, so a default
    :class:`DspSettings` yields an empty list (no processing).
    """
    filters: list[str] = []
    eq = settings.equalizer
    if eq is not None and not eq.is_flat:
        for hz, gain in zip(EQ_BANDS_HZ, eq.gains, strict=False):
            if abs(gain) >= 0.01:
                filters.append(f"equalizer=f={hz}:width_type=o:width=1:g={gain:g}")
    if settings.boost_db > 0.01:
        filters.append(f"volume={settings.boost_db:g}dB")
    if settings.normalize:
        filters.append("dynaudnorm")
    if settings.skip_silence:
        filters.append("silenceremove=stop_periods=-1:stop_duration=1:stop_threshold=-50dB")
    return filters


__all__ = [
    "EQ_BANDS_HZ",
    "EQ_PRESETS",
    "DspSettings",
    "Equalizer",
    "build_audio_filters",
]
