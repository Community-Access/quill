"""Unit tests for ``quill.core.media.dsp`` (EQ + DSP filter compilation)."""

from __future__ import annotations

from quill.core.media import (
    EQ_BANDS_HZ,
    EQ_PRESETS,
    DspSettings,
    Equalizer,
    build_audio_filters,
)


def test_presets_have_ten_bands() -> None:
    assert len(EQ_BANDS_HZ) == 10
    for name, gains in EQ_PRESETS.items():
        assert len(gains) == 10, name


def test_equalizer_clamps_and_pads() -> None:
    eq = Equalizer(gains=(99, -99, 3))  # over-range + short
    assert eq.gains[0] == 12.0
    assert eq.gains[1] == -12.0
    assert eq.gains[2] == 3.0
    assert len(eq.gains) == 10  # padded with zeros


def test_preset_lookup() -> None:
    assert Equalizer.preset("bass").name == "bass"
    assert Equalizer.preset("bass").is_flat is False
    assert Equalizer.preset("flat").is_flat is True
    assert Equalizer.preset("nonexistent").name == "flat"


def test_default_settings_produce_no_filters() -> None:
    assert build_audio_filters(DspSettings()) == []


def test_flat_eq_produces_no_filters() -> None:
    assert build_audio_filters(DspSettings(equalizer=Equalizer.preset("flat"))) == []


def test_eq_bands_compile() -> None:
    eq = Equalizer(gains=(6, 0, 0, 0, 0, 0, 0, 0, 0, -6))
    filters = build_audio_filters(DspSettings(equalizer=eq))
    assert any("equalizer=f=31:" in f and "g=6" in f for f in filters)
    assert any("equalizer=f=16000:" in f and "g=-6" in f for f in filters)
    assert len(filters) == 2  # only the two non-zero bands


def test_boost_normalize_skip_silence_order() -> None:
    settings = DspSettings(boost_db=6, normalize=True, skip_silence=True)
    filters = build_audio_filters(settings)
    assert filters == [
        "volume=6dB",
        "dynaudnorm",
        "silenceremove=stop_periods=-1:stop_duration=1:stop_threshold=-50dB",
    ]


def test_boost_clamped_non_negative() -> None:
    assert DspSettings(boost_db=-5).boost_db == 0.0
    assert DspSettings(boost_db=99).boost_db == 12.0
