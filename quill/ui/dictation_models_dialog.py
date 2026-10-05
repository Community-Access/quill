"""Speech Models: the optional, better-accuracy models, downloaded on request.

Reached from Dictation Settings (Better Accuracy: Speech Models...) in both
editors, through the shared dialog, so QUILL and QUILL Lite cannot drift.

**What it promises.** Dictation already works with the built-in engines; this
window only adds. Nothing downloads until the person presses Download and says
yes to a sentence that names the source, the sizes, the licence, where the
model will be saved and that their voice never leaves the computer. On a
metered connection it asks first. It checks the free space, shows progress
with a Cancel Download button, keeps what arrived so the next Download carries
on, checks every file against its pinned checksum, and Remove frees the space
again. The models are shared with the other editor on the same computer, and in
a portable copy they are saved inside the portable folder
(:mod:`quill.core.windows_dictation.model_store`).

**The two-second check** (:mod:`quill.core.windows_dictation.speed_check`) runs
when the window opens, on a worker; each model's details then say whether this
computer should keep up, and the download question repeats it.

The list is our suggested order: the models VS Code offers first, with
Nemotron as the suggested download, then the rest of the Whisper family. The
built-in Whisper tiny is listed in its VS Code place, already installed.

Speech here is only what the screen reader cannot know (GATE-13): when a
download starts, every quarter, and how it ended.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from typing import Any

import wx

from quill.core.windows_dictation import model_store, speed_check
from quill.core.windows_dictation.model_catalog import (
    CATALOGUE,
    DownloadableModel,
    megabytes,
)
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button, show_message_box

__all__ = ["SpeechModelsDialog", "open_speech_models"]

_PAD = 8
_TINY_ROW = (
    "Whisper tiny: built in. Fastest and lightest, weakest accuracy; a VS Code "
    "alternative. Already installed."
)
#: Where the built-in Whisper tiny sits in the list: after the VS Code models.
_TINY_AFTER = "whisper_base"


def _status(model: DownloadableModel) -> str:
    if model_store.installed(model):
        return "Downloaded"
    if model_store.remaining_bytes(model) < model.download_bytes:
        return "Partly downloaded; Download carries on"
    return "Suggested download" if model.suggested else "Not downloaded"


class SpeechModelsDialog(wx.Dialog):
    """The optional speech models. :attr:`chosen` is set by Use for Dictation."""

    def __init__(
        self,
        parent: Any,
        announce: Callable[[str], None] | None = None,
        *,
        run_check: Callable[[], speed_check.SpeedCheck] | None = None,
    ) -> None:
        super().__init__(
            parent, title="Speech Models", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._announce = announce or (lambda _text: None)
        self.chosen: str | None = None
        self._check: speed_check.SpeedCheck | None = None
        self._cancel = threading.Event()
        self._busy: DownloadableModel | None = None
        self._last_quarter = -1
        #: One entry per list row: a model, or None for the built-in tiny row.
        self._rows: list[DownloadableModel | None] = []
        for model in CATALOGUE:
            self._rows.append(model)
            if model.id == _TINY_AFTER:
                self._rows.append(None)

        root = wx.BoxSizer(wx.VERTICAL)
        intro = wx.StaticText(
            self,
            label=(
                "Dictation already works with the built-in engines. These are optional, "
                "larger models for better accuracy, in our suggested order; your voice "
                "never leaves this computer."
            ),
        )
        intro.Wrap(620)
        root.Add(intro, 0, wx.ALL, _PAD)
        label = wx.StaticText(self, label="Speech &models:")
        self.models = wx.ListBox(self, choices=[self._row_text(row) for row in self._rows])
        self.models.SetHelpText(
            "The optional speech models, the ones VS Code offers first and then the rest "
            "of the Whisper family. Each row says what the model is good for, its size "
            "and whether it is on this computer. Details below say more."
        )
        self.models.Bind(wx.EVT_LISTBOX, lambda _e: self._show_details())
        root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.models, 1, wx.EXPAND | wx.ALL, _PAD)

        details_label = wx.StaticText(self, label="De&tails:")
        self.details = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.details.SetHelpText(
            "About the chosen model: what it is better at, its languages, download and "
            "disk size, what computer suits it and whether this one should keep up, its "
            "published accuracy, its licence and where it is saved."
        )
        root.Add(details_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.details, 1, wx.EXPAND | wx.ALL, _PAD)

        progress_label = wx.StaticText(self, label="&Progress:")
        self.progress = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.progress.SetName("Download progress")
        self.progress.SetHelpText("How far the current download has got, or how it ended.")
        self.gauge = wx.Gauge(self, range=100)
        self.gauge.SetName("Download progress")
        self.gauge.SetHelpText("How far the current download has got.")
        root.Add(progress_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.progress, 0, wx.EXPAND | wx.ALL, _PAD)
        root.Add(self.gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, _PAD)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.download = wx.Button(self, label="&Download...")
        self.download.SetHelpText(
            "Download the chosen model, after a question that names where it comes from, "
            "its size, its licence and where it will be saved. A download that was "
            "stopped carries on from where it stopped."
        )
        self.cancel_download = wx.Button(self, label="Cance&l Download")
        self.cancel_download.SetHelpText(
            "Stop the download. What has arrived is kept, so Download carries on later."
        )
        self.remove = wx.Button(self, label="&Remove")
        self.remove.SetHelpText("Delete the chosen model from this computer to free the space.")
        self.use = wx.Button(self, label="&Use for Dictation")
        self.use.SetHelpText(
            "Choose this downloaded model as the speech engine. Dictation Settings shows "
            "it chosen; press OK there to keep it."
        )
        close = wx.Button(self, wx.ID_CANCEL, "Close")
        close.SetHelpText("Close this window. A download in progress is stopped and kept.")
        for button in (self.download, self.cancel_download, self.remove, self.use, close):
            buttons.Add(button, 0, wx.RIGHT, _PAD)
        root.Add(buttons, 0, wx.ALL, _PAD)
        self.SetSizer(root)
        self.SetSize((680, 600))
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)
        bind_close_button(self, close, modeless=False)
        self.download.Bind(wx.EVT_BUTTON, self._on_download)
        self.cancel_download.Bind(wx.EVT_BUTTON, lambda _e: self._cancel.set())
        self.remove.Bind(wx.EVT_BUTTON, self._on_remove)
        self.use.Bind(wx.EVT_BUTTON, self._on_use)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
        self.models.SetSelection(0)
        self._show_details()
        self.models.SetFocus()
        self._start_check(run_check or speed_check.run)

    # -- the list ----------------------------------------------------------- #

    def _row_text(self, row: DownloadableModel | None) -> str:
        if row is None:
            return _TINY_ROW
        return f"{row.name}: {row.good_for} {megabytes(row.download_bytes)}. {_status(row)}."

    def selected(self) -> DownloadableModel | None:
        index = self.models.GetSelection()
        return self._rows[index] if 0 <= index < len(self._rows) else None

    def _refresh(self) -> None:
        for index, row in enumerate(self._rows):
            text = self._row_text(row)
            if self.models.GetString(index) != text:
                self.models.SetString(index, text)
        self._show_details()

    def details_text(self, model: DownloadableModel) -> str:
        verdict = speed_check.verdict(model, self._check)
        lines = [
            model.description,
            f"Good for: {model.good_for}",
            f"Languages: {model.language_names}.",
            f"Download: {megabytes(model.download_bytes)}. On disk: {megabytes(model.disk_bytes)}.",
            f"Works best on: {model.works_best_on}",
            verdict or "Checking this computer's speed...",
            f"Accuracy: {model.accuracy}",
            f"Licence: {model.licence}, {model.licence_url}",
            f"Saved in: {model_store.model_folder(model)}",
            f"Status: {_status(model)}.",
        ]
        return "\n".join(lines)

    def _show_details(self) -> None:
        model = self.selected()
        if model is None:
            self.details.SetValue(_TINY_ROW + " It is the built-in Whisper engine.")
        else:
            self.details.SetValue(self.details_text(model))
        here = model is not None and model_store.installed(model)
        idle = self._busy is None
        self.download.Enable(idle and model is not None and not here)
        self.cancel_download.Enable(not idle)
        self.remove.Enable(
            idle and model is not None and (here or _status(model).startswith("Partly"))
        )
        self.use.Enable(here)

    # -- the two-second check ----------------------------------------------- #

    def _start_check(self, run_check: Callable[[], speed_check.SpeedCheck]) -> None:
        def work() -> None:
            result = run_check()
            wx.CallAfter(self._check_done, result)

        threading.Thread(  # GATE-40-OK: two-second speed check, result marshalled back
            target=work, name="quill-dictation-speed-check", daemon=True
        ).start()

    def _check_done(self, result: speed_check.SpeedCheck) -> None:
        if not self:
            return
        self._check = result
        self._show_details()

    # -- download ----------------------------------------------------------- #

    def confirmation(self, model: DownloadableModel) -> str:
        """The question asked before anything is downloaded."""
        verdict = speed_check.verdict(model, self._check)
        return (
            f"Download {model.name}?\n\n"
            f"It comes from {model.source}: {megabytes(model.download_bytes)} to download, "
            f"{megabytes(model.disk_bytes)} on disk. It will be saved in "
            f"{model_store.model_folder(model)}, and QUILL and QUILL Lite on this computer "
            "share it. It stays on this computer: your voice is never sent anywhere.\n\n"
            f"Licence: {model.licence} ({model.licence_url})."
            + (f"\n\n{verdict}" if verdict else "")
        )

    def _on_download(self, _event: Any) -> None:
        model = self.selected()
        if model is None or self._busy is not None or model_store.installed(model):
            return
        if os.environ.get("QUILL_SAFE_MODE") == "1":
            self._tell("Downloading speech models is turned off in Safe Mode.", wx.ICON_WARNING)
            return
        problem = model_store.free_space_problem(model)
        if problem:
            self._tell(problem, wx.ICON_WARNING)
            return
        from quill.core.net_metered import METERED, connection_cost

        if connection_cost() == METERED and not self._ask(
            f"This connection is metered. {model.name} is {megabytes(model.download_bytes)}. "
            "Download it anyway?"
        ):
            return
        if not self._ask(self.confirmation(model)):
            return
        self._begin(model)

    def _begin(self, model: DownloadableModel) -> None:
        self._busy = model
        self._cancel.clear()
        self._last_quarter = -1
        self.gauge.SetValue(0)
        self.progress.SetValue(f"Downloading {model.name}...")
        self._show_details()
        self.cancel_download.SetFocus()
        self._announce(f"Downloading {model.name}.")

        def progress(fraction: float, _message: str) -> None:
            wx.CallAfter(self._on_progress, fraction)

        def work() -> None:
            try:
                model_store.download(model, progress=progress, should_cancel=self._cancel.is_set)
            except BaseException as error:  # noqa: BLE001 - reported as a sentence
                wx.CallAfter(self._finished, model, error)
                return
            wx.CallAfter(self._finished, model, None)

        threading.Thread(  # GATE-40-OK: user-started model download, results marshalled back
            target=work, name="quill-dictation-model-download", daemon=True
        ).start()

    def _on_progress(self, fraction: float) -> None:
        if not self or self._busy is None:
            return
        percent = int(fraction * 100)
        self.gauge.SetValue(percent)
        self.progress.SetValue(f"Downloading {self._busy.name}: {percent} percent.")
        quarter = percent // 25
        if 0 < quarter < 4 and quarter != self._last_quarter:
            self._last_quarter = quarter
            self._announce(f"{percent} percent.")

    def _finished(self, model: DownloadableModel, error: BaseException | None) -> None:
        if not self:
            return
        from quill.core.release_assets import DownloadCancelled

        self._busy = None
        if error is None:
            self.gauge.SetValue(100)
            said = (
                f"{model.name} is downloaded. Press Use for Dictation, or choose it in "
                "the Speech engine list."
            )
        elif isinstance(error, DownloadCancelled):
            said = f"Download of {model.name} stopped. What arrived is kept; Download carries on."
        else:
            said = str(error.args[0]) if error.args else f"{model.name} could not be downloaded."
        self.progress.SetValue(said)
        self._refresh()
        self._announce(said)

    # -- remove and use ----------------------------------------------------- #

    def _on_remove(self, _event: Any) -> None:
        model = self.selected()
        if model is None or self._busy is not None:
            return
        if not self._ask(
            f"Remove {model.name} from this computer? It frees {megabytes(model.disk_bytes)}, "
            "for QUILL and QUILL Lite alike. You can download it again later."
        ):
            return
        try:
            model_store.remove(model.id)
        except model_store.ModelDownloadError as error:
            self._tell(str(error.args[0]), wx.ICON_WARNING)
            return
        self.progress.SetValue(f"{model.name} was removed.")
        self._refresh()
        self._announce(f"{model.name} removed.")

    def _on_use(self, _event: Any) -> None:
        model = self.selected()
        if model is not None and model_store.installed(model):
            self.chosen = model.id
            self.EndModal(wx.ID_OK)

    def _on_destroy(self, event: Any) -> None:
        if event.GetEventObject() is self:
            self._cancel.set()  # a download still running stops; its bytes stay
        event.Skip()

    # -- asking ------------------------------------------------------------- #

    def _ask(self, question: str) -> bool:
        answer = show_message_box(question, "Speech Models", wx.YES_NO | wx.ICON_QUESTION, self)
        return answer == wx.YES

    def _tell(self, sentence: str, icon: int) -> None:
        show_message_box(sentence, "Speech Models", wx.OK | icon, self)


def open_speech_models(parent: Any, announce: Callable[[str], None] | None = None) -> str | None:
    """Show Speech Models; return the model chosen with Use for Dictation, if any."""
    from quill.ui.dialog_contract import show_modal_dialog

    dialog = SpeechModelsDialog(parent, announce)
    try:
        show_modal_dialog(dialog, "Speech Models")
        return dialog.chosen
    finally:
        dialog.Destroy()
