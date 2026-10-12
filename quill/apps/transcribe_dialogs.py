"""QUILL Transcribe's own windows: Set Up, Choose Model and Choose Microphone.

Stock controls only (spec section 8): lists, choices, check boxes and
read-only text a screen reader can review. Everything else QUILL Transcribe
shows is shared with the editors -- Dictation Settings, the Model Library,
Dictation Commands, Transcribe a Recording -- so it works the same way in all
of them.

**Set Up QUILL Transcribe** is one page, not a wizard: what the app does, the
microphone (with a four-second test that never leaves this computer), the
model, the start and stop key, and starting with Windows. Finish keeps the
choices; Skip keeps none of them and opens nothing. Neither installs a model
or leaves the microphone open.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    bind_close_button,
    show_message_box,
)

__all__ = ["ChooseModelDialog", "SetupDialog", "choose_microphone"]

_PAD = 8

INTRO = (
    "QUILL Transcribe types what you say into the program you are using: an email "
    "in Outlook, a form in your browser, a note in Notepad, a document in Word.\n\n"
    "It writes into the field that has the focus when you start, and only that "
    "field. If you move somewhere else, it pauses and keeps your words until you "
    "say where they go. It never reads what is already in the other program.\n\n"
    "Your speech stays on this computer unless you choose an internet model "
    "yourself. Nothing listens until you start dictation, and the microphone "
    "closes when you stop."
)


def _microphones() -> tuple[list[str], str]:
    """``(names, the label of the Windows default row)``."""
    from quill.ui.windows_dictation_devices import default_microphone_name, microphone_names

    names = microphone_names()
    default = default_microphone_name()
    label = f"Windows default microphone ({default})" if default else "Windows default microphone"
    return names, label


def _details(row: Any) -> str:
    where = (
        "Runs on this computer; your speech never leaves it."
        if row.local
        else "Sends your speech over the internet to the provider named below."
    )
    state = "Ready to use." if row.ready else "Not downloaded yet: use the Model Library."
    return (
        f"{row.name}. {where} {state}\n"
        f"Languages: {row.languages}. Size: {row.size}.\n"
        f"From: {row.source}. Licence: {row.licence}.\n{row.note}"
    )


class SetupDialog(wx.Dialog):
    """First run, and Help > Set Up QUILL Transcribe... afterwards."""

    def __init__(
        self,
        parent: Any,
        *,
        microphone: str,
        engine: str,
        key: str,
        at_login: bool,
        test_microphone: Callable[[str, str, Callable[[str], None]], None],
    ) -> None:
        super().__init__(
            parent,
            title="Set Up QUILL Transcribe",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        from quill.core.transcribe.models import model_rows

        self._test = test_microphone
        root = wx.BoxSizer(wx.VERTICAL)
        about = wx.StaticText(self, label="&About QUILL Transcribe:")
        self.intro = wx.TextCtrl(self, value=INTRO, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.intro.SetHelpText(
            "What QUILL Transcribe does and does not do, to read with the arrow keys. "
            "Tab moves on to the choices."
        )
        root.Add(about, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.intro, 1, wx.EXPAND | wx.ALL, _PAD)

        names, default_label = _microphones()
        self._microphone_names = ["", *names]
        if microphone and microphone not in self._microphone_names:
            self._microphone_names.append(microphone)
            names = [*names, f"{microphone} (not connected)"]
        mic_label = wx.StaticText(self, label="&Microphone:")
        self.microphone = wx.Choice(self, choices=[default_label, *names])
        self.microphone.SetHelpText(
            "The microphone QUILL Transcribe listens on. The Windows default follows "
            "whatever Windows is set to; a named one stays chosen."
        )
        self.microphone.SetSelection(self._microphone_names.index(microphone))
        self.test_button = wx.Button(self, label="&Test Microphone")
        self.test_button.SetHelpText(
            "Records four seconds on the chosen microphone and says how loud it was "
            "and what it heard. The recording stays on this computer and is not kept."
        )
        result_label = wx.StaticText(self, label="Test &result:")
        self.test_result = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.test_result.SetHelpText("What the last microphone test found.")
        self.test_button.Bind(wx.EVT_BUTTON, self._on_test)
        root.Add(mic_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.microphone, 0, wx.EXPAND | wx.ALL, _PAD)
        test_row = wx.BoxSizer(wx.HORIZONTAL)
        test_row.Add(self.test_button, 0, wx.RIGHT, _PAD)
        test_row.Add(result_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, _PAD)
        test_row.Add(self.test_result, 1, wx.EXPAND)
        root.Add(test_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, _PAD)

        self._rows = [row for row in model_rows() if row.ready]
        model_label = wx.StaticText(self, label="Speech mo&del:")
        self.model = wx.Choice(self, choices=[row.label for row in self._rows])
        self.model.SetHelpText(
            "The model that turns your speech into text. Only models already on this "
            "computer are listed here; more can be downloaded later from the Model "
            "Library. The one you choose is used every time until you change it."
        )
        ids = [row.id for row in self._rows]
        self.model.SetSelection(ids.index(engine) if engine in ids else 0)
        root.Add(model_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.model, 0, wx.EXPAND | wx.ALL, _PAD)

        key_label = wx.StaticText(self, label="Start and stop &key (leave empty for none):")
        self.key = wx.TextCtrl(self, value=key)
        self.key.SetHelpText(
            "Type the key that starts and stops dictation from any program, for "
            "example Ctrl+Alt+PageDown. Leave it empty to use the tray menu instead. "
            "Nothing is registered with Windows until you choose a key here."
        )
        root.Add(key_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.key, 0, wx.EXPAND | wx.ALL, _PAD)

        self.at_login = wx.CheckBox(self, label="Start QUILL Transcribe when I sign in to &Windows")
        self.at_login.SetHelpText(
            "Opens QUILL Transcribe in the tray when you sign in, so your key works "
            "straight away. It does not start listening until you start dictation."
        )
        self.at_login.SetValue(at_login)
        root.Add(self.at_login, 0, wx.ALL, _PAD)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        finish = wx.Button(self, wx.ID_OK, "Finish")
        finish.SetHelpText("Keep these choices and close setup.")
        skip = wx.Button(self, wx.ID_CANCEL, "Skip")
        skip.SetHelpText(
            "Close setup without changing anything. Setup is on the Help menu whenever you want it."
        )
        buttons.Add(finish, 0, wx.RIGHT, _PAD)
        buttons.Add(skip, 0)
        root.Add(buttons, 0, wx.ALL, _PAD)
        self.SetSizer(root)
        self.SetSize((620, 640))
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        bind_close_button(self, skip, modeless=False)
        self.intro.SetFocus()

    def _on_test(self, _event: Any) -> None:
        self.test_button.Disable()
        self.test_result.SetValue("Recording...")
        self._test(self.chosen_microphone(), self.chosen_engine(), self._show_test)

    def _show_test(self, sentence: str) -> None:
        if not self:
            return
        self.test_button.Enable()
        self.test_result.SetValue(sentence)

    def chosen_microphone(self) -> str:
        row = self.microphone.GetSelection()
        return self._microphone_names[row] if 0 <= row < len(self._microphone_names) else ""

    def chosen_engine(self) -> str:
        row = self.model.GetSelection()
        return self._rows[row].id if 0 <= row < len(self._rows) else ""

    def chosen_key(self) -> str:
        return str(self.key.GetValue()).strip()


class ChooseModelDialog(wx.Dialog):
    """Every model, marked local or internet, ready or not; one is chosen."""

    def __init__(self, parent: Any, *, current: str, open_library: Callable[[], None]) -> None:
        super().__init__(
            parent, title="Choose Model", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.chosen = ""
        self._open_library = open_library
        root = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self, label="&Models:")
        self.list = wx.ListBox(self)
        self.list.SetHelpText(
            "Every speech model QUILL knows. Each says whether it runs on this "
            "computer or sends your speech over the internet, which languages it "
            "knows, and whether it is downloaded. Enter uses the one you are on."
        )
        details_label = wx.StaticText(self, label="&About this model:")
        self.details = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.details.SetHelpText(
            "The model you are on: where it runs, its languages and size, who "
            "publishes it and under which licence."
        )
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        use = wx.Button(self, wx.ID_OK, "Use This Model")
        use.SetHelpText(
            "Make this your model. It is used every time you dictate until you choose "
            "another; QUILL Transcribe never switches on its own."
        )
        library = wx.Button(self, label="Model &Library...")
        library.SetHelpText(
            "Download, check or remove the optional models. Downloads are your choice, "
            "show their size first, and are checked before they are used."
        )
        cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Keep the model you have.")
        for button in (use, library, cancel):
            buttons.Add(button, 0, wx.RIGHT, _PAD)
        root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.list, 1, wx.EXPAND | wx.ALL, _PAD)
        root.Add(details_label, 0, wx.LEFT | wx.RIGHT, _PAD)
        root.Add(self.details, 1, wx.EXPAND | wx.ALL, _PAD)
        root.Add(buttons, 0, wx.ALL, _PAD)
        self.SetSizer(root)
        self.SetSize((640, 560))
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        bind_close_button(self, cancel, modeless=False)
        self.Bind(wx.EVT_BUTTON, self._on_use, id=wx.ID_OK)
        library.Bind(wx.EVT_BUTTON, self._on_library)
        self.list.Bind(wx.EVT_LISTBOX, lambda _e: self._describe())
        apply_listbox_activation(self.list, self._on_use)
        self._fill(current)
        self.list.SetFocus()

    def _fill(self, current: str) -> None:
        from quill.core.transcribe.models import model_rows

        self._rows = model_rows()
        self.list.Set([row.label for row in self._rows])
        ids = [row.id for row in self._rows]
        self.list.SetSelection(ids.index(current) if current in ids else 0)
        self._describe()

    def _row(self) -> Any:
        index = self.list.GetSelection()
        return self._rows[index] if 0 <= index < len(self._rows) else None

    def _describe(self) -> None:
        row = self._row()
        self.details.SetValue(_details(row) if row is not None else "")

    def _on_library(self, _event: Any) -> None:
        row = self._row()
        self._open_library()
        self._fill(row.id if row is not None else "")

    def _on_use(self, _event: Any) -> None:
        row = self._row()
        if row is None:
            return
        if not row.ready:
            show_message_box(
                f"{row.name} is not downloaded yet. Choose Model Library to download "
                "it first, or choose a model that is ready.",
                "Choose Model",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return
        self.chosen = row.id
        self.EndModal(wx.ID_OK)


def choose_microphone(host: Any, current: str) -> str | None:
    """The microphone list as a stock single-choice window; ``None`` if cancelled."""
    names, default_label = _microphones()
    values = ["", *names]
    labels = [default_label, *names]
    if current and current not in values:
        values.append(current)
        labels.append(f"{current} (not connected)")
    dialog = wx.SingleChoiceDialog(
        host.frame,
        "The microphone QUILL Transcribe listens on:",
        "Choose Microphone",
        labels,
    )
    try:
        dialog.SetSelection(values.index(current) if current in values else 0)
        if host._show_modal_dialog(dialog, "Choose Microphone") != wx.ID_OK:
            return None
        return values[dialog.GetSelection()]
    finally:
        dialog.Destroy()
