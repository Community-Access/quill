"""What pressing Play would actually do, in the button's own label.

Jeff, 2026-09-30, from the main window: "I land in the library on favorites, if I
tab I see play, play what?"

The button said "Play". That is the correct *verb* and a useless *label*. A sighted
listener reads it next to a Now Playing line and a highlighted tree row and assembles
the answer in a glance; somebody hearing "Play, button" has been told the verb and
nothing else -- not what it would play, not whether it would resume something, not
whether pressing it would do anything at all.

The first fix split the two halves: a short visible label and an accessible name
carrying the object. The survey of the next day (qc.md 6b, item 1) found that on
wxMSW a button is self-labelled and ``set_accessible_name`` is inert on it, so the
fix was inaudible -- the button still said "Play". The object has to be in the
label. That rule, the elision that keeps the row still, and the ampersand escaping
now live in :mod:`quill.core.transport_button`, shared with Quill Radio's main
window; this module is Cast's reading of it: Cast's mnemonics (chosen against the
Podcasts, Episode, Downloads, View, Quillins, Window and Help menus), Cast's active
verb (Pause -- Stop is a second button), and Cast's sentence for the one dead state.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from quill.core import transport_button as tb

__all__ = [
    "LOADING",
    "PAUSED",
    "PLAYING",
    "STOPPED",
    "button_face",
    "button_label",
    "label_samples",
    "transport_name",
]

#: The phases this module distinguishes. Loading counts as playing, because
#: pressing the button while a stream opens should pause it, which is what the
#: listener means.
STOPPED = tb.STOPPED
LOADING = tb.LOADING
PLAYING = tb.PLAYING
PAUSED = tb.PAUSED

#: What the dead state tells a listener to do. Both routes are in the window
#: they are standing in.
_DEAD_HINT = "choose a podcast or an episode in the library first, or use Continue Listening"


def button_face(
    state: str,
    *,
    show_title: str = "",
    episode_title: str = "",
    selection: str = "",
    can_play_selection: bool = False,
) -> tb.ButtonFace:
    """Label, sentence and verb for the Play/Pause/Resume button, as one reading."""
    return tb.face(
        state,
        active_verb="pause",
        object_name=show_title,
        episode_title=episode_title,
        selection=selection,
        can_play_selection=can_play_selection,
        mnemonics=tb.CAST_MNEMONICS,
        dead_hint=_DEAD_HINT,
    )


def button_label(
    state: str,
    *,
    show_title: str = "",
    episode_title: str = "",
    selection: str = "",
    can_play_selection: bool = False,
) -> str:
    """The visible label, object included: "Pla&y The Daily", "Pau&se The Daily,
    Thursday's episode", "Re&sume ...", or "Pla&y -- nothing selected"."""
    return button_face(
        state,
        show_title=show_title,
        episode_title=episode_title,
        selection=selection,
        can_play_selection=can_play_selection,
    ).label


def transport_name(
    state: str,
    *,
    show_title: str = "",
    episode_title: str = "",
    selection: str = "",
    can_play_selection: bool = False,
) -> str:
    """The whole sentence, never elided: what pressing the button would do.

    Spoken when the button is pressed in the one state where it does nothing,
    and used wherever a status line wants the same words as the button.
    """
    return button_face(
        state,
        show_title=show_title,
        episode_title=episode_title,
        selection=selection,
        can_play_selection=can_play_selection,
    ).spoken


def label_samples() -> list[str]:
    """Every label shape the button can show, for GATE-15."""
    return tb.label_samples(tb.CAST_MNEMONICS, active_verb="pause")
