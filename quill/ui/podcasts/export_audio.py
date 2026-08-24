"""Save Episode Audio As, for an episode that is not downloaded yet.

The verb already worked on a file that was here. On one that was not, it asked
"download it now? then run this command again" -- honest, because it refuses to
block the UI thread on a download of unknown length, but it makes the listener
the scheduler: press the key, wait for a sound you have to be watching for,
remember what you were doing, press the key again.

Earshot says **"Preparing audio file for export"** and opens the save dialog
when the bytes arrive. This is that: one keystroke, one wait, one outcome.

**The wait is a poll, not a callback.** ``PodcastDownloadQueue`` has one
``on_completed`` hook, wired once by whoever owns the queue, so a per-item
continuation would mean threading a registry through the app frame to serve one
menu item. A ``wx.Timer`` reading a local queue once a second costs nothing,
cannot leak across frames, and stops itself -- including at the ceiling, since
a progress-free wait past a few minutes is indistinguishable from a hang.

The decisions all live in the wx-free :mod:`quill.core.podcasts.audio_export`;
what is here is the timer and the two dialogs.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.podcasts import audio_export

#: Where a waiting export parks its timer on the window that owns it.
LIVE_TIMERS = "_export_audio_timers"


def export_episode_audio(
    parent: Any,
    download_queue: Any,
    download_root: Path,
    show: Any,
    episode: Any,
    *,
    announce: Callable[[str], None],
    wx: Any = None,
    on_finished: Callable[[], None] | None = None,
) -> bool:
    """Save the episode's audio somewhere, fetching it first if need be.

    Returns whether the save dialog was reached *in this call* -- False when a
    download had to start, which is not a failure and says so out loud.

    *on_finished* is the caller's chance to re-read the row (the download
    changed it), and runs however the export ended.
    """
    if wx is None:
        import wx as wx_module

        wx = wx_module

    # Existence, not the recorded path: a downloaded copy deleted from outside
    # the app leaves the record behind, and fetching it again is the useful
    # answer to that -- not a copy that raises.
    if _existing_path(episode) is not None:
        return _save_now(parent, show, episode, announce=announce, wx=wx, on_finished=on_finished)

    from quill.ui.podcasts.show_actions import enqueue_episode_download

    item_id = str(episode.guid)
    enqueue_episode_download(download_queue, download_root, show, episode, item_id=item_id)
    announce(audio_export.preparing(str(episode.title)))
    _wait_for(
        parent,
        download_queue,
        show,
        episode,
        item_id=item_id,
        announce=announce,
        wx=wx,
        on_finished=on_finished,
    )
    return False


def copy_episode_path(episode: Any, *, announce: Callable[[str], None], wx: Any = None) -> bool:
    """Put the downloaded file's path on the clipboard.

    The other half of handing a file off, and the one that needs no file
    manager: a path can be pasted into an upload box, a terminal, or a message
    to somebody. Refused for an episode with no file, because a path to
    nothing is worse than no path.
    """
    if wx is None:
        import wx as wx_module

        wx = wx_module

    path = _existing_path(episode)
    if path is None:
        announce(audio_export.missing_file(str(episode.title)))
        return False
    if not wx.TheClipboard.Open():
        announce("The clipboard could not be opened.")
        return False
    try:
        wx.TheClipboard.SetData(wx.TextDataObject(str(path)))
        wx.TheClipboard.Flush()
    finally:
        wx.TheClipboard.Close()
    announce(audio_export.copied_path(str(path)))
    return True


# -- the wait -------------------------------------------------------------------


def _wait_for(
    parent: Any,
    download_queue: Any,
    show: Any,
    episode: Any,
    *,
    item_id: str,
    announce: Callable[[str], None],
    wx: Any,
    on_finished: Callable[[], None] | None,
) -> Any:
    """Poll the queue until the file lands, then open the save dialog."""
    timer = wx.Timer(parent)
    # Held by the window, not by a closure cell. A wx.Timer whose only
    # reference is the handler bound to it is a timer one garbage collection
    # away from never firing again -- and the list is also how the frame can
    # stop them all when it closes, and how a test reaches them.
    live = getattr(parent, LIVE_TIMERS, None)
    if live is None:
        live = []
        setattr(parent, LIVE_TIMERS, live)
    live.append(timer)
    waited = {"seconds": 0.0}

    def _stop() -> None:
        try:
            if timer.IsRunning():
                timer.Stop()
        except Exception:  # noqa: BLE001 - a dying timer must not crash a menu
            pass
        if timer in live:
            live.remove(timer)
        if on_finished is not None:
            on_finished()

    def _on_tick(event: Any) -> None:
        # One parent's EVT_TIMER is shared by every timer bound to it, so
        # identity has to be checked before acting on a tick.
        if event.GetId() != timer.GetId():
            event.Skip()
            return
        waited["seconds"] += audio_export.POLL_SECONDS
        item = download_queue.get(item_id)
        state = audio_export.poll_state(item, waited["seconds"])
        if state == audio_export.WAITING:
            return
        _stop()
        title = str(episode.title)
        if state == audio_export.READY:
            # The queue writes the path onto the episode as it completes; if
            # it somehow did not, the row itself knows where it put the file.
            if not audio_export.has_audio(episode):
                episode.downloaded_path = str(getattr(item, "destination", "") or "")
            _save_now(parent, show, episode, announce=announce, wx=wx, on_finished=None)
            return
        if state == audio_export.FAILED:
            announce(audio_export.failed(title, str(getattr(item, "error", "") or "")))
        elif state == audio_export.CANCELLED:
            announce(audio_export.cancelled(title))
        else:
            announce(audio_export.gave_up(title))

    parent.Bind(wx.EVT_TIMER, _on_tick, timer)
    timer.Start(audio_export.POLL_SECONDS * 1000)
    return timer


# -- the save dialog ------------------------------------------------------------


def _save_now(
    parent: Any,
    show: Any,
    episode: Any,
    *,
    announce: Callable[[str], None],
    wx: Any,
    on_finished: Callable[[], None] | None,
) -> bool:
    import shutil

    source = _existing_path(episode)
    if source is None:
        announce(audio_export.missing_file(str(episode.title)))
        if on_finished is not None:
            on_finished()
        return False
    suggested = audio_export.suggested_filename(show, episode, source.suffix)
    try:
        with wx.FileDialog(
            parent,
            message="Save episode audio as",
            defaultFile=suggested,
            wildcard=f"Audio file (*{source.suffix})|*{source.suffix}|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return False
            destination = Path(dialog.GetPath())
        try:
            # Copied, never moved: QUILL Cast goes on managing its own
            # downloaded copy (retention, storage caps, Remove Downloaded
            # Copy), and the saved one is the listener's, outside all of it.
            shutil.copy2(source, destination)
        except OSError as error:
            announce(f"Could not save the audio: {error}")
            return False
        announce(f"Saved {episode.title} to {destination.name}")
        return True
    finally:
        if on_finished is not None:
            on_finished()


def _existing_path(episode: Any) -> Path | None:
    """The episode's file, if it is genuinely there.

    A recorded path is not a present file: a downloaded copy deleted from
    outside the app leaves the record behind.
    """
    if not audio_export.has_audio(episode):
        return None
    path = Path(str(episode.downloaded_path))
    return path if path.exists() else None


__all__ = ["LIVE_TIMERS", "copy_episode_path", "export_episode_audio"]
