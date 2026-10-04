"""Say an action's outcome and keep it, in one call (qc.md F-10).

Most of Cast's and Radio's verbs end by announcing a sentence -- "Exported 12
podcasts to subscriptions.opml" -- and until now that sentence was gone the
moment it was said: F9 could not repeat it and Activity (Shift+F9) never
listed it. :func:`report_outcome` says the same sentence through the shared
result model (:func:`quill.ui.activity_window.report_result`), so it is
spoken exactly as before *and* kept, with Open Folder when the action made a
file.

*host* is anything with ``_announce``: an app frame, or a dialog whose
``_announce`` is the frame's callback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core import activity

__all__ = ["keep_outcome", "report_outcome", "say_recording_failed", "say_recording_saved"]


def _open_folder(path: Path) -> str:
    import wx

    folder = path if path.is_dir() else path.parent
    if not folder.exists():
        return f"{folder} is no longer there."
    wx.LaunchDefaultApplication(str(folder))
    return f"Opened {folder.name}."


def report_outcome(
    host: Any,
    action: str,
    summary: str,
    *,
    object_name: str = "",
    path: Path | str | None = None,
    failed: bool = False,
    reason: str = "",
) -> None:
    """Speak *summary* and record it as the result of *action*."""
    from quill.ui.activity_window import report_result

    actions: dict[str, Any] = {}
    next_actions: tuple[activity.NextAction, ...] = ()
    if path and not failed:
        where = Path(path)
        next_actions = (activity.OPEN_FOLDER,)
        actions[activity.OPEN_FOLDER.id] = lambda: _open_folder(where)
    report_result(
        host,
        activity.ActionResult(
            action=action,
            object_name=object_name,
            outcome=activity.FAILED if failed else activity.COMPLETED,
            summary=summary,
            reason=reason,
            next_actions=next_actions,
        ),
        actions,
    )


def keep_outcome(
    action: str,
    summary: str,
    *,
    object_name: str = "",
    path: Path | str | None = None,
    failed: bool = False,
    reason: str = "",
) -> None:
    """Record an outcome the caller has already spoken (with its own earcon)."""
    from quill.ui.activity_window import register_actions

    next_actions: tuple[activity.NextAction, ...] = ()
    actions: dict[str, Any] = {}
    if path and not failed:
        where = Path(path)
        next_actions = (activity.OPEN_FOLDER,)
        actions[activity.OPEN_FOLDER.id] = lambda: _open_folder(where)
    result = activity.ActionResult(
        action=action,
        object_name=object_name,
        outcome=activity.FAILED if failed else activity.COMPLETED,
        summary=summary,
        reason=reason,
        next_actions=next_actions,
    )
    activity.LOG.record(result)
    if actions:
        register_actions(result, actions)


def say_recording_saved(host: Any, destination: Path) -> None:
    """Quill Radio: the recorder's stop-and-finalize edge, said with its cue and kept."""
    from quill.core.sound_events import SoundEvent

    sentence = f"Recording saved: {destination.name}"
    host._announce(sentence, sound=SoundEvent.RADIO_RECORDING_STOPPED)
    keep_outcome("Record", f"{sentence}.", path=destination)


def say_recording_failed(host: Any, station: str, reason: str) -> None:
    """Quill Radio: a recording that captured nothing, on the error cue, and kept."""
    from quill.core.sound_events import SoundEvent

    host._announce(
        f"Recording of {station} saved nothing: {reason}. No file was kept.",
        sound=SoundEvent.RADIO_STREAM_ERROR,
    )
    keep_outcome(
        "Record",
        f"Recording of {station} saved nothing.",
        object_name=station,
        failed=True,
        reason=reason,
    )
