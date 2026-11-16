"""Compression strength: Earshot's three levels, Radio's compressor untouched
(earshot.md E6). Pure."""

from __future__ import annotations

from quill.core.audio.compressor_levels import (
    COMPRESSION_LEVELS,
    LEGACY_COMPRESSOR_FILTER,
    compressor_filters,
    compressor_value,
)
from quill.core.audio_enhance import build_filter_graph, is_enhancement_active
from quill.core.podcasts.models import PodcastSettings


def test_radio_true_is_the_old_compressor() -> None:
    assert compressor_filters(True) == [LEGACY_COMPRESSOR_FILTER]
    assert build_filter_graph(0, 0, 0, compressor_enabled=True) == LEGACY_COMPRESSOR_FILTER


def test_each_level_has_its_own_filter() -> None:
    assert len(set(COMPRESSION_LEVELS.values())) == 3
    for level, graph in COMPRESSION_LEVELS.items():
        assert build_filter_graph(0, 0, 0, compressor_enabled=level) == graph
    assert "threshold=-36dB:ratio=4" in COMPRESSION_LEVELS["strong"]


def test_off_is_nothing() -> None:
    assert compressor_filters(False) == []
    assert compressor_filters("nonsense") == []
    assert not is_enhancement_active(0, 0, 0, compressor_enabled=False)
    assert is_enhancement_active(0, 0, 0, compressor_enabled="balanced")


def test_a_podcast_passes_off_or_its_level() -> None:
    assert compressor_value(False, "strong") is False
    assert compressor_value(True, "strong") == "strong"
    assert compressor_value(True, "bogus") == "light"
    settings = PodcastSettings(compressor_enabled=True, compression_level="balanced")
    assert settings.compressor() == "balanced"
    assert PodcastSettings.from_dict({"compression_level": "loud"}).compression_level == "light"
    assert PodcastSettings.from_dict(settings.to_dict()).compression_level == "balanced"
