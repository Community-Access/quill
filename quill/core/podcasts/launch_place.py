"""Where QUILL Cast lands when it opens.

Jeff, 2026-09-30: "make launch place configurable in settings", and, on the default,
"provide question 1 as the default but allow the user to change it in settings".

The field, ``PodcastSettings.default_launch_view``, existed for a release with
nothing exposing it, so the only way to choose a launch place was a text editor. This
module is the vocabulary for the Preferences row: the choices in the order the row
offers them, and the two translations between a row index and the stored value.

**The shipped default is the automatic rule, not a place.** An empty value means
"what is new": the Inbox if anything is waiting, else Continue Listening if anything
is half-heard, else Podcasts. That is Earshot's answer and what a listener would say
if asked why they opened the app. Every other choice always lands on that place,
whether or not it has anything -- which is a different promise, and the one somebody
makes on purpose when they pick it.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

__all__ = ["AUTOMATIC", "CHOICES", "index_for", "view_at"]

#: The stored value for the automatic rule. Empty, because that is what the field
#: has always held for "no preference", so an upgrade changes nobody's launch.
AUTOMATIC = ""

#: ``(stored value, label)`` in the order the Preferences row offers them. The
#: places after the automatic rule are in the order the Places list shows them.
CHOICES: tuple[tuple[str, str], ...] = (
    (AUTOMATIC, "What is new (the Inbox, else Continue Listening, else Podcasts)"),
    ("inbox", "Inbox"),
    ("new_episodes", "New Episodes"),
    ("continue_listening", "Continue Listening"),
    ("favorites", "Favorites"),
    # The rest of the one window's places (qc.md 4.3), appended so a stored
    # index from before the window keeps its meaning.
    ("personal_audio", "Personal Audio"),
    ("playlists", "Playlists"),
    ("queue", "Play Queue"),
    ("recently_expired", "Recently Expired"),
    ("downloads", "Downloads"),
    ("notifications", "Notifications"),
    ("podcasts", "Podcasts"),
)


def index_for(stored: str) -> int:
    """The row for a stored value; an unknown value reads as the automatic rule.

    Automatic rather than an error, because a value from a deleted or renamed view
    should degrade to the behaviour that cannot surprise anybody, not to a crash
    in the Preferences window.
    """
    wanted = (stored or "").strip().lower()
    for index, (value, _label) in enumerate(CHOICES):
        if value == wanted:
            return index
    return 0


def view_at(index: int) -> str:
    """The stored value for a row; out of range reads as the automatic rule."""
    if 0 <= index < len(CHOICES):
        return CHOICES[index][0]
    return AUTOMATIC
