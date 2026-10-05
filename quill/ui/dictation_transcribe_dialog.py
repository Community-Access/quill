"""Transcribe a Recording: choose the recording, the model, and where the text goes.

Shared by QUILL and QUILL Lite (Tools > Dictation in QUILL Lite, Tools >
Speech > Live Dictation in QUILL, Shift+F5 in both). One small window:

* **Recording** -- typed, chosen with Browse (several at once queue one after
  another), or dropped on the window.
* **Speech model** -- every engine this computer has, most accurate first and
  the most accurate local one chosen (:mod:`~quill.core.windows_dictation.file_models`),
  with OpenAI's models joining the list once OpenAI has said which ones the
  saved key may use. Under it, what the model is good for and how long this
  recording should take with it.
* **Language**, **where the text goes** (a new document, or this one at the
  cursor), **timestamps** on each paragraph, and whether spoken punctuation and
  commands are obeyed.

While a transcription is running the window says so, and **Stop Transcribing**
stops it and anything waiting. The work itself is
:mod:`quill.ui.windows_dictation_transcribe`'s; this window only asks.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import wx

from quill.core.windows_dictation.file_models import (
    FileModel,
    default_model,
    estimate_sentence,
    file_models,
)
from quill.core.windows_dictation.speech_language import SPEECH_LANGUAGES
from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["DESTINATIONS", "STOP_TRANSCRIBING", "TranscribeChoice", "TranscribeFileDialog"]

#: What Stop Transcribing ends the window with.
STOP_TRANSCRIBING = 5811

#: (value, label) for where the text goes.
DESTINATIONS: tuple[tuple[str, str], ...] = (
    ("new", "A new document"),
    ("cursor", "This document, at the cursor, when it finishes"),
)

_PAD = 8


@dataclass(frozen=True, slots=True)
class TranscribeChoice:
    """Everything the window asked, read after OK."""

    paths: tuple[Path, ...]
    model: FileModel
    language: str
    destination: str
    timestamps: bool
    obey_commands: bool


class _Drop(wx.FileDropTarget):
    """A recording dropped on the window fills the Recording box."""

    def __init__(self, dialog: TranscribeFileDialog) -> None:
        super().__init__()
        self._dialog = dialog

    def OnDropFiles(self, _x: int, _y: int, filenames: Sequence[str]) -> bool:  # noqa: N802
        self._dialog.set_paths([Path(name) for name in filenames])
        return True


class TranscribeFileDialog(wx.Dialog):
    """Ask what to transcribe and how. Read with :meth:`choice` after OK."""

    def __init__(
        self,
        parent: Any,
        *,
        language: str = "en",
        paths: Sequence[Path] = (),
        running: str = "",
        weak: bool | None = None,
        load_openai: bool = True,
        warn: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent, title="Transcribe a Recording")
        self._paths: list[Path] = [Path(path) for path in paths]
        self._openai: list[str] = []
        self._models: list[FileModel] = []
        self._weak = _weak_computer() if weak is None else weak
        self._warn = warn
        self.chosen: TranscribeChoice | None = None
        root = wx.BoxSizer(wx.VERTICAL)

        if running:
            running_label = wx.StaticText(self, label="Transcribing now:")
            self.running = wx.TextCtrl(
                self, value=running, style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_NO_VSCROLL
            )
            self.running.SetName("Transcribing now")
            self.running.SetHelpText(
                "What is being transcribed at the moment, how far it has got, and how "
                "many recordings are waiting after it."
            )
            stop = wx.Button(self, STOP_TRANSCRIBING, label="&Stop Transcribing")
            stop.SetHelpText(
                "Stops the transcription that is running and forgets any recordings "
                "waiting after it. Nothing is written into a document."
            )
            stop.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(STOP_TRANSCRIBING))
            root.Add(running_label, 0, wx.LEFT | wx.TOP, _PAD)
            root.Add(self.running, 0, wx.EXPAND | wx.ALL, _PAD)
            root.Add(stop, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)

        file_label = wx.StaticText(self, label="&Recording:")
        self.file = wx.TextCtrl(self)
        self.file.SetHelpText(
            "The recording to turn into text: MP3, M4A, AAC, WAV, Ogg, Opus, FLAC or "
            "WMA. Type its full path, choose it with Browse, or drop the file on this "
            "window. Choosing several with Browse transcribes them one after another."
        )
        browse = wx.Button(self, label="&Browse...")
        browse.SetHelpText(
            "Opens the file picker. Hold Ctrl to choose several recordings; they are "
            "transcribed one after another with the same choices."
        )
        browse.Bind(wx.EVT_BUTTON, self._on_browse)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(self.file, 1, wx.EXPAND | wx.RIGHT, _PAD)
        row.Add(browse, 0)
        root.Add(file_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(row, 0, wx.EXPAND | wx.ALL, _PAD)

        language_label = wx.StaticText(self, label="&Language spoken in the recording:")
        self._languages = [value for value, _label in SPEECH_LANGUAGES]
        self.language = wx.Choice(
            self, choices=[label.split(" (", 1)[0] for _v, label in SPEECH_LANGUAGES]
        )
        self.language.SetSelection(
            self._languages.index(language) if language in self._languages else 0
        )
        self.language.SetHelpText(
            "English or Spanish. The model list shows only the models that know the "
            "language chosen here."
        )
        self.language.Bind(wx.EVT_CHOICE, lambda _e: self._fill_models())
        root.Add(language_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.language, 0, wx.EXPAND | wx.ALL, _PAD)

        model_label = wx.StaticText(self, label="Speech &model:")
        self.model = wx.Choice(self)
        self.model.SetHelpText(
            "Every speech model on this computer, most accurate first, with the most "
            "accurate one chosen for you: the two built into QUILL, any you downloaded "
            "in Dictation Settings, Speech Models, and OpenAI's models when your own "
            "OpenAI key is saved. A slower model is fine for a recording: nobody is "
            "waiting for each phrase, and you can keep working."
        )
        self.model.Bind(wx.EVT_CHOICE, lambda _e: self._describe())
        about_label = wx.StaticText(self, label="About this model and this recording:")
        self.about = wx.TextCtrl(self, style=wx.TE_READONLY | wx.TE_MULTILINE, size=(-1, 90))
        self.about.SetName("About this model and this recording")
        self.about.SetHelpText(
            "What the chosen model is good for, how long the recording is, and about "
            "how long transcribing it should take on this computer."
        )
        root.Add(model_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.model, 0, wx.EXPAND | wx.ALL, _PAD)
        root.Add(about_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.about, 0, wx.EXPAND | wx.ALL, _PAD)

        where_label = wx.StaticText(self, label="Put the text &in:")
        self._destinations = [value for value, _label in DESTINATIONS]
        self.destination = wx.Choice(self, choices=[label for _v, label in DESTINATIONS])
        self.destination.SetSelection(0)
        self.destination.SetHelpText(
            "A new document is the default: the transcript opens in a document of its "
            "own when it is ready. This document puts it where the cursor is in this "
            "document at the moment it finishes, as one step Ctrl+Z can take back."
        )
        root.Add(where_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.destination, 0, wx.EXPAND | wx.ALL, _PAD)

        self.timestamps = wx.CheckBox(self, label="Add &timestamps")
        self.timestamps.SetValue(False)  # off unless the person checks it (owner, 2026-10-05)
        self.timestamps.SetHelpText(
            "Off unless you check it. A new paragraph starts wherever the recording "
            "pauses for two seconds or more; with timestamps checked, each paragraph "
            "begins with the hours, minutes and seconds into the recording where it was "
            "said, like [00:01:23], so you can find it again."
        )
        self.obey = wx.CheckBox(self, label="&Obey spoken punctuation and commands")
        self.obey.SetHelpText(
            "Off by default: in a recording, somebody who says new paragraph or comma "
            "usually means the words. Turn it on for a recording you dictated on "
            "purpose, and comma, period, new line, new paragraph and scratch that work "
            "as they do in dictation. Commands that move the cursor are ignored."
        )
        root.Add(self.timestamps, 0, wx.ALL, _PAD)
        root.Add(self.obey, 0, wx.ALL, _PAD)

        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        ok = self.FindWindowById(wx.ID_OK, self)
        if ok is not None:
            ok.SetLabel("Transcribe")
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, _PAD)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self.file.Bind(wx.EVT_TEXT, self._on_typed)
        self.SetDropTarget(_Drop(self))
        self.file.SetDropTarget(_Drop(self))
        self._show_paths()
        self._fill_models()
        self.SetSizerAndFit(root)
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self.file.SetFocus()
        if load_openai:
            self._load_openai()

    # -- the recording ---------------------------------------------------------- #

    def set_paths(self, paths: Sequence[Path]) -> None:
        self._paths = [Path(path) for path in paths if str(path).strip()]
        self._show_paths()
        self._describe()

    def _show_paths(self) -> None:
        if len(self._paths) > 1:
            text = f"{len(self._paths)} recordings: " + "; ".join(path.name for path in self._paths)
        else:
            text = str(self._paths[0]) if self._paths else ""
        self.file.ChangeValue(text)

    def _on_typed(self, event: Any) -> None:
        event.Skip()
        typed = self.file.GetValue().strip().strip('"')
        self._paths = [Path(typed)] if typed else []
        self._describe()

    def _on_browse(self, _event: Any) -> None:
        from quill.core.windows_dictation.audio_file import file_filter

        with wx.FileDialog(
            self,
            "Choose recordings to transcribe",
            wildcard=file_filter(),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:
                return
            self.set_paths([Path(name) for name in picker.GetPaths()])
        self.file.SetFocus()

    # -- the models --------------------------------------------------------------- #

    def _language(self) -> str:
        return self._languages[max(0, self.language.GetSelection())]

    def _fill_models(self) -> None:
        chosen = self.selected_model()
        self._models = file_models(self._language(), self._openai)
        self.model.Set([model.label for model in self._models])
        ids = [model.id for model in self._models]
        keep = chosen.id if chosen is not None and chosen.id in ids else None
        fallback = default_model(self._models)
        target = keep or (fallback.id if fallback is not None else None)
        if target is not None:
            self.model.SetSelection(ids.index(target))
        self._describe()

    def selected_model(self) -> FileModel | None:
        row = self.model.GetSelection() if self._models else wx.NOT_FOUND
        return self._models[row] if 0 <= row < len(self._models) else None

    def _describe(self) -> None:
        model = self.selected_model()
        if model is None:
            self.about.SetValue("No speech model is available for this language here.")
            return
        from quill.core.windows_dictation.audio_file import duration_of

        lines = [model.description]
        if len(self._paths) == 1 and self._paths[0].is_file():
            lines.append(estimate_sentence(model, duration_of(self._paths[0]), weak=self._weak))
        elif len(self._paths) > 1:
            total = sum(duration_of(path) for path in self._paths if path.is_file())
            lines.append(estimate_sentence(model, total, weak=self._weak))
        self.about.SetValue("\n".join(lines))

    def _load_openai(self) -> None:
        """OpenAI's list for the saved key, read on a worker; never on this thread."""
        from quill.core.windows_dictation.openai_models import cloud_problem

        if cloud_problem():
            return  # no key, or Safe Mode: OpenAI is simply not offered
        from quill.core.windows_dictation.openai_models import list_transcription_models, load_key
        from quill.ui.update_download import thread_submit

        key = load_key()

        def work(**_kwargs: Any) -> tuple[list[str], str]:
            return list_transcription_models(key)

        def done(_name: str, result: Any) -> None:
            wx.CallAfter(self.show_openai, list(result[0]))

        thread_submit("quill-transcribe-openai-models", work, on_success=done)

    def show_openai(self, models: Sequence[str]) -> None:
        """Add OpenAI's models to the list, keeping the person's choice."""
        if not self:
            return
        self._openai = list(models)
        self._fill_models()

    # -- reading it back ----------------------------------------------------------- #

    def _on_ok(self, event: Any) -> None:
        problem = self._problem()
        if problem:
            if self._warn is not None:
                self._warn(problem)
            else:
                from quill.ui.dialog_contract import show_message_box

                show_message_box(problem, "Transcribe a Recording", wx.OK | wx.ICON_WARNING, self)
            (self.model if "model" in problem else self.file).SetFocus()
            return
        model = self.selected_model()
        assert model is not None
        self.chosen = TranscribeChoice(
            paths=tuple(self._paths),
            model=model,
            language=self._language(),
            destination=self._destinations[max(0, self.destination.GetSelection())],
            timestamps=self.timestamps.GetValue(),
            obey_commands=self.obey.GetValue(),
        )
        event.Skip()

    def _problem(self) -> str:
        if not self._paths:
            return "Choose a recording to transcribe first: type its path, or use Browse."
        missing = [path.name or str(path) for path in self._paths if not path.is_file()]
        if missing:
            return f"{missing[0]} was not found. Check the path, or choose it with Browse."
        if self.selected_model() is None:
            return "There is no speech model for this language here; choose another language."
        return ""

    def choice(self) -> TranscribeChoice | None:
        return self.chosen


def _weak_computer() -> bool:
    """The two-second check's hardware answer, without timing a model."""
    try:
        from quill.core.windows_dictation.speed_check import run

        return run(timer=lambda: None).weak
    except Exception:  # noqa: BLE001 - assume the modest computer
        return True
