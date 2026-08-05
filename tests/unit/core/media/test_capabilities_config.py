"""Unit tests for the capability matrix and config defaults."""

from __future__ import annotations

from quill.core.media import MEDIA_DEFAULTS, capabilities_for, default_config, resolve


def test_libmpv_has_dsp() -> None:
    caps = capabilities_for("libmpv")
    assert caps.equalizer and caps.gapless and caps.pitch_preserving_speed


def test_wx_media_is_transport_only() -> None:
    caps = capabilities_for("wx.media")
    assert not caps.equalizer and not caps.skip_silence and not caps.gapless


def test_unknown_backend_is_conservative() -> None:
    caps = capabilities_for("mystery")
    assert not any((
        caps.equalizer,
        caps.volume_boost,
        caps.skip_silence,
        caps.gapless,
        caps.crossfade,
    ))


def test_defaults_are_complete_and_copied() -> None:
    config = default_config()
    assert config == MEDIA_DEFAULTS
    assert config is not MEDIA_DEFAULTS  # a copy, not the shared dict
    assert config["media_default_speed"] == 1.0
    assert config["media_skip_forward_seconds"] == 30


def test_resolve_overlays_known_keys_only() -> None:
    merged = resolve({"media_default_speed": 1.5, "unrelated_key": "x"})
    assert merged["media_default_speed"] == 1.5
    assert "unrelated_key" not in merged
    assert merged["media_skip_back_seconds"] == 15  # untouched default
