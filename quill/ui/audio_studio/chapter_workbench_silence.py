"""The Chapter Workbench's "Propose chapters from silences", for any recording.

Item 42 of the 2026-10-16 checklist. The scan was already in the Workbench;
what this module adds is everything around it that an ordinary MP3 -- a
lecture, a meeting, a talk -- needs, split out of ``chapter_workbench.py``
because that module sits on its GATE-11 budget:

* **Guesses say so.** Proposed chapters are titled "Proposed chapter 1, 2..."
  (:mod:`quill.core.speech.chapter_proposals`), never the "Chapter 1" an
  author would write.
* **Your chapters are kept.** When the recording already has chapters of its
  own, the Workbench asks first: *Keep mine and add proposals* (the default:
  every existing chapter kept, a proposed boundary added only where it is new)
  or *Replace with the proposal*. Cancel changes nothing. A recording with no
  chapter marks is never asked -- there is nothing of yours to lose.
* **The scan can be cancelled.** While it runs, the same button reads "Stop
  proposing chapters"; pressing it, or closing the Workbench, discards the
  scan's answer and leaves the list exactly as it was. (ffmpeg finishes its
  pass in the background and its result is thrown away; nothing is written.)
* **A failure resets the button.** The scan's errors -- no ffmpeg, an
  unreadable file -- are shown, and the button goes back to proposing.

Reviewing is the Workbench's own: each proposed chapter is in the list with
its start time, Play hears it, Set start to playhead and Split at playhead
move a boundary by ear, Rename names it, Restore original takes the whole
proposal back, and Save writes it (MP3 in place, M4B as a new file).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.i18n import _
from quill.core.speech.chapter_proposals import (
    PROPOSED_TITLE,
    has_authored_chapters,
    merge_proposals,
    retitle_as_proposed,
)
from quill.ui.audio_studio.chapter_workbench_dialogs import SilenceParamsDialog

__all__ = ["RECORDING_WILDCARD", "SilenceProposalMixin", "bind_host_shortcuts", "pick_recording"]

#: What Find Chapters in a Recording offers: what the Workbench can open and save.
RECORDING_WILDCARD = "Recordings (*.mp3;*.m4a;*.m4b)|*.mp3;*.m4a;*.m4b|All files (*.*)|*.*"

#: The button's two labels: proposing, and while a scan runs.
PROPOSE_LABEL = "Propose chapters from silen&ces..."
STOP_LABEL = "Stop proposing chapters (silen&ces)"


class SilenceProposalMixin:
    """The silence proposal's flow. Mixed into ``ChapterWorkbenchDialog``."""

    _book: Any
    _run_background: Callable[..., None] | None
    _propose_btn: Any = None
    #: The running scan's token; ``None`` when no scan is running.
    _silence_scan: dict[str, bool] | None = None

    # Provided by the dialog.
    def _apply(self, chapters: list[Any], *, select: int, spoken: str) -> None: ...
    def _announce(self, text: str) -> None: ...
    def _error(self, message: str) -> None: ...

    def _set_scanning(self, token: dict[str, bool] | None) -> None:
        self._silence_scan = token
        button = self._propose_btn
        if button is not None and button:
            button.SetLabel(str(_(STOP_LABEL if token is not None else PROPOSE_LABEL)))

    def _cancel_silence_scan(self, *, spoken: bool = True) -> None:
        token = self._silence_scan
        if token is None:
            return
        token["cancelled"] = True
        self._set_scanning(None)
        if spoken:
            self._announce(str(_("Chapter proposal stopped. The chapter list is unchanged.")))

    def _ask_keep_or_replace(self, count: int) -> str | None:
        """``"keep"``, ``"replace"`` or ``None`` (cancel). Keep is the default."""
        from quill.ui.dialog_contract import show_modal_dialog

        dialog = wx.MessageDialog(
            self,  # type: ignore[arg-type]
            str(
                _(
                    "This recording already has {count} chapters. Keep them and add "
                    "only the proposed boundaries that are new, or replace them with "
                    "the proposal? Restore original undoes either."
                ).format(count=count)
            ),
            str(_("Chapters already here")),
            wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION,
        )
        dialog.SetYesNoCancelLabels(
            str(_("Keep mine, add proposals")), str(_("Replace with the proposal")), "Cancel"
        )
        try:
            answer = show_modal_dialog(dialog, str(_("Chapters already here")))
        finally:
            dialog.Destroy()
        if answer == wx.ID_YES:
            return "keep"
        if answer == wx.ID_NO:
            return "replace"
        return None

    def _on_propose_from_silences(self) -> None:
        """Ask the two knobs, then scan in the background; pressed again, stop."""
        if self._silence_scan is not None:
            self._cancel_silence_scan()
            return
        from quill.core.speech.silence import detect_silence_chapters

        with SilenceParamsDialog(self) as dlg:  # type: ignore[arg-type]
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: native modal
                return
            noise_db, min_silence_s = dlg.values()
        if not self._book.path.is_file():
            self._error(str(_("The book file is missing on disk.")))
            return
        existing = list(self._book.chapters)
        choice = "replace"
        if has_authored_chapters(existing):
            answer = self._ask_keep_or_replace(len(existing))
            if answer is None:
                return
            choice = answer
        path = self._book.path
        token = {"cancelled": False}
        self._set_scanning(token)

        def work(_progress: object = None) -> object:
            try:
                return detect_silence_chapters(
                    path,
                    noise_db=noise_db,
                    min_silence_s=min_silence_s,
                    min_chapter_ms=5000,
                    title_prefix=PROPOSED_TITLE,
                )
            except Exception as exc:  # noqa: BLE001 - delivered to on_success to reset
                return exc

        def on_success(result: object) -> None:
            if token["cancelled"] or not self:
                return
            self._set_scanning(None)
            if isinstance(result, Exception):
                self._error(str(result))
                return
            self._land_proposal(result, existing, choice)

        if self._run_background is not None:
            self._run_background(str(_("Proposing chapters from silences")), work, on_success)
            return
        on_success(work())

    def _land_proposal(self, result: object, existing: list[Any], choice: str) -> None:
        if not isinstance(result, list) or len(result) < 2:
            self._announce(str(_("No silences long enough were found; no changes made.")))
            return
        if choice == "keep":
            merged = merge_proposals(existing, result, int(self._book.total_ms))
            added = len(merged) - len(existing)
            if added <= 0:
                self._announce(
                    str(_("Every proposed boundary is already one of yours; no changes made."))
                )
                return
            self._apply(
                merged,
                select=0,
                spoken=str(
                    _(
                        "Kept your {kept} chapters and added {added} proposed ones, "
                        "titled Proposed chapter. Review, rename, or Restore original."
                    ).format(kept=len(existing), added=added)
                ),
            )
            return
        proposed = retitle_as_proposed(result)
        self._apply(
            proposed,
            select=0,
            spoken=str(
                _(
                    "Proposed {count} chapters from silences, titled Proposed chapter. "
                    "Review, rename, or Restore original."
                ).format(count=len(proposed))
            ),
        )


