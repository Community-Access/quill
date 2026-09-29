"""Whether to check a feed, how often, and what to say when something arrives.

Three questions that belong together because a listener sets them together, and
because answering them in different places is how Quill Radio and QUILL Cast
ended up disagreeing: Radio read ``podcast_refresh_minutes`` out of its own
history file while Cast read ``podcast_check_interval_minutes`` out of the
podcast one, so turning the check on in one app did nothing in the other.

They resolve through the settings chain the library already has -- shared
default, then folder (outermost first), then the podcast itself
(:func:`quill.core.podcasts.settings_resolver.effective_settings`) -- so "every
hour, except this one show, which I want quietly and only once a day" is
expressible without any new mechanism. Adding a *fourth* inheritance scheme for
alerts would have been the mistake.

### The interval, and "never" as a real answer

``check_interval_minutes`` is minutes, and **0 means never on its own**: not a
hidden default, not a compromise. Somebody on a metered connection, or somebody
who simply wants the app quiet, is entitled to a podcast client that reaches the
network only when asked. Set globally it turns the whole check off; set on one
show it leaves that show alone while the rest keep their cadence.

### The alert, and why "quiet" exists

``new_episode_alert`` is **on**, **quiet** or **off**:

* **on** -- a desktop notification, the sound, and an entry in the in-app list.
* **quiet** -- the entry only. Nothing appears over what you are reading and
  nothing plays. This is the mode that makes a busy show bearable: nine new
  episodes of a daily news podcast is information you want to be able to *find*,
  not information you want announced nine times.
* **off** -- nothing at all, not even the list entry.

Quiet is the default for a reason. An app that starts putting toasts over
somebody's document because they subscribed to something has made a decision
that belongs to them.

wx-free, strict-typed, pure: no clock, no store, no network. The caller supplies
the settings and the shows; this decides.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

__all__ = [
    "ALERT_CHOICES",
    "ALERT_DEFAULT",
    "ALERT_LABELS",
    "ALERT_OFF",
    "ALERT_ON",
    "ALERT_QUIET",
    "alert_for_show",
    "anything_to_check",
    "describe_alert",
    "interval_for_show",
    "normalize_alert",
    "plays_sound",
    "shows_worth_checking",
    "wants_desktop_notice",
    "wants_list_entry",
]

#: A desktop notification, the sound, and the in-app entry.
ALERT_ON = "on"
#: The in-app entry only: nothing over your document, nothing played.
ALERT_QUIET = "quiet"
#: Nothing at all.
ALERT_OFF = "off"

#: The shipped answer. Quiet, deliberately -- see the module docstring.
ALERT_DEFAULT = ALERT_QUIET

#: ``(value, label)`` for a chooser, in the order they belong in one: loudest
#: first, so the list reads as a volume rather than as an alphabet.
ALERT_CHOICES: tuple[tuple[str, str], ...] = (
    (ALERT_ON, "Notify me -- a notification and a sound"),
    (ALERT_QUIET, "Quietly -- add it to the list, say nothing"),
    (ALERT_OFF, "Not at all"),
)

#: The words each value reads back as, for a settings report or a status line.
#: Never retyped at a call site: one wording, everywhere.
ALERT_LABELS: dict[str, str] = {
    ALERT_ON: "Notify me",
    ALERT_QUIET: "Quietly",
    ALERT_OFF: "Not at all",
}


def normalize_alert(value: object) -> str:
    """A stored alert mode, or :data:`ALERT_DEFAULT` when it is not one of ours.

    A settings file is somebody else's input, and the safe direction is always
    the quieter one: a typo must never turn into toasts nobody asked for.
    """
    wanted = str(value or "").strip().lower()
    return wanted if wanted in ALERT_LABELS else ALERT_DEFAULT


def describe_alert(value: object) -> str:
    """How this mode reads back to a person."""
    return ALERT_LABELS[normalize_alert(value)]


def wants_list_entry(mode: object) -> bool:
    """Whether this mode records the arrival in the in-app list.

    True for both **on** and **quiet**: the list is the thing that makes a
    missed notification recoverable, and a listener who chose "quietly" chose
    where to be told, not whether.
    """
    return normalize_alert(mode) in (ALERT_ON, ALERT_QUIET)


def wants_desktop_notice(mode: object) -> bool:
    """Whether this mode shows a desktop notification."""
    return normalize_alert(mode) == ALERT_ON


def plays_sound(mode: object) -> bool:
    """Whether this mode plays the new-episode sound.

    The same answer as the desktop notice on purpose: "quiet" that still made a
    noise would be a lie, and those are the two halves of being interrupted.
    """
    return normalize_alert(mode) == ALERT_ON


def interval_for_show(settings: Any) -> int:
    """Minutes between automatic checks for a show, from its resolved settings.

    *settings* is what :func:`effective_settings` returned for that show, so the
    folder and per-podcast overrides are already applied. 0 means never on its
    own. Clamped by :mod:`quill.core.podcasts.refresh_policy` so a stored value
    that survived a units change cannot turn into a request every second.
    """
    from quill.core.podcasts import refresh_policy

    raw = getattr(settings, "check_interval_minutes", None)
    if raw is None:
        raw = refresh_policy.DEFAULT_INTERVAL_MINUTES
    return refresh_policy.normalize_interval(raw)


def alert_for_show(settings: Any) -> str:
    """The alert mode in force for a show, from its resolved settings."""
    return normalize_alert(getattr(settings, "new_episode_alert", ALERT_DEFAULT))


def shows_worth_checking(
    shows: Iterable[Any],
    resolve: Any,
    *,
    force: bool = False,
    global_minutes: int | None = None,
) -> list[Any]:
    """The shows an automatic check should actually ask about.

    *resolve* is called with a show and returns its effective settings (the
    library's ``effective_settings``), so this stays free of the library type.

    **This answers "which shows", never "is it time yet".** The cadence belongs
    to the caller's timer; mixing the two here was a real bug on the way to
    this release -- the worker re-read the same interval field and refused every
    show whenever the *global* value was 0, which is the shipped default.

    So a per-show interval of 0 means **this show is opted out**, and it is only
    read that way when there is a global cadence for it to be an exception to.
    Pass *global_minutes* to say what that is; without it, only the pause and
    the missing-feed checks apply.

    A show is skipped when it has no feed to ask, when it is paused (the
    existing "leave this show alone" switch), or when it is opted out as above.

    ``force=True`` is the Refresh key on a row: it ignores every one of those,
    because a switch that could strand a show would be a trap rather than a
    preference.
    """
    wanted: list[Any] = []
    for show in shows:
        if not str(getattr(show, "feed_url", "") or "").strip():
            continue  # a local/imported show has no feed to ask
        if force:
            wanted.append(show)
            continue
        if bool(getattr(show, "paused", False)):
            continue
        if global_minutes is not None and global_minutes > 0:
            try:
                resolved = resolve(show)
            except Exception:  # noqa: BLE001 - unresolvable settings: leave it alone
                continue
            if interval_for_show(resolved) <= 0:
                continue  # an explicit "never" for this show, against a global yes
        wanted.append(show)
    return wanted


def anything_to_check(
    shows: Sequence[Any], resolve: Any, *, global_minutes: int | None = None
) -> bool:
    """Whether an automatic check has anything at all to do.

    The timer asks this before it reaches the network, so a listener who is
    subscribed to nothing -- or who has set every show to never -- costs no
    request, no thread and no battery. An app that wakes up to do nothing is
    still an app that woke up.
    """
    return bool(shows_worth_checking(shows, resolve, global_minutes=global_minutes))
