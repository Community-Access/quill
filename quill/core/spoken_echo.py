"""The Spoken Echo: a reviewable record of what QUILL most recently spoke.

Every announcement QUILL speaks (status-bar updates and forced result
announcements alike) flows through a single choke point in the UI shell. This
module is the pure, ``wx``-free core behind the "Echo" feature: it keeps a short
rolling history of those spoken lines and formats them for the read-only review
dialog so a screen-reader user can re-read, navigate, and copy text that would
otherwise have scrolled past in speech.

The history itself lives on the UI shell (a small ``deque``); the recording and
formatting rules live here so they can be unit-tested without a UI.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence

#: How many recent announcements the Echo keeps. Newest-first when displayed.
SPOKEN_ECHO_LIMIT = 20


def new_history(limit: int = SPOKEN_ECHO_LIMIT) -> deque[str]:
    """Return an empty bounded history suitable for :func:`record_spoken`."""
    return deque(maxlen=max(1, int(limit)))


def record_spoken(history: deque[str], message: object) -> bool:
    """Append ``message`` to ``history`` if it is worth keeping.

    Returns ``True`` when the message was recorded. Empty/whitespace-only
    messages and an immediate repeat of the previous line are dropped, so the
    Echo never fills up with blank entries or a status that re-fires verbatim on
    every keystroke.
    """
    text = "" if message is None else str(message).strip()
    if not text:
        return False
    if history and history[-1] == text:
        return False
    history.append(text)
    return True


#: What the Echo says when the user has turned the history off, so an empty
#: review is never mistaken for "nothing was said".
HISTORY_OFF_MESSAGE = (
    "Announcement history is off, so QUILL is not keeping a list of what it said. "
    "To turn it back on, open Settings, Accessibility, and check Keep an announcement history."
)


def echo_history_enabled(settings: object) -> bool:
    """The "Keep an announcement history" setting (announcement_echo_history).

    Off means nothing is recorded and anything already kept is dropped -- it is
    a privacy switch, so it must not leave the last twenty lines lying around.
    Settings objects without the field (companion apps) keep the history.
    """
    return bool(getattr(settings, "announcement_echo_history", True))


def spoken_echo_text(entries: Sequence[str], settings: object) -> str:
    """The Echo dialog's text: the history, or why there is none."""
    if not echo_history_enabled(settings):
        return HISTORY_OFF_MESSAGE
    return format_spoken_echo(entries)


def format_spoken_echo(entries: Sequence[str]) -> str:
    """Render the history newest-first for the review dialog.

    Entries are numbered with ``1.`` as the most recent line so the thing the
    user just heard sits at the top, where focus lands. An empty history yields
    a single explanatory line rather than a blank control.
    """
    cleaned = [str(entry).strip() for entry in entries if str(entry).strip()]
    if not cleaned:
        return "Nothing has been announced yet."
    newest_first = list(reversed(cleaned))
    return "\n".join(f"{index}. {line}" for index, line in enumerate(newest_first, start=1))
