"""**Download...** -- saving a recording, or a whole book, off the UI thread.

The rights decision lives in :mod:`quill.core.radio.downloadable` and the
transfer in :mod:`quill.core.radio.media_download`; this is the part that needs
a window: asking where to put it, running it on the task manager, and saying
what happened.

Three things it is careful about:

* **The menu item appears only where it can work**, and a refusal is still
  spoken. A row that cannot be saved does not carry a dead *Download...* -- but
  asking for one anyway (from the command palette, say) says *why*, because the
  four reasons a thing cannot be downloaded are genuinely different facts and
  "nothing happened" is the least useful of them.
* **A book is a folder, not forty prompts.** Downloading a whole book asks for
  one folder and then works through the chapters in order, saying "Chapter 12 of
  40" as it goes -- never a dialog per chapter.
* **It is interruptible and it never blocks listening.** The transfer runs on the
  task manager, so the radio keeps playing throughout, and Stop stops it within a
  chunk rather than at the end of a 90 MB chapter.
"""

from __future__ import annotations

from typing import Any

#: How often a book download speaks its progress. Every chapter would be
#: constant interruption on a forty-part novel; every fifth is a heartbeat you
#: can ignore while still knowing it is alive.
ANNOUNCE_EVERY = 5


def _announce(host: Any, message: str) -> None:
    announce = getattr(host, "_announce", None)
    if callable(announce):
        announce(message)


def can_download(station: Any) -> bool:
    """Whether to put *Download...* on this row's menu at all."""
    from quill.core.radio.downloadable import can_download as _decide

    return bool(_decide(station))


def _choose_folder(host: Any, title: str) -> str:
    """Ask where to save. Returns "" when the listener backed out."""
    picker = getattr(host, "_pick_download_folder", None)
    if callable(picker):
        return str(picker(title) or "")
    import wx

    parent = getattr(host, "dialog", None) or getattr(host, "frame", None) or host
    with wx.DirDialog(parent, title) as dialog:  # dialog_button_contract: exempt
        return str(dialog.GetPath()) if dialog.ShowModal() == wx.ID_OK else ""


def download_station(host: Any, station: Any, *, group: str = "") -> bool:
    """Queue one recording. True when it was added.

    Everything goes through the queue, including a single file: one code path
    means one place that decides where a file lands, one place that reports, and
    a second download started while the first is going simply joins the line
    rather than racing it.
    """
    from quill.core.radio import downloadable
    from quill.ui.radio import download_runner

    decision = downloadable.can_download(station)
    if not decision.allowed:
        # Said rather than silently declined: "Download" doing nothing is
        # indistinguishable from a bug, and the reason is the useful part.
        _announce(host, decision.reason)
        return False
    return bool(download_runner.enqueue(host, [station], group=group))


def download_book(host: Any, chapters: list[Any], *, title: str = "", author: str = "") -> bool:
    """Queue every chapter of a book, in order, into one folder.

    The case the queue exists for: forty chapters is an hour of transferring
    that must not hold the app still, must survive one bad address, and must be
    stoppable without losing what already arrived. The filing rules decide the
    folder (``download_prefs``), so nobody is asked forty questions -- or even
    one, unless they asked to be.
    """
    from quill.ui.radio import download_runner

    return bool(download_runner.enqueue(host, chapters, group=title, author=author))


def stop_download(host: Any) -> bool:
    """Stop the transfer in progress. Whatever has arrived is kept."""
    from quill.ui.radio import download_runner

    if not download_runner.cancel_current(host):
        _announce(host, "No download is running.")
        return False
    _announce(host, "Stopping the download. Anything already saved is kept.")
    return True
