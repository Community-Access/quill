"""Tests for verbosity channels (§7)."""

from __future__ import annotations

from quill.core.verbosity.channels import (
    ALWAYS_ON_CHANNELS,
    DEFAULT_CHANNELS,
    VISUAL_ALWAYS_ON_NAME,
    Channel,
    route_channels,
)


def test_default_mix_is_all_four_channels() -> None:
    assert DEFAULT_CHANNELS == (Channel.SPEECH | Channel.BRAILLE | Channel.SOUND | Channel.VISUAL)


def test_visual_is_the_always_on_floor() -> None:
    assert ALWAYS_ON_CHANNELS == Channel.VISUAL


def test_routing_always_includes_visual_even_from_nothing() -> None:
    routed = route_channels(Channel.NONE)
    assert Channel.VISUAL in routed


def test_routing_cannot_silence_visual() -> None:
    # A request for speech-only still keeps the visual floor.
    routed = route_channels(Channel.SPEECH)
    assert Channel.VISUAL in routed
    assert Channel.SPEECH in routed
    assert Channel.SOUND not in routed


def test_routing_preserves_requested_channels() -> None:
    routed = route_channels(Channel.SPEECH | Channel.SOUND)
    assert Channel.SPEECH in routed
    assert Channel.SOUND in routed
    assert Channel.VISUAL in routed


def test_visual_always_on_accessible_name_is_explicit() -> None:
    # §5 decision 2: the floor checkbox has a clear, fixed accessible name.
    assert "always on" in VISUAL_ALWAYS_ON_NAME.lower()
    assert "cannot be disabled" in VISUAL_ALWAYS_ON_NAME.lower()