def bind_host_shortcuts(dialog: Any, shortcuts: dict[str, Callable[[], None] | None]) -> None:
    """Make the host's own playback keys work inside the modal Workbench.

    Quill Studio passes its Sleep Timer and Play Queue handlers so a listener
    can reach them while a book plays in the Workbench; until 2026-10-16 it
    passed them to a function that did not accept them, so Studio's Edit a
    Book raised before the Workbench opened. *shortcuts* maps a chord in
    ``wx.AcceleratorEntry`` spelling to a handler; ``None`` handlers are
    skipped.
    """
    entries = []
    for chord, handler in shortcuts.items():
        if handler is None:
            continue
        entry = wx.AcceleratorEntry()
        if not entry.FromString(chord):
            continue
        command_id = wx.NewIdRef()
        dialog.Bind(wx.EVT_MENU, lambda _e, run=handler: run(), id=command_id)
        entries.append(wx.AcceleratorEntry(entry.GetFlags(), entry.GetKeyCode(), int(command_id)))
    if entries:
        dialog.SetAcceleratorTable(wx.AcceleratorTable(entries))


def pick_recording(parent: Any, default_dir: str = "") -> Any:
    """Find Chapters in a Recording's file picker: a ``Path``, or ``None`` on Cancel."""
    from pathlib import Path

    with wx.FileDialog(
        parent,
        str(_("Find chapters in a recording")),
        defaultDir=default_dir,
        wildcard=RECORDING_WILDCARD,
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    ) as dialog:
        if dialog.ShowModal() != wx.ID_OK:  # GATE-42-OK: native file picker
            return None
        return Path(dialog.GetPath())
