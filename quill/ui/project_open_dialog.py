"""Opening a project, and the two per-project questions (code.md 2.1, 4.7, decision 4).

- **Open Project Folder.** A project is just a folder. The window lists the
  recent projects first, newest at the top, so the usual case is Down Arrow
  and Enter; **Browse for a Folder** opens the system folder picker.
- **Use this project's agent notes?** Asked once per project, the first time a
  task runs there, when the project carries ``AGENTS.md`` or another agent
  instruction file. **Read Them First** shows their text here, read-only,
  before you decide. The answer is kept in QUILL, never in the project.
- **Engine Tools for This Project** (decision 4): the engine's own tools, each
  a check box, all off until checked, remembered for this project only.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import wx

from quill.core.ai import project_task_words as words
from quill.ui.accessible_names import set_accessible_name
from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    bind_close_button,
    show_modal_dialog,
)
from quill.ui.dpi import dip_size
from quill.ui.spoken_name import set_spoken_name

__all__ = [
    "EngineToolsDialog",
    "InstructionFilesDialog",
    "OpenProjectDialog",
    "ask_instruction_files",
    "choose_project_folder",
    "edit_engine_tools",
]

_PAD = 8


def _text(parent: wx.Window, value: str, name: str, help_text: str, lines: int = 3) -> Any:
    field = wx.TextCtrl(parent, value=value, style=wx.TE_MULTILINE | wx.TE_READONLY)
    set_spoken_name(field, name)  # no label before it, so the name must be spoken
    field.SetHelpText(help_text)
    field.SetMinSize((-1, field.GetCharHeight() * lines + _PAD))
    return field


class OpenProjectDialog(wx.Dialog):
    """Recent projects, newest first, and a way to pick another folder."""

    def __init__(self, parent: Any, recent: list[Path]) -> None:
        super().__init__(parent, title="Open Project Folder")  # words.OPEN_PROJECT_TITLE
        self._recent = list(recent)
        self.chosen: Path | None = None
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        sizer.Add(
            wx.StaticText(self, label="&Recent projects"), 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD
        )
        rows = [f"{p.name}, {p}" for p in self._recent] or ["No recent projects yet."]
        self.list = wx.ListBox(self, choices=rows)
        set_accessible_name(self.list, "Recent projects")
        self.list.SetHelpText(
            "Folders you have opened as projects, newest first. Enter opens the one "
            "selected. A project is just a folder; QUILL keeps its own notes about it "
            "in its own data folder, never in the project."
        )
        apply_listbox_activation(self.list, lambda _e: self._open_selected())
        if self._recent:
            self.list.SetSelection(0)
        else:
            self.list.Disable()
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, _PAD)
        row = wx.BoxSizer(wx.HORIZONTAL)
        browse = wx.Button(self, label="&Browse for a Folder...")
        browse.SetHelpText("Opens the Windows folder picker to choose any folder as a project.")
        browse.Bind(wx.EVT_BUTTON, lambda _e: self._browse())
        row.Add(browse, 0, wx.RIGHT, _PAD)
        row.AddStretchSpacer(1)
        self.open_button = wx.Button(self, wx.ID_OK, "Open")
        self.open_button.SetHelpText("Opens the selected recent project.")
        self.open_button.Bind(wx.EVT_BUTTON, lambda _e: self._open_selected())
        self.open_button.Enable(bool(self._recent))
        cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Closes this window without opening a project.")
        row.Add(self.open_button, 0, wx.RIGHT, _PAD)
        row.Add(cancel, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, _PAD)
        if self._recent:
            self.open_button.SetDefault()
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label="Open",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Cancel",
        )
        self.SetInitialSize(dip_size(self, 560, 380))
        self.Centre()
        (self.list if self._recent else browse).SetFocus()

    def _open_selected(self) -> None:
        index = self.list.GetSelection()
        if 0 <= index < len(self._recent):
            self.chosen = self._recent[index]
            self.EndModal(wx.ID_OK)

    def _browse(self) -> None:
        with wx.DirDialog(self, "Choose a project folder", style=wx.DD_DIR_MUST_EXIST) as picker:
            if picker.ShowModal() == wx.ID_OK:
                self.chosen = Path(picker.GetPath())
                self.EndModal(wx.ID_OK)


def choose_project_folder(parent: Any, recent: list[Path]) -> Path | None:
    dialog = OpenProjectDialog(parent, recent)
    try:
        result = show_modal_dialog(dialog, words.OPEN_PROJECT_TITLE)
        return dialog.chosen if result == wx.ID_OK else None
    finally:
        dialog.Destroy()


class InstructionFilesDialog(wx.Dialog):
    """Use This Project's Agent Notes? Yes, No, or read them first."""

    def __init__(self, parent: Any, files: list[str], read: Callable[[], str]) -> None:
        super().__init__(
            parent,
            title="Use This Project's Agent Notes?",  # words.INSTRUCTIONS_QUESTION_TITLE
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._read = read
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        self.question = _text(
            self,
            words.instructions_question(files),
            "Question",
            "Which files in this project hold notes for AI agents, and what using them "
            "means. You are asked once per project; QUILL remembers the answer.",
        )
        sizer.Add(self.question, 0, wx.EXPAND | wx.ALL, _PAD)
        sizer.Add(wx.StaticText(self, label="&Notes"), 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        self.notes = _text(
            self,
            "",
            "Notes",
            "The notes' text, after Read Them First. Read it with the arrow keys.",
            lines=8,
        )
        sizer.Add(self.notes, 1, wx.EXPAND | wx.ALL, _PAD)
        row = wx.BoxSizer(wx.HORIZONTAL)
        read_button = wx.Button(self, label="&Read Them First")
        read_button.SetHelpText("Shows the notes' text in this window, so you can decide.")
        read_button.Bind(wx.EVT_BUTTON, lambda _e: self._show_notes())
        row.Add(read_button, 0, wx.RIGHT, _PAD)
        row.AddStretchSpacer(1)
        use = wx.Button(self, wx.ID_YES, "&Use Them")
        use.SetHelpText("Sends the notes with every task in this project, marked as data.")
        use.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_YES))
        skip = wx.Button(self, wx.ID_NO, "&Don't Use Them")
        skip.SetHelpText("Leaves the notes out of tasks in this project.")
        skip.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_NO))
        row.Add(use, 0, wx.RIGHT, _PAD)
        row.Add(skip, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, _PAD)
        # Use Them is the affirmative answer; Escape is Don't Use Them.
        apply_modal_ids(self, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO)
        use.SetDefault()
        self.SetInitialSize(dip_size(self, 620, 420))
        self.Centre()
        self.question.SetFocus()

    def _show_notes(self) -> None:
        self.notes.SetValue(self._read() or "The notes could not be read.")
        self.notes.SetInsertionPoint(0)
        self.notes.SetFocus()


