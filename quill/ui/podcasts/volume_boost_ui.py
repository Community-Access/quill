"""Choosing Volume Boost in the Podcast Manager (list.md 2.8).

The control was already there and was two things short of useful. It was
**session-only**, so the show you fixed last week was quiet again today. And
its ceiling was 100% of the system volume, so a podcast already playing at 100
could not be boosted at all -- which is exactly the badly-mastered show the
control exists for. (Below 100 it worked correctly; the ceiling was the whole
of the problem, and Quill Radio's boost has always gone past it.)

It was also global, which is the one shape that cannot solve what it is for:
turn it up for the quiet show and every other show is now too loud.

So the level is **per podcast and persisted**, through the same
``apply_show_override`` every other per-show setting uses. With nothing
selected it still applies to what is playing, for this session: refusing
outright would make the control useless from the Play Queue, where there is a
thing playing and no row highlighted.

Here rather than in ``manager_phase4``, which is at its GATE-11 ceiling -- and
because "what does this control mean?" is a question worth reading in one
place.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts import volume_boost

#: What the control says it does, and what it does not (the section-3 rule).
#: Here rather than beside the control because the control is in a module at
#: its size ceiling, and because this is the sentence that explains the whole
#: feature.
HELP = (
    "Makes a quiet podcast louder, for this podcast only. It is playback "
    "gain: nothing on disk changes, nothing about the system volume changes, "
    "and no other show is affected. Chosen with a podcast selected, it is "
    "saved for that podcast."
)


def chosen(dialog: Any, index: int) -> None:
    """Apply the level at *index*, and save it against the selected podcast."""
    level = volume_boost.from_index(index)
    controller = getattr(dialog, "_controller", None)
    if controller is not None:
        controller.set_volume_boost(volume_boost.multiplier(level))
    show = dialog._sort_context_show()
    if show is None:
        dialog._announce(f"{volume_boost.describe(level)} Not saved -- no podcast is selected.")
        return
    dialog._library.apply_show_override(show, volume_boost=level)
    dialog._on_library_changed()
    dialog._announce(volume_boost.describe(level))


def for_show(library: Any, show: Any) -> str:
    """The level this podcast plays at, from its own settings or the default."""
    if show is None:
        return volume_boost.OFF
    settings = library.effective_settings(show)
    return volume_boost.normalize(getattr(settings, "volume_boost", volume_boost.OFF))


__all__ = ["HELP", "chosen", "for_show"]
