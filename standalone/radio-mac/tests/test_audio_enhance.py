"""Tests for quill_radio_mac.core.audio_enhance.

Covers the pieces ported from upstream ``quill.core.audio_enhance``:
EQ_PRESETS content, clamp_eq_gain range clamping, build_filter_graph's
exact filter-graph strings (derived by hand from the upstream builder,
not guessed), filter ordering (mono -> EQ -> compressor -> smart speed
-> night mode), and EnhanceError's coded-error rendering. No wx, no IO,
no subprocess -- this port drops the ffmpeg relay entirely.
"""

from __future__ import annotations

from quill_radio_mac.core.audio_enhance import (
    EQ_BAND_MAX_DB,
    EQ_BAND_MIN_DB,
    EQ_PRESETS,
    EnhanceError,
    build_filter_graph,
    clamp_eq_gain,
)


def test_eq_presets_match_upstream_values():
    assert EQ_PRESETS["Flat"] == (0.0, 0.0, 0.0)
    assert EQ_PRESETS["Bass Boost"] == (7.0, 0.0, 1.0)
    assert EQ_PRESETS["Voice Clarity"] == (-3.0, 4.0, 2.0)
    assert EQ_PRESETS["Podcast"] == (-4.0, 3.0, 0.0)
    assert EQ_PRESETS["Small Speakers"] == (6.0, 0.0, 2.0)
    assert EQ_PRESETS["Late Night"] == (2.0, 0.0, -3.0)
    assert len(EQ_PRESETS) == 6


def test_clamp_eq_gain_within_range_unchanged():
    assert clamp_eq_gain(4.5) == 4.5
    assert clamp_eq_gain(0.0) == 0.0


def test_clamp_eq_gain_clamps_to_band_limits():
    assert clamp_eq_gain(999.0) == EQ_BAND_MAX_DB
    assert clamp_eq_gain(-999.0) == EQ_BAND_MIN_DB
    assert clamp_eq_gain(12.0) == 12.0
    assert clamp_eq_gain(-12.0) == -12.0


def test_build_filter_graph_empty_when_nothing_engaged():
    assert build_filter_graph(0.0, 0.0, 0.0, compressor_enabled=False) == ""


def test_build_filter_graph_flat_preset_is_still_empty():
    bass, mid, treble = EQ_PRESETS["Flat"]
    assert build_filter_graph(bass, mid, treble, compressor_enabled=False) == ""


def test_build_filter_graph_bass_boost_preset_skips_zero_gain_band():
    bass, mid, treble = EQ_PRESETS["Bass Boost"]
    graph = build_filter_graph(bass, mid, treble, compressor_enabled=False)
    # Mid gain is 0.0 in this preset, so its band is omitted entirely.
    assert graph == "equalizer=f=100:t=q:w=1:g=7.0,equalizer=f=8000:t=q:w=1:g=1.0"


def test_build_filter_graph_eq_plus_compressor_combo():
    bass, mid, treble = EQ_PRESETS["Bass Boost"]
    graph = build_filter_graph(bass, mid, treble, compressor_enabled=True)
    assert graph == (
        "equalizer=f=100:t=q:w=1:g=7.0,"
        "equalizer=f=8000:t=q:w=1:g=1.0,"
        "acompressor=threshold=-18dB:ratio=3:attack=20:release=250:makeup=2"
    )


def test_build_filter_graph_voice_clarity_preset_uses_all_three_bands():
    bass, mid, treble = EQ_PRESETS["Voice Clarity"]
    graph = build_filter_graph(bass, mid, treble, compressor_enabled=False)
    assert graph == (
        "equalizer=f=100:t=q:w=1:g=-3.0,"
        "equalizer=f=1000:t=q:w=1:g=4.0,"
        "equalizer=f=8000:t=q:w=1:g=2.0"
    )


def test_build_filter_graph_mono_and_night_mode_with_no_eq():
    graph = build_filter_graph(
        0.0, 0.0, 0.0, compressor_enabled=False, mono_enabled=True, night_mode_enabled=True
    )
    assert graph == "pan=mono|c0=0.5*c0+0.5*c1,dynaudnorm=f=250:g=15:p=0.9"


def test_build_filter_graph_smart_speed_after_compressor():
    graph = build_filter_graph(
        0.0, 0.0, 0.0, compressor_enabled=True, smart_speed_enabled=True
    )
    assert graph == (
        "acompressor=threshold=-18dB:ratio=3:attack=20:release=250:makeup=2,"
        "silenceremove=stop_periods=-1:stop_duration=0.5:stop_threshold=-40dB"
    )


def test_build_filter_graph_full_combo_ordering():
    # mono first, then EQ bands, then compressor, then smart speed, then
    # night mode last -- exactly the order upstream's docstring specifies.
    graph = build_filter_graph(
        7.0,
        0.0,
        1.0,
        compressor_enabled=True,
        smart_speed_enabled=True,
        mono_enabled=True,
        night_mode_enabled=True,
    )
    assert graph == (
        "pan=mono|c0=0.5*c0+0.5*c1,"
        "equalizer=f=100:t=q:w=1:g=7.0,"
        "equalizer=f=8000:t=q:w=1:g=1.0,"
        "acompressor=threshold=-18dB:ratio=3:attack=20:release=250:makeup=2,"
        "silenceremove=stop_periods=-1:stop_duration=0.5:stop_threshold=-40dB,"
        "dynaudnorm=f=250:g=15:p=0.9"
    )


def test_build_filter_graph_clamps_out_of_range_gains():
    graph = build_filter_graph(999.0, 0.0, -999.0, compressor_enabled=False)
    assert graph == (
        "equalizer=f=100:t=q:w=1:g=12.0,"
        "equalizer=f=8000:t=q:w=1:g=-12.0"
    )


def test_enhance_error_renders_coded_message():
    error = EnhanceError("libmpv could not apply the filter graph")
    assert error.code == "QUILL-RADIO-ENHANCE-FAILED"
    assert str(error) == "[QUILL-RADIO-ENHANCE-FAILED] libmpv could not apply the filter graph"