def ask_instruction_files(parent: Any, files: list[str], read: Callable[[], str]) -> bool | None:
    """True to use the notes, False not to; None if the window was closed unanswered."""
    dialog = InstructionFilesDialog(parent, files, read)
    try:
        result = show_modal_dialog(dialog, words.INSTRUCTIONS_QUESTION_TITLE)
    finally:
        dialog.Destroy()
    if result == wx.ID_YES:
        return True
    if result == wx.ID_NO:
        return False
    return None


class EngineToolsDialog(wx.Dialog):
    """One check box per engine tool, off until checked (decision 4)."""

    def __init__(self, parent: Any, engine_name: str, tools: list[Any], on: frozenset[str]) -> None:
        super().__init__(parent, title="Engine Tools for This Project")  # words.ENGINE_TOOLS_TITLE
        from quill.core.ai.vendor_tools import VENDOR_TOOLS_WARNING

        self._tools = tools
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        about = _text(
            self,
            VENDOR_TOOLS_WARNING,
            "About these tools",
            "What turning on an engine's own tools means. QUILL's own project tools "
            "are always used; these are extra, and off unless you check them.",
            lines=5,
        )
        sizer.Add(about, 0, wx.EXPAND | wx.ALL, _PAD)
        sizer.Add(
            wx.StaticText(self, label=f"{engine_name}'s own tools"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            _PAD,
        )
        # One real check box per tool, not a check-list box (A11Y-SR-1), so the
        # reader says each one's state as Tab lands on it.
        pane = wx.ScrolledWindow(self, style=wx.VSCROLL)
        pane.SetScrollRate(0, 10)
        boxes = wx.BoxSizer(wx.VERTICAL)
        pane.SetSizer(boxes)
        self.boxes: list[wx.CheckBox] = []
        for tool in tools:
            box = wx.CheckBox(pane, label=tool.label)
            box.SetValue(tool.id in on)
            box.SetHelpText(
                f"{tool.description} Checked: the engine may use it in this project, "
                "and each use asks you first."
            )
            boxes.Add(box, 0, wx.ALL, _PAD // 2)
            self.boxes.append(box)
        sizer.Add(pane, 1, wx.EXPAND | wx.ALL, _PAD)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer(1)
        ok = wx.Button(self, wx.ID_OK, "OK")
        ok.SetHelpText("Keeps the tools checked here for this project.")
        cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Closes without changing anything.")
        bind_close_button(self, cancel, modeless=False)
        row.Add(ok, 0, wx.RIGHT, _PAD)
        row.Add(cancel, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, _PAD)
        apply_modal_ids(
            self, affirmative_id=wx.ID_OK, affirmative_label="OK", cancel_id=wx.ID_CANCEL
        )
        self.SetInitialSize(dip_size(self, 620, 440))
        self.Centre()
        (self.boxes[0] if self.boxes else ok).SetFocus()

    def checked(self) -> frozenset[str]:
        return frozenset(
            t.id for t, box in zip(self._tools, self.boxes, strict=True) if box.GetValue()
        )


def edit_engine_tools(
    parent: Any, engine: str, engine_name: str, choices: Any, announce: Callable[[str], None]
) -> None:
    """Show the opt-in list for *engine* and store the answer in *choices*."""
    from quill.core.ai.vendor_tools import VENDOR_TOOLS

    tools = list(VENDOR_TOOLS.get(engine, ()))
    if not tools:
        announce(words.ENGINE_TOOLS_NONE)
        return
    dialog = EngineToolsDialog(parent, engine_name, tools, choices.enabled(engine))
    try:
        if show_modal_dialog(dialog, words.ENGINE_TOOLS_TITLE) == wx.ID_OK:
            choices.set_enabled(engine, dialog.checked())
    finally:
        dialog.Destroy()
