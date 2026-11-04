"""Running a command for an agent: the approval, and the project's allow list (code.md 4.6).

**Run This Command?** One sentence on what will run, where, and the agent's
reason; then the exact command in a read-only field the person can arrow
through and braille character by character; then, only when QUILL found one,
the warning lines ("This may reach the internet."). Allow once is the default
(Enter), Don't allow is Escape, and **Always allow this command here** is
offered only for a command with no warning line, because a command QUILL warns
about is one somebody should look at every time.

**Commands Allowed in This Project** is the person's own list, kept in QUILL's
app data and never in the repository: a cloned project cannot pre-approve its
own commands. It also holds the deliberate bypass, **Run commands without
asking** (decision 7), off by default and confirmed when turned on.

Nothing here decides what is safe: :func:`quill.core.ai.command_runner.assess_command`
does, and these windows only show its answer.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.ai import project_task_words as words
from quill.core.ai.command_runner import AllowList, CommandAssessment
from quill.ui.accessible_names import set_accessible_name
from quill.ui.dialog_contract import (
    apply_modal_ids,
    bind_close_button,
    show_message_box,
    show_modal_dialog,
)
from quill.ui.dpi import dip_size

__all__ = [
    "AllowedCommandsDialog",
    "CommandApprovalDialog",
    "ask_command",
    "ask_keep_waiting",
    "edit_allowed_commands",
]

_PAD = 8
_ALWAYS = wx.ID_YES


def _field(parent: wx.Window, sizer: wx.Sizer, label: str, value: str, help_text: str) -> Any:
    sizer.Add(wx.StaticText(parent, label=label), 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
    field = wx.TextCtrl(parent, value=value, style=wx.TE_READONLY)
    set_accessible_name(field, label.replace("&", ""))
    field.SetHelpText(help_text)
    sizer.Add(field, 0, wx.EXPAND | wx.ALL, _PAD)
    return field


class CommandApprovalDialog(wx.Dialog):
    """What will run, the exact text, any warning, and three answers."""

    def __init__(self, parent: Any, assessment: CommandAssessment, question: str) -> None:
        super().__init__(parent, title="Run This Command?")  # words.COMMAND_APPROVAL_TITLE
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        self.question = _field(
            self,
            sizer,
            "What will run",
            question,
            "What the agent wants to run, where, and why, in one sentence. Enter "
            "allows it once; Escape does not allow it.",
        )
        self.command = _field(
            self,
            sizer,
            "&Command",
            assessment.command,
            "The exact command, as it will run in your project folder. Arrow "
            "through it to check every character. A warning below appears only when "
            "QUILL finds one: the command may reach the internet, delete files, or "
            "work outside the project. QUILL cannot stop an allowed command from "
            "doing anything your own account can do, so the approval is the safety "
            "check.",
        )
        self.warnings: Any = None
        if assessment.warnings:
            self.warnings = _field(
                self,
                sizer,
                "&Warning",
                " ".join(assessment.warnings),
                "What QUILL found in this command that you should know before "
                "allowing it. Commands with a warning can only be allowed once.",
            )
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer(1)
        self.once = wx.Button(self, wx.ID_OK, "Allow &once")
        self.once.SetHelpText("Runs this command now. The next command asks again.")
        row.Add(self.once, 0, wx.LEFT, _PAD)
        self.always: Any = None
        if assessment.may_always_allow:
            self.always = wx.Button(self, _ALWAYS, "&Always allow this command here")
            self.always.SetHelpText(
                "Runs it now and adds it to this project's allowed commands, so it "
                "runs without asking next time. The list is yours, kept in QUILL, "
                "never in the project."
            )
            self.always.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(_ALWAYS))
            row.Add(self.always, 0, wx.LEFT, _PAD)
        self.deny = wx.Button(self, wx.ID_CANCEL, "&Don't allow")
        self.deny.SetHelpText("Does not run it. The agent is told, and carries on without it.")
        row.Add(self.deny, 0, wx.LEFT, _PAD)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, _PAD)
        self.once.SetDefault()
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label="Allow &once",
            cancel_id=wx.ID_CANCEL,
            cancel_label="&Don't allow",
        )
        self.SetInitialSize(dip_size(self, 620, 260 if self.warnings is None else 320))
        self.Centre()
        self.question.SetFocus()


def ask_command(parent: Any, assessment: CommandAssessment, question: str) -> str:
    """``"once"``, ``"always"`` or ``"deny"``."""
    dialog = CommandApprovalDialog(parent, assessment, question)
    try:
        result = show_modal_dialog(dialog, words.COMMAND_APPROVAL_TITLE)
    finally:
        dialog.Destroy()
    if result == wx.ID_OK:
        return "once"
    if result == _ALWAYS and assessment.may_always_allow:
        return "always"
    return "deny"


def ask_keep_waiting(parent: Any, seconds: float) -> bool:
    """The long-command notice: Yes keeps waiting, No stops the command."""
    answer = show_message_box(
        words.keep_waiting_question(seconds),
        "Keep Waiting?",
        wx.YES_NO | wx.ICON_QUESTION,
        parent,
    )
    return answer == wx.YES


class AllowedCommandsDialog(wx.Dialog):
    """The person's allow list for one project, and the bypass switch."""

    def __init__(self, parent: Any, allow: AllowList, project: str) -> None:
        super().__init__(
            parent,
            title="Commands Allowed in This Project",  # words.ALLOW_TITLE
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._allow = allow
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        about = wx.TextCtrl(
            self,
            value=(
                f"Commands in {project} that run without asking. A line allows that "
                "exact command, or any command that starts with it and a space: "
                "pytest allows pytest -q tests. Commands QUILL warns about are never "
                "allowed this way."
            ),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_NO_VSCROLL,
        )
        set_accessible_name(about, "About this list")
        about.SetHelpText("What this list does, and what it never does.")
        sizer.Add(about, 0, wx.EXPAND | wx.ALL, _PAD)
        sizer.Add(
            wx.StaticText(self, label="&Allowed commands"), 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD
        )
        self.entries = wx.ListBox(self, choices=allow.entries())
        set_accessible_name(self.entries, "Allowed commands")
        self.entries.SetHelpText(
            "The commands this project runs without asking. Delete removes the one selected."
        )
        self.entries.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        sizer.Add(self.entries, 1, wx.EXPAND | wx.ALL, _PAD)
        sizer.Add(wx.StaticText(self, label="&New command"), 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        self.new_entry = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        set_accessible_name(self.new_entry, "New command")
        self.new_entry.SetHelpText(
            "Type a command or the start of one, such as pytest, then press Enter or "
            "Add to allow it."
        )
        self.new_entry.Bind(wx.EVT_TEXT_ENTER, lambda _e: self.add())
        sizer.Add(self.new_entry, 0, wx.EXPAND | wx.ALL, _PAD)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        add = wx.Button(self, label="A&dd")
        add.SetHelpText("Adds what you typed to the list.")
        add.Bind(wx.EVT_BUTTON, lambda _e: self.add())
        remove = wx.Button(self, label="&Remove")
        remove.SetHelpText("Removes the selected command from the list.")
        remove.Bind(wx.EVT_BUTTON, lambda _e: self.remove())
        buttons.Add(add, 0, wx.RIGHT, _PAD)
        buttons.Add(remove, 0)
        sizer.Add(buttons, 0, wx.LEFT | wx.RIGHT, _PAD)
        self.bypass = wx.CheckBox(self, label="Run commands &without asking")
        self.bypass.SetValue(allow.bypass)
        self.bypass.SetHelpText(
            "When checked, the agent runs any command it chooses in this project "
            "without showing it to you first, except pushing, publishing and system "
            "changes. Off unless you check it, and QUILL asks you to confirm. The task "
            "window's status line says so while it is on."
        )
        self.bypass.Bind(wx.EVT_CHECKBOX, self._on_bypass)
        sizer.Add(self.bypass, 0, wx.ALL, _PAD)
        end = wx.BoxSizer(wx.HORIZONTAL)
        end.AddStretchSpacer(1)
        close = wx.Button(self, wx.ID_CANCEL, "Close")
        close.SetHelpText("Closes this window. Every change here is already saved.")
        bind_close_button(self, close, modeless=False)
        end.Add(close, 0)
        sizer.Add(end, 0, wx.EXPAND | wx.ALL, _PAD)
        self.SetEscapeId(wx.ID_CANCEL)
        self.SetInitialSize(dip_size(self, 560, 460))
        self.Centre()
        self.entries.SetFocus()

    def add(self) -> None:
        text = " ".join(self.new_entry.GetValue().split())
        if not text:
            return
        self._allow.add(text)
        self.new_entry.Clear()
        self._reload(select=text)

    def remove(self) -> None:
        index = self.entries.GetSelection()
        if index == wx.NOT_FOUND:
            return
        self._allow.remove(self.entries.GetString(index))
        self._reload()

    def _reload(self, select: str = "") -> None:
        entries = self._allow.entries()
        self.entries.Set(entries)
        if select in entries:
            self.entries.SetSelection(entries.index(select))

    def _on_list_key(self, event: Any) -> None:
        if event.GetKeyCode() == wx.WXK_DELETE:
            self.remove()
            return
        event.Skip()

    def _on_bypass(self, _event: Any) -> None:
        if self.bypass.GetValue():
            answer = show_message_box(
                words.BYPASS_CONFIRM,
                "Run Commands Without Asking?",
                wx.YES_NO | wx.NO_DEFAULT,
                self,
            )
            if answer != wx.YES:
                self.bypass.SetValue(False)
                return
        self._allow.set_bypass(self.bypass.GetValue())


def edit_allowed_commands(parent: Any, allow: AllowList, project: str) -> None:
    dialog = AllowedCommandsDialog(parent, allow, project)
    try:
        show_modal_dialog(dialog, words.ALLOW_TITLE)
    finally:
        dialog.Destroy()
