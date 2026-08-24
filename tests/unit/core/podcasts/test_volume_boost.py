"""Volume Boost, per podcast (list.md 2.8) -- and Skip Silence's promise (2.7).

**Boost.** Quill Radio's is a switch, which is right for radio: what you are
listening to changes every time you tune elsewhere, and one global answer is
the only one that could keep up. A podcast library is the opposite case -- one
badly-mastered show among forty is exactly what a global control cannot fix, so
this is per show, with a global default.

**Skip Silence** is the other half of the same conversation, and the thing
worth pinning is not the setting but the guarantee behind it: **compressing
silence must not move a saved position**. If it did, resuming an episode you
part-listened to with the filter on would land somewhere you have never been --
and the further in you were, the further wrong it would be.

Quill Radio calls it Skip Silence and QUILL Cast calls it Smart Speed. They are
the *same ffmpeg filter*, and that is asserted below, because two names for one
behaviour is how two apps drift into disagreeing about it.
"""

from __future__ import annotations

import pytest

from quill.core import audio_enhance
from quill.core.podcasts import volume_boost as vb
from quill.core.podcasts.models_settings import PodcastSettings

# -- the levels -------------------------------------------------------------------


def test_off_is_the_shipped_answer() -> None:
    assert PodcastSettings().volume_boost == vb.OFF
    assert vb.multiplier(PodcastSettings().volume_boost) == 1.0


def test_the_four_levels_are_audibly_different_from_each_other() -> None:
    """A four-way choice is only worth having if the steps can be told apart."""
    factors = [factor for _name, _label, factor in vb.LEVELS]
    assert factors == sorted(factors)
    gaps = [b - a for a, b in zip(factors, factors[1:], strict=False)]
    assert all(gap >= 0.1 for gap in gaps)


def test_anything_unreadable_is_off() -> None:
    """A typo in a settings file must never make the next episode louder than
    somebody asked for."""
    for junk in ("", "  ", "LOUD", None, 3, True, []):
        assert vb.normalize(junk) == vb.OFF


def test_a_level_is_matched_however_it_was_cased() -> None:
    assert vb.normalize("HIGH") == vb.HIGH
    assert vb.normalize(" Medium ") == vb.MEDIUM


def test_the_index_round_trips_through_a_wx_selection() -> None:
    for index, (name, _label, _factor) in enumerate(vb.LEVELS):
        assert vb.from_index(index) == name
        assert vb.index_of(name) == index


def test_an_out_of_range_selection_is_off_rather_than_a_crash() -> None:
    for junk in (-1, len(vb.LEVELS), "1", None):
        assert vb.from_index(junk) == vb.OFF


# -- applying it ------------------------------------------------------------------


def test_boost_multiplies_the_volume_already_chosen() -> None:
    """Boost and the volume control compose rather than fight."""
    assert vb.apply_to(100, vb.OFF) == 100
    assert vb.apply_to(50, vb.MEDIUM) == 65
    assert vb.apply_to(80, vb.LOW) == 92


def test_boost_goes_past_100_which_is_the_whole_point() -> None:
    """A podcast already at full volume is precisely the one that needs it."""
    assert vb.apply_to(100, vb.HIGH) == 150


def test_boost_stops_at_the_ceiling() -> None:
    """Past about there a spoken-word recording stops getting louder and
    starts distorting."""
    assert vb.apply_to(200, vb.HIGH) == vb.MAX_PERCENT
    assert vb.MAX_PERCENT == 150


def test_a_nonsense_volume_is_silence_rather_than_an_exception() -> None:
    for junk in (None, "loud", [], object()):
        assert vb.apply_to(junk, vb.HIGH) == 0


# -- what it says -----------------------------------------------------------------


def test_off_says_what_happens_instead() -> None:
    said = vb.describe(vb.OFF)
    assert "the volume you set" in said


