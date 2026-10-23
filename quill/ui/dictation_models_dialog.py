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

**The recommendation** (dict.md D-22, :mod:`quill.core.windows_dictation.model_advice`)
sits above the list as read-only text: one model for this computer, the
dictation language and What matters most, with its reasons. It is written
from the cores and memory at once and rewritten when the timed check ends.
Show Recommended Model moves to its row; nothing is downloaded or chosen for
the person. Switch to Recommended Model chooses it, when it is on this
computer, and changes nothing but the model. Every row and details box names
the model's tier (Lightweight, Balanced or High accuracy).

**After a switch** (:func:`offer_to_remove_replaced`), once the new model is
saved, the old one's files are offered for deletion -- No by default, naming
the space it frees -- because a switch is when a large download stops earning
its place, and the person may never come back here to remove it. Never while
dictation may still hold the old model (the delete would fail), and the
question leads with what changed, because it arrives after the window that
made the change has closed (accessibility review, 2026-10-23).

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

from quill.core.windows_dictation import model_advice, model_store, speed_check
from quill.core.windows_dictation.model_catalog import (
    CATALOGUE,
    DownloadableModel,
    downloadable,
    megabytes,
)
from quill.core.windows_dictation.model_types import TIER_MEANINGS
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button, show_message_box

__all__ = ["SpeechModelsDialog", "offer_to_remove_replaced", "open_speech_models", "will_offer"]

