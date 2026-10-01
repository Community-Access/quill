"""What pressing Play would actually do, said out loud.

Jeff, 2026-09-30, from the main window: "I land in the library on favorites, if I
tab I see play, play what?"

The button said "Play". That is the correct *label* and a useless *name*. A sighted
listener reads it next to a Now Playing line and a highlighted tree row and assembles
the answer in a glance; somebody hearing "Play, button" has been told the verb and
nothing else -- not what it would play, not whether it would resume something, not
whether pressing it would do anything at all. And in the one state where it genuinely
does nothing (stopped, with nothing selected that can play) it looked exactly the same
as in the state where it would start an episode.

So the two halves are split, which is what ``set_accessible_name`` is for:

* **The visible label stays short** -- Play, Pause, Resume. A button whose visible
  text grew to a full sentence would reflow the row it sits in every time the
  selection changed, which is its own kind of unusable.
* **The accessible name carries the object.** "Resume The Daily, Thursday's episode"
  is what a screen reader should say, because that is the whole of what the listener
  cannot otherwise find out.

One rule decides every case below: **the name describes the effect of pressing it,
not the state of the player.** Those are different sentences, and only the first one
answers "play what?". A button named after the state ("Stopped") is a readout
wearing a button's clothes, which is the same mistake Radio's status bar was
redesigned to stop making.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

__all__ = ["PAUSED", "PLAYING", "STOPPED", "button_label", "transport_name"]

#: The three states this module distinguishes. Deliberately *not* the player's own
#: enum: this module is wx-free and must not import the UI, and the caller already
#: holds the enum. Loading counts as playing, because pressing the button while a
#: stream opens should pause it, which is what the listener means.
PLAYING = "playing"
PAUSED = "paused"
STOPPED = "stopped"


def button_label(state: str) -> str:
    """The short visible label, with its access key.

    Three labels rather than two, because Resume and Play are different promises:
    Play starts something at the beginning, Resume returns to a place. A listener
    who hears Resume knows their position survived.
    """
    if state == PLAYING:
        return "&Pause"
    if state == PAUSED:
        return "&Resume"
    return "&Play"


def _episode_phrase(show_title: str, episode_title: str) -> str:
    """ "The Daily, Thursday's episode", or whichever half exists."""
    show = (show_title or "").strip()
    episode = (episode_title or "").strip()
    if show and episode:
        return f"{show}, {episode}"
    return episode or show


def transport_name(
    state: str,
    *,
    show_title: str = "",
    episode_title: str = "",
    selection: str = "",
    can_play_selection: bool = False,
) -> str:
    """The accessible name: what pressing the button would do, in full.

    *selection* is what the library cursor is on, and *can_play_selection* whether
    pressing Play would actually start it -- a folder, a pinned view or an empty
    show is a selection that cannot be played, and a button that says it would play
    "News" when News is a folder has lied about the one thing it was asked.

    The stopped-with-nothing-playable case says **what to do instead**, because it
    is the only state in which the button does nothing, and a button that does
    nothing and says only "Play" is indistinguishable from a broken one. That was
    the report.
    """
    if state == PLAYING:
        what = _episode_phrase(show_title, episode_title)
        return f"Pause {what}" if what else "Pause"
    if state == PAUSED:
        what = _episode_phrase(show_title, episode_title)
        return f"Resume {what}" if what else "Resume"
    if can_play_selection and selection.strip():
        return f"Play {selection.strip()}"
    # Stopped, and nothing pressing it would start. Name the two routes, since the
    # listener is standing in the library and one of them is under their cursor.
    return (
        "Play. Nothing is selected that can be played -- choose a podcast or an "
        "episode in the library first, or use Continue Listening"
    )