def test_a_level_says_how_much_and_that_it_is_this_podcast_only() -> None:
    """The per-show half is the useful half, so the sentence has to carry it."""
    said = vb.describe(vb.MEDIUM)
    assert "30 percent" in said
    assert "this podcast only" in said


# -- it survives a save -----------------------------------------------------------


def test_the_setting_round_trips() -> None:
    settings = PodcastSettings()
    settings.volume_boost = vb.HIGH
    assert PodcastSettings.from_dict(settings.to_dict()).volume_boost == vb.HIGH


def test_an_older_library_file_reads_as_off() -> None:
    data = PodcastSettings().to_dict()
    data.pop("volume_boost", None)
    assert PodcastSettings.from_dict(data).volume_boost == vb.OFF


def test_a_hand_edited_level_goes_through_the_shared_normalisation() -> None:
    data = PodcastSettings().to_dict()
    data["volume_boost"] = "VERY LOUD"
    assert PodcastSettings.from_dict(data).volume_boost == vb.OFF


def test_it_is_per_show_overridable_like_every_other_playback_setting() -> None:
    from quill.core.podcasts.models import PodcastShow
    from quill.core.podcasts.subscriptions import PodcastLibrary

    show = PodcastShow(id="s", title="Quiet Show", feed_url="https://e/f.xml", episodes=[])
    library = PodcastLibrary(shows=[show])

    library.apply_show_override(show, volume_boost=vb.HIGH)

    assert library.effective_settings(show).volume_boost == vb.HIGH
    assert library.settings.volume_boost == vb.OFF, "the default is untouched"


# -- Skip Silence: the guarantee (2.7) --------------------------------------------


def test_skip_silence_and_smart_speed_are_the_same_filter() -> None:
    """Quill Radio calls it Skip Silence, QUILL Cast calls it Smart Speed.

    Two names for one behaviour is how two apps drift into disagreeing about
    it -- so the fact that there is only one filter is asserted rather than
    assumed. Radio's controller passes its ``skip_silence`` straight in as
    ``smart_speed_enabled``.
    """
    from pathlib import Path

    radio = (
        Path(__file__).resolve().parents[4] / "quill" / "ui" / "radio" / "player_controller.py"
    ).read_text(encoding="utf-8")

    assert "smart_speed_enabled=self._skip_silence" in radio


def test_the_silence_filter_is_engaged_only_when_asked() -> None:
    assert audio_enhance.build_filter_graph(0, 0, 0, compressor_enabled=False) == ""
    graph = audio_enhance.build_filter_graph(
        0, 0, 0, compressor_enabled=False, smart_speed_enabled=True
    )
    assert "silenceremove" in graph


def test_removing_silence_never_re_times_the_media() -> None:
    """**The guarantee** (2.7): a saved position stays in the original media
    timeline.

    It holds because of *where* the filter runs. It is an output-side ``-af``
    graph -- it changes the samples being played, and nothing about the source
    the player counts position against. Nothing in the graph seeks, trims the
    input, or rewrites timestamps, so "forty minutes in" means the same thing
    with the filter on as with it off, and a resume lands where it was left.

    Asserted structurally, because the alternative failure is invisible: an
    input-side filter would still play correctly and would quietly move every
    saved position.
    """
    graph = audio_enhance.build_filter_graph(
        3, 0, -2, compressor_enabled=True, smart_speed_enabled=True
    )

    assert "silenceremove" in graph
    for re_timing in ("atrim", "asetpts", "atempo", "-ss", "aselect"):
        assert re_timing not in graph, f"{re_timing} would move the timeline"


@pytest.mark.parametrize("enabled", [True, False])
def test_the_filter_changes_nothing_else_about_the_graph(enabled: bool) -> None:
    """Turning it on must not disturb the EQ or the compressor beside it."""
    graph = audio_enhance.build_filter_graph(
        6, -3, 2, compressor_enabled=True, smart_speed_enabled=enabled
    )
    assert "acompressor" in graph
    assert "equalizer" in graph or "bass" in graph or "treble" in graph