_PAD = 8
_TINY_ROW = (
    "Whisper tiny, Lightweight: built in. Fastest and lightest, weakest accuracy; a "
    "VS Code alternative. Already installed."
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
        language: str = "en",
    ) -> None:
        super().__init__(
            parent, title="Speech Models", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._announce = announce or (lambda _text: None)
        self.chosen: str | None = None
        self._check: speed_check.SpeedCheck | None = None
        self._language = language
        self._recommendation: model_advice.Recommendation | None = None
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

        # D-22: one model suggested for this computer, with its reasons as text
        # to read, never a switch.
        priority_label = wx.StaticText(self, label="&What matters most:")
        self.priority = wx.Choice(self, choices=[label for _v, label in model_advice.PRIORITIES])
        self.priority.SetHelpText(
            "What the recommendation below aims for: a balance of speed and accuracy, "
            "the quickest response after you pause, or the fewest mistakes this "
            "computer can keep up with. It only changes the advice, never your model."
        )
        self.priority.SetSelection(0)
        self.priority.Bind(wx.EVT_CHOICE, self._on_priority)
        advice_label = wx.StaticText(self, label="Re&commendation:")
        self.advice = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.advice.SetHelpText(
            "The model that suits this computer and why: whether it keeps up, about "
            "how soon your words appear after you pause, its tier and its download "
            "size. The figures are estimates. Nothing changes until you choose a model."
        )
        self.show_recommended = wx.Button(self, label="&Show Recommended Model")
        self.show_recommended.SetHelpText(
            "Move to the recommended model in the list below, to read its details and "
            "download or use it. It does not download or choose anything."
        )
        self.show_recommended.Bind(wx.EVT_BUTTON, self._on_show_recommended)
        priority_row = wx.BoxSizer(wx.HORIZONTAL)
        priority_row.Add(priority_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, _PAD)
        priority_row.Add(self.priority, 1)
        root.Add(priority_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, _PAD)
        root.Add(advice_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.advice, 0, wx.EXPAND | wx.ALL, _PAD)
        self.switch_recommended = wx.Button(self, label="Switc&h to Recommended Model")
        self.switch_recommended.SetHelpText(
            "Choose the recommended model as the speech engine, changing nothing else. "
            "From Dictation Settings, press OK there to keep it. A model not yet on this "
            "computer is not downloaded: you are told, and taken to its row."
        )
        self.switch_recommended.Bind(wx.EVT_BUTTON, self._on_switch_recommended)
        recommended_row = wx.BoxSizer(wx.HORIZONTAL)
        recommended_row.Add(self.show_recommended, 0, wx.RIGHT, _PAD)
        recommended_row.Add(self.switch_recommended, 0)
        root.Add(recommended_row, 0, wx.LEFT | wx.RIGHT, _PAD)

        label = wx.StaticText(self, label="Speech &models:")
        self.models = wx.ListBox(self, choices=[self._row_text(row) for row in self._rows])
        self.models.SetHelpText(
            "The optional speech models, the ones VS Code offers first and then the rest "
            "of the Whisper family. Each row says its tier (Lightweight, Balanced or High "
            "accuracy), what the model is good for, its size and whether it is on this "
            "computer. Details below say more."
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
        self.SetSize((680, 720))
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)
        bind_close_button(self, close, modeless=False)
        self.download.Bind(wx.EVT_BUTTON, self._on_download)
        self.cancel_download.Bind(wx.EVT_BUTTON, lambda _e: self._cancel.set())
        self.remove.Bind(wx.EVT_BUTTON, self._on_remove)
        self.use.Bind(wx.EVT_BUTTON, self._on_use)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
        self.models.SetSelection(0)
        self._show_details()
        self._show_advice(speed_check.latest())
        self.models.SetFocus()
        self._start_check(run_check or speed_check.run)

    # -- the list ----------------------------------------------------------- #

    def _row_text(self, row: DownloadableModel | None) -> str:
        if row is None:
            return _TINY_ROW
        return (
            f"{row.name}, {row.tier}: {row.good_for} {megabytes(row.download_bytes)}. "
            f"{_status(row)}."
        )

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
            f"Tier: {TIER_MEANINGS[model.tier]}",
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
        self._show_advice(result)

    # -- the recommendation (D-22) ------------------------------------------ #

    def _show_advice(self, check: speed_check.SpeedCheck) -> None:
        """Write the recommendation for *check* and the chosen priority. Silent:
        the text is there to read, and a check finishing is not news."""
        priority = model_advice.PRIORITIES[max(0, self.priority.GetSelection())][0]
        advice = model_advice.recommend(check, self._language, priority=priority)
        self._recommendation = advice
        self.advice.SetValue(advice.details)
        self.show_recommended.Enable(self._recommended_row() is not None)
        # Enabled whenever there is advice, so Tab always reaches it; pressing it
        # when the model is not here says so rather than sitting greyed out.
        self.switch_recommended.Enable(bool(advice.model_id))

    def _recommended_row(self) -> int | None:
        advice = self._recommendation
        if advice is None:
            return None
        for index, row in enumerate(self._rows):
            row_id = "whisper" if row is None else row.id  # the built-in tiny row
            if row_id == advice.model_id:
                return index
        return None  # Moonshine, built in, has no row here

    def _on_priority(self, _event: Any) -> None:
        self._show_advice(self._check or speed_check.latest())
        if self._recommendation is not None:
            # The focus stays on the choice, so the new advice is news.
            self._announce(f"Recommended: {self._recommendation.name}.")

    def _on_show_recommended(self, _event: Any) -> None:
        index = self._recommended_row()
        if index is None:
            return
        self.models.SetSelection(index)
        self._show_details()
        self.models.SetFocus()  # the reader says the row it lands on

    def _on_switch_recommended(self, _event: Any) -> None:
        advice = self._recommendation
        if advice is None:
            return
        if self._busy is not None:  # closing would stop the download silently
            self._tell(
                "A model is downloading. Wait for it, or press Cancel Download first.",
                wx.ICON_INFORMATION,
            )
            return
        if not advice.built_in:
            model = downloadable(advice.model_id)
            if model is None or not model_store.installed(model):
                # Said before focus moves, so the box does not cut off the row.
                self._tell(
                    f"{advice.name} is not on this computer yet. Download it, then switch.",
                    wx.ICON_INFORMATION,
                )
                self._on_show_recommended(None)
                return
        self.chosen = advice.model_id
        self.EndModal(wx.ID_OK)

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
        self.progress.SetValue(f"{model.name} was removed. {megabytes(model.disk_bytes)} freed.")
        self._refresh()
        self.models.SetFocus()  # Remove is disabled now; focus must not fall to nowhere
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


def _engine_name(engine_id: str) -> str:
    model = downloadable(engine_id)
    if model is not None:
        return model.name
    from quill.core.windows_dictation.engines import engine_info

    return engine_info(engine_id).label.split(" (")[0]


def will_offer(old_engine: str, new_engine: str, *, in_use: bool = False) -> bool:
    """Whether :func:`offer_to_remove_replaced` would ask: a switch away from a
    downloaded model still on this computer, which dictation is not holding."""
    if in_use or not old_engine or old_engine == new_engine:
        return False
    model = downloadable(old_engine)
    return model is not None and model_store.installed(model)


def offer_to_remove_replaced(
    parent: Any,
    old_engine: str,
    new_engine: str,
    announce: Callable[[str], None],
    *,
    in_use: bool = False,
) -> bool:
    """After a switch from *old_engine* to *new_engine* has been saved, offer to
    delete the old model's files. Returns whether they were deleted.

    No is the default: deleting is the one answer that costs a download to undo.
    Not asked while dictation may hold the old model (*in_use*), when there is
    nothing to delete (a built-in engine, a model not here) or nothing changed.
    The question leads with the switch, so it stands on its own when heard
    straight after the window that made it; a caller announcing the switch
    itself should skip that when :func:`will_offer` says the box will say it.
    """
    if not will_offer(old_engine, new_engine, in_use=in_use):
        return False
    model = downloadable(old_engine)
    assert model is not None  # will_offer checked
    freed = megabytes(model.disk_bytes)
    answer = show_message_box(
        f"Now using {_engine_name(new_engine)}. Delete {model.name} to free {freed}? "
        "QUILL, QUILL Lite and QUILL Transcribe share its files; any of them still set "
        f"to {model.name} will need it downloaded again.",
        "Delete Old Speech Model",
        wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        parent,
    )
    if answer != wx.YES:
        return False
    try:
        model_store.remove(model.id)
    except model_store.ModelDownloadError:
        show_message_box(
            f"{model.name} could not be deleted; something may still be using it. "
            "Remove it in Speech Models later.",
            "Delete Old Speech Model",
            wx.OK | wx.ICON_WARNING,
            parent,
        )
        return False
    announce(f"{model.name} deleted. {freed} freed.")
    return True


def open_speech_models(
    parent: Any, announce: Callable[[str], None] | None = None, *, language: str = "en"
) -> str | None:
    """Show Speech Models; return the model chosen with Use for Dictation or
    Switch to Recommended Model, if any.
    *language* is the dictation language, which the recommendation follows."""
    from quill.ui.dialog_contract import show_modal_dialog

    dialog = SpeechModelsDialog(parent, announce, language=language)
    try:
        show_modal_dialog(dialog, "Speech Models")
        return dialog.chosen
    finally:
        dialog.Destroy()
