"""Tests for the shared audio-output mode (stereo / mono / left / right).

This is an accessibility setting before it is a sound one. Mono exists so that
hard-panned content does not vanish for someone listening with one ear or one
hearing aid; the single-ear modes exist so the other ear stays free for a
screen reader. Both reasons apply to every app that plays audio, which is why
the vocabulary is shared rather than reinvented per app -- a listener should
not have to learn this twice.
"""

from quill.core.audio.channel_mode import (
    CYCLE_ORDER,
    DEFAULT_MODE,
    announce,
    description,
    is_active,
    label,
    next_mode,
    normalize,
)
from quill.core.audio_enhance import CHANNEL_MODES, build_filter_graph


def test_every_cycle_entry_is_a_real_filter_mode() -> None:
    """The vocabulary and the DSP must not drift apart."""
    assert set(CYCLE_ORDER) == set(CHANNEL_MODES)


def test_cycling_visits_every_mode_and_returns_home() -> None:
    seen = [DEFAULT_MODE]
    mode = DEFAULT_MODE
    for _ in range(len(CYCLE_ORDER) - 1):
        mode = next_mode(mode)
        seen.append(mode)
    assert seen == list(CYCLE_ORDER)
    assert next_mode(mode) == DEFAULT_MODE


def test_stereo_comes_first_because_it_is_the_way_back() -> None:
    assert CYCLE_ORDER[0] == "stereo"
    assert CYCLE_ORDER[1] == "mono"


def test_an_unknown_stored_mode_plays_normally() -> None:
    """A settings file outlives the code that wrote it. An unrecognised mode
    must play normally, never silence an ear."""
    for junk in ("", "  ", "quadraphonic", "MONO-ISH", None):
        assert normalize(junk) == "stereo"  # type: ignore[arg-type]
    assert next_mode("nonsense") == "mono"


def test_stored_modes_are_matched_case_and_space_insensitively() -> None:
    assert normalize("  Mono ") == "mono"
    assert normalize("LEFT") == "left"


def test_only_stereo_is_inactive() -> None:
    assert is_active("stereo") is False
    assert all(is_active(m) for m in ("mono", "left", "right"))


# -- what the listener hears -------------------------------------------------


def test_every_mode_has_a_label_and_an_explanation() -> None:
    for mode in CYCLE_ORDER:
        assert label(mode)
        assert description(mode)


def test_the_single_ear_modes_are_named_by_ear_not_by_channel() -> None:
    """ "Left ear only" is what the listener is choosing; "left channel" is an
    implementation detail they should never have to translate."""
    assert label("left") == "Left ear only"
    assert "left ear" in description("left").lower()
    assert "right ear silent" in description("left").lower()


def test_mono_explains_that_nothing_is_lost() -> None:
    """The whole point of mono here -- say it, rather than just "Mono"."""
    assert "nothing is lost" in description("mono").lower()


def test_the_announcement_gives_both_the_name_and_the_meaning() -> None:
    """Enough for someone who chose it, and for someone who hit it by accident."""
    spoken = announce("mono")
    assert spoken.startswith("Mono.")
    assert "blended" in spoken


# -- the modes actually reach the filter graph -------------------------------


def test_mono_blends_rather_than_dropping_a_channel() -> None:
    """Dropping one channel would lose hard-panned content entirely, which is
    the exact problem mono is here to solve."""
    graph = build_filter_graph(0, 0, 0, compressor_enabled=False, channel_mode="mono")
    assert "pan=mono|c0=0.5*c0+0.5*c1" in graph


def test_one_ear_modes_carry_the_whole_field_into_that_ear() -> None:
    left = build_filter_graph(0, 0, 0, compressor_enabled=False, channel_mode="left")
    assert "c0=0.5*c0+0.5*c1" in left  # everything into the left
    assert "c1=0*c0" in left  # right silenced


def test_stereo_adds_no_filter_at_all() -> None:
    assert build_filter_graph(0, 0, 0, compressor_enabled=False, channel_mode="stereo") == ""
