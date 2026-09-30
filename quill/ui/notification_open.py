"""Enter on a notification, and the way back to what it was about.

The notification centre stores a *target* beside every notice
(:mod:`quill.core.notification_targets`) and hands it here when somebody opens
a row. Without this the list is a log: it tells you three episodes arrived and
leaves you to go and find the show yourself, which is the navigation the list
was supposed to save.

### Two apps, two doors, one resolution

Quill Radio and QUILL Cast write to one notification file, so either can be
showing a notice the other raised. What they do not share is a way to display a
podcast: Radio reveals it in the Browse Stations tree, Cast selects it in its
own library tree. The half that *is* shared -- read the target, find the show,
and say something true when it is gone -- lives in :func:`resolve_show`, and
the two doors are three lines each.

### What it says when it cannot

Every refusal here names the reason, because "nothing happened" is the one
outcome a screen reader cannot explain on its own. A subscription dropped
since the notice was written, a Subscriptions branch hidden in Choose Browse
Sources, a notice from before targets existed -- each gets its own sentence
rather than a shared shrug.
"""

from __future__ import annotations

from typing import Any

__all__ = ["NOTHING_TO_OPEN", "open_in_cast", "open_in_radio", "resolve_show"]

#: What the notification centre itself says for a notice with no target. Said
#: here too, so a target that no longer resolves and a target that never
#: existed do not read as two different kinds of failure.
NOTHING_TO_OPEN = "There is nothing to open for this one."

_GONE = "That podcast is not in your subscriptions any more."


def _say(host: Any) -> Any:
    return getattr(host, "_announce", None) or (lambda _m: None)


def resolve_show(target: str) -> tuple[Any, str]:
    """``(show, refusal)`` for *target* -- exactly one of the two is filled.

    The library is read fresh. A notice can be days old and the subscription
    behind it may have gone in the meantime, which is a normal thing to have
    happened and worth saying plainly rather than opening the wrong row.
    """
    from quill.core import notification_targets

    kind, target_id = notification_targets.parse(target)
    if kind != notification_targets.KIND_SHOW or not target_id:
        return (None, NOTHING_TO_OPEN)
    try:
        from quill.core.paths import app_data_dir
        from quill.core.podcasts.subscriptions import load_library

        show = load_library(app_data_dir()).find_show(target_id)
    except Exception:  # noqa: BLE001 - an unreadable library is a missing show
        return (None, _GONE)
    return (show, "") if show is not None else (None, _GONE)


def open_in_radio(host: Any, target: str) -> None:
    """Quill Radio's door: Browse Stations, cursor on the show.

    The window is opened first and the reveal asked for afterwards, which is
    the order that works whether or not Browse Stations was already up --
    ``open_browse_stations`` answers ``None`` when it brought an existing
    window to the front rather than building a second one, and the dialog it
    kept is on the frame either way.
    """
    say = _say(host)
    show, refusal = resolve_show(target)
    if show is None:
        say(refusal)
        return
    from quill.ui.radio import browse_reveal

    dialog = host.open_browse_stations() or getattr(host, "_radio_browse_dialog", None)
    if dialog is None or not browse_reveal.open_to_show(dialog, show.feed_url):
        # The branch can be switched off in Choose Browse Sources, and then
        # there is no row to land on however the window was opened.
        say(f"{show.title}. Turn on Subscriptions in Choose Browse Sources to open its row.")


def open_in_cast(host: Any, target: str) -> None:
    """QUILL Cast's door: its own library tree, cursor on the show.

    ``_reload_library_tree`` is the app's existing "put the cursor here"
    verb -- the same one Add a Podcast finishes with -- so a notification
    lands exactly where adding the show would have.
    """
    say = _say(host)
    show, refusal = resolve_show(target)
    if show is None:
        say(refusal)
        return
    reload_tree = getattr(host, "_reload_library_tree", None)
    if not callable(reload_tree):
        say(NOTHING_TO_OPEN)
        return
    reload_tree(keep_key=("show", show.id))
