"""Tests for the audio-converter Advanced DSP composition (#1255 §6)."""

from __future__ import annotations

from quill.core.audio import dsp as d
from quill.core.audio.dsp import DspOptions


def test_default_options_add_no_filters() -> None:
    opts = DspOptions()
    assert d.build_dsp_filters(opts) == ()
    assert opts.is_active() is False


def test_high_pass_and_trim() -> None:
    f = d.build_dsp_filters(DspOptions(high_pass=True, trim_silence=True))
    assert any("highpass" in x for x in f)
    assert any("silenceremove" in x for x in f)


def test_gain_emits_volume() -> None:
    f = d.build_dsp_filters(DspOptions(gain_db=-3.5))
    assert "volume=-3.5dB" in f


def test_tempo_uses_atempo_and_ignores_unity() -> None:
    assert d.build_dsp_filters(DspOptions(tempo=1.0)) == ()
    f = d.build_dsp_filters(DspOptions(tempo=1.5))
    assert any("atempo" in x for x in f)


def test_loudness_targets() -> None:
    ab = d.build_dsp_filters(DspOptions(loudness="audiobook"))
    assert any("loudnorm=I=-20.0" in x for x in ab)
    pod = d.build_dsp_filters(DspOptions(loudness="podcast"))
    assert any("loudnorm=I=-16.0" in x for x in pod)
    assert d.build_dsp_filters(DspOptions(loudness="")) == ()


def test_compressor_and_leveler() -> None:
    f = d.build_dsp_filters(DspOptions(compressor=True, leveler=True))
    assert any("acompressor" in x for x in f)
    assert any("dynaudnorm" in x for x in f)


def test_fade_in_and_out() -> None:
    f = d.build_dsp_filters(DspOptions(fade_in_s=2.0, fade_out_s=3.0))
    joined = ",".join(f)
    assert "afade=t=in:st=0:d=2" in joined
    # Fade-out via reverse-fade-reverse (no duration probe needed).
    assert f.count("areverse") == 2
    assert "d=3" in joined


def test_filter_order_is_stable_clean_then_shape_then_loudness_then_fades() -> None:
    f = d.build_dsp_filters(
        DspOptions(high_pass=True, gain_db=2, compressor=True, loudness="podcast", fade_in_s=1.0)
    )
    order = [
        next(i for i, x in enumerate(f) if key in x)
        for key in ("highpass", "volume", "acompressor", "loudnorm", "afade")
    ]
    assert order == sorted(order)  # cleaning -> shaping -> loudness -> fades


def test_is_active_true_when_any_option_set() -> None:
    assert DspOptions(compressor=True).is_active() is True
    assert DspOptions(gain_db=1).is_active() is True


def test_loudness_choices_pairs() -> None:
    choices = d.loudness_choices()
    values = {v for v, _label in choices}
    assert values == {"", "audiobook", "podcast"}
    for _v, label in choices:
        assert label
