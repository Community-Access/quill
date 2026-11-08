"""The four windows behind saved replace jobs, shared by both editors.

Split from :mod:`quill.ui.replace_jobs` under GATE-11; that module keeps the two
commands and imports these by name, which is where a test replaces them.
Every window is labelled and keyboard-complete (GATE-14: OK, Cancel and Close
carry no access key, and no two controls in one window share one):

* **Run Replace Job**: a list of the saved jobs; Enter runs the one you are on.
* **Manage Replace Jobs**: the list, with New, Edit, Rename and Delete.
* **Edit Replace Job**: a name and the list of steps, with Add, Edit, Remove,
  Move Up and Move Down.
* **Replace Step**: Find what, Replace with, Regular expression, Match case.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.replace_jobs import (
    ReplaceJob,
    ReplaceStep,
    describe_step,
    step_error,
    unique_job_name,
)

__all__ = [
    "choose_replace_job",
    "edit_replace_job",
    "edit_replace_step",
    "manage_replace_jobs",
]

_PAD = 8
ShowModal = Callable[[Any, str], int]


# --------------------------------------------------------------------------- #
# Small shared pieces
# --------------------------------------------------------------------------- #


def _button_row(root: Any, *buttons: Any) -> None:
    import wx

    row = wx.BoxSizer(wx.HORIZONTAL)
    row.AddStretchSpacer()
    for index, button in enumerate(buttons):
        row.Add(button, 0, wx.RIGHT if index < len(buttons) - 1 else 0, _PAD)
    root.Add(row, 0, wx.EXPAND | wx.ALL, _PAD)


def _button(dialog: Any, sizer: Any, label: str, help_text: str, handler: Any) -> Any:
    import wx

    button = wx.Button(dialog, label=label)
    button.SetHelpText(help_text)
    button.Bind(wx.EVT_BUTTON, lambda _event: handler())
    sizer.Add(button, 0, wx.EXPAND | wx.BOTTOM, 4)
    return button


def _tell(parent: Any, message: str, title: str, show_modal: ShowModal) -> None:
    """A problem, in a message box the reader announces, through the host's route."""
    import wx

    box = wx.MessageDialog(parent, message, title, wx.OK | wx.ICON_WARNING)
    try:
        show_modal(box, title)
    finally:
        box.Destroy()


def _confirm(parent: Any, message: str, title: str, show_modal: ShowModal) -> bool:
    import wx

    box = wx.MessageDialog(parent, message, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
    try:
        return bool(show_modal(box, title) == wx.ID_YES)
    finally:
        box.Destroy()


def _ask_name(parent: Any, title: str, value: str, show_modal: ShowModal) -> str | None:
    import wx

    box = wx.TextEntryDialog(parent, "Job name:", title, value=value)
    try:
        if show_modal(box, title) != wx.ID_OK:
            return None
        return str(box.GetValue()).strip()
    finally:
        box.Destroy()


def _job_row(job: ReplaceJob) -> str:
    count = len(job.steps)
    return f"{job.name}, {count} {'step' if count == 1 else 'steps'}"


# --------------------------------------------------------------------------- #
# The four windows
# --------------------------------------------------------------------------- #


def choose_replace_job(
    parent: Any, jobs: list[ReplaceJob], show_modal: ShowModal, *, in_selection: bool
) -> int | None:
    """Which job to run. Returns its index, or ``None`` for Cancel."""
    import wx

    from quill.ui.accessible_names import set_accessible_name
    from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids
    from quill.ui.dpi import dip_size

    title = "Run Replace Job"
    where = "the selection" if in_selection else "the whole document"
    dialog = wx.Dialog(
        parent, title="Run Replace Job", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
    )
    try:
        root = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(dialog, label=f"&Job to run on {where}:")
        listbox = wx.ListBox(dialog, choices=[_job_row(job) for job in jobs])
        set_accessible_name(listbox, "Job to run")
        listbox.SetHelpText(
            "Your saved replace jobs. Enter runs the one you are on, every step in "
            "order, as one change that Control Z takes back. Manage Replace Jobs "
            "adds, edits and deletes them."
        )
        listbox.SetSelection(0)
        root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(listbox, 1, wx.EXPAND | wx.ALL, _PAD)
        ok = wx.Button(dialog, wx.ID_OK, "OK")
        ok.SetHelpText("Run the job you are on.")
        ok.SetDefault()
        cancel = wx.Button(dialog, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Close this window and change nothing.")
        _button_row(root, ok, cancel)
        dialog.SetSizerAndFit(root)
        dialog.SetSize(dip_size(dialog, 480, 360))
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        apply_listbox_activation(listbox, lambda _event: dialog.EndModal(wx.ID_OK))
        listbox.SetFocus()
        if show_modal(dialog, title) != wx.ID_OK:
            return None
        index = int(listbox.GetSelection())
        return index if 0 <= index < len(jobs) else None
    finally:
        dialog.Destroy()


def edit_replace_step(
    parent: Any, step: ReplaceStep | None, show_modal: ShowModal
) -> ReplaceStep | None:
    """One step's four fields. Returns the step, or ``None`` for Cancel."""
    import wx

    from quill.ui.dialog_contract import apply_modal_ids
    from quill.ui.dpi import dip_size

    title = "Replace Step"
    current = step or ReplaceStep("")
    dialog = wx.Dialog(
        parent, title="Replace Step", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
    )
    try:
        root = wx.BoxSizer(wx.VERTICAL)
        find_label = wx.StaticText(dialog, label="&Find what:")
        find = wx.TextCtrl(dialog, value=current.find)
        find.SetHelpText(
            "The text this step looks for. With Regular expression checked, a "
            "pattern: \\s for any space, ^ and $ for the start and end of a line."
        )
        replace_label = wx.StaticText(dialog, label="Re&place with:")
        replace = wx.TextCtrl(dialog, value=current.replace)
        replace.SetHelpText(
            "What each match becomes. Leave it empty to delete the matches. Typed "
            "exactly, unless Regular expression is checked, when \\1 puts back the "
            "first group."
        )
        regex = wx.CheckBox(dialog, label="&Regular expression")
        regex.SetValue(current.regex)
        regex.SetHelpText("Read Find what as a regular expression rather than as plain text.")
        match_case = wx.CheckBox(dialog, label="Match &case")
        match_case.SetValue(current.match_case)
        match_case.SetHelpText("Find only matches with the same capital letters.")
        for control in (find_label, find, replace_label, replace):
            root.Add(control, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(regex, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(match_case, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        ok = wx.Button(dialog, wx.ID_OK, "OK")
        ok.SetHelpText("Keep this step.")
        ok.SetDefault()
        cancel = wx.Button(dialog, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Close this window and change nothing.")
        _button_row(root, ok, cancel)

        def built() -> ReplaceStep:
            return ReplaceStep(
                str(find.GetValue()),
                str(replace.GetValue()),
                bool(regex.GetValue()),
                bool(match_case.GetValue()),
            )

        def on_ok(_event: Any) -> None:
            problem = step_error(built())
            if problem:
                _tell(dialog, problem, title, show_modal)
                find.SetFocus()
                return
            dialog.EndModal(wx.ID_OK)

        ok.Bind(wx.EVT_BUTTON, on_ok)
        dialog.SetSizerAndFit(root)
        dialog.SetSize(dip_size(dialog, 480, 300))
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        find.SetFocus()
        if show_modal(dialog, title) != wx.ID_OK:
            return None
        return built()
    finally:
        dialog.Destroy()


class _JobEditor:
    """Edit Replace Job: a name and its steps. Methods are the buttons, for the tests."""

    TITLE = "Edit Replace Job"

    def __init__(
        self,
        parent: Any,
        job: ReplaceJob,
        others: list[ReplaceJob],
        index: int,
        show_modal: ShowModal,
    ) -> None:
        import wx

        from quill.ui.accessible_names import set_accessible_name
        from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids
        from quill.ui.dpi import dip_size

        self._show_modal = show_modal
        self._others = others
        self._index = index
        self.steps = [ReplaceStep(**s.to_dict()) for s in job.steps]  # type: ignore[arg-type]
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        self.dialog = dialog = wx.Dialog(parent, title="Edit Replace Job", style=style)
        root = wx.BoxSizer(wx.VERTICAL)
        name_label = wx.StaticText(dialog, label="&Name:")
        self.name = wx.TextCtrl(dialog, value=job.name)
        self.name.SetHelpText("What this job is called in the list you run it from.")
        root.Add(name_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.name, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, _PAD)
        steps_label = wx.StaticText(dialog, label="&Steps, run in this order:")
        self.list = wx.ListBox(dialog)
        set_accessible_name(self.list, "Steps, run in this order")
        self.list.SetHelpText(
            "Each step runs on the result of the one before. Enter edits the step you are on."
        )
        apply_listbox_activation(self.list, lambda _event: self.edit_step())
        root.Add(steps_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        middle = wx.BoxSizer(wx.HORIZONTAL)
        middle.Add(self.list, 1, wx.EXPAND | wx.RIGHT, _PAD)
        side = wx.BoxSizer(wx.VERTICAL)
        _button(dialog, side, "&Add Step...", "Add a step after the one you are on.", self.add_step)
        _button(dialog, side, "&Edit Step...", "Change the step you are on.", self.edit_step)
        _button(dialog, side, "&Remove Step", "Take the step you are on out.", self.remove_step)
        _button(
            dialog,
            side,
            "Move &Up",
            "Run the step you are on one place earlier.",
            lambda: self.move(-1),
        )
        _button(
            dialog,
            side,
            "Move Do&wn",
            "Run the step you are on one place later.",
            lambda: self.move(1),
        )
        middle.Add(side, 0)
        root.Add(middle, 1, wx.EXPAND | wx.ALL, _PAD)
        ok = wx.Button(dialog, wx.ID_OK, "OK")
        ok.SetHelpText("Keep this job as it is now.")
        ok.SetDefault()
        cancel = wx.Button(dialog, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Close this window and change nothing.")
        _button_row(root, ok, cancel)
        ok.Bind(wx.EVT_BUTTON, lambda _event: self.on_ok())
        dialog.SetSizerAndFit(root)
        dialog.SetSize(dip_size(dialog, 600, 420))
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self._refresh(0)
        self.name.SetFocus()

    def _refresh(self, select: int) -> None:
        self.list.Set([f"{n}. {describe_step(s)}" for n, s in enumerate(self.steps, start=1)])
        if self.steps:
            self.list.SetSelection(max(0, min(select, len(self.steps) - 1)))

    def _current(self) -> int:
        index = int(self.list.GetSelection())
        return index if 0 <= index < len(self.steps) else -1

    def add_step(self) -> None:
        step = edit_replace_step(self.dialog, None, self._show_modal)
        if step is None:
            return
        at = self._current() + 1 if self.steps else 0
        self.steps.insert(at, step)
        self._refresh(at)
        self.list.SetFocus()

    def edit_step(self) -> None:
        index = self._current()
        if index < 0:
            return
        step = edit_replace_step(self.dialog, self.steps[index], self._show_modal)
        if step is not None:
            self.steps[index] = step
            self._refresh(index)
        self.list.SetFocus()

    def remove_step(self) -> None:
        index = self._current()
        if index < 0:
            return
        del self.steps[index]
        self._refresh(index)
        self.list.SetFocus()

    def move(self, by: int) -> None:
        index = self._current()
        target = index + by
        if index < 0 or not 0 <= target < len(self.steps):
            return
        self.steps[index], self.steps[target] = self.steps[target], self.steps[index]
        self._refresh(target)
        self.list.SetFocus()

    def problem(self) -> str:
        name = str(self.name.GetValue()).strip()
        if not name:
            return "Give the job a name."
        if not unique_job_name(name, self._others, ignore=self._index):
            return f"There is already a job called {name}. Choose another name."
        if not self.steps:
            return "Add at least one step. Add Step does that."
        return ""

    def on_ok(self) -> None:
        import wx

        problem = self.problem()
        if problem:
            _tell(self.dialog, problem, self.TITLE, self._show_modal)
            (self.name if "name" in problem else self.list).SetFocus()
            return
        self.dialog.EndModal(wx.ID_OK)

    def show(self) -> int:
        """Through the host's modal route, which announces and brailles."""
        return int(self._show_modal(self.dialog, self.TITLE))

    def result(self) -> ReplaceJob:
        return ReplaceJob(str(self.name.GetValue()).strip(), list(self.steps))


def edit_replace_job(
    parent: Any,
    job: ReplaceJob,
    jobs: list[ReplaceJob],
    index: int,
    show_modal: ShowModal,
) -> ReplaceJob | None:
    """Edit *job* (``jobs[index]``, or a new one at ``-1``). ``None`` is Cancel."""
    import wx

    editor = _JobEditor(parent, job, jobs, index, show_modal)
    try:
        if editor.show() != wx.ID_OK:
            return None
        return editor.result()
    finally:
        editor.dialog.Destroy()


class _JobManager:
    """Manage Replace Jobs. Works on a copy; Close hands the copy back."""

    TITLE = "Manage Replace Jobs"

    def __init__(self, parent: Any, jobs: list[ReplaceJob], show_modal: ShowModal) -> None:
        import wx

        from quill.ui.accessible_names import set_accessible_name
        from quill.ui.dialog_contract import (
            apply_listbox_activation,
            apply_modal_ids,
            bind_close_button,
        )
        from quill.ui.dpi import dip_size

        self._show_modal = show_modal
        self.jobs = list(jobs)
        self.changed = False
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        self.dialog = dialog = wx.Dialog(parent, title="Manage Replace Jobs", style=style)
        root = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(dialog, label="Saved &jobs:")
        self.list = wx.ListBox(dialog)
        set_accessible_name(self.list, "Saved jobs")
        self.list.SetHelpText(
            "Your saved replace jobs, each a list of find and replace steps run in "
            "order. Enter edits the one you are on."
        )
        apply_listbox_activation(self.list, lambda _event: self.edit())
        root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        middle = wx.BoxSizer(wx.HORIZONTAL)
        middle.Add(self.list, 1, wx.EXPAND | wx.RIGHT, _PAD)
        side = wx.BoxSizer(wx.VERTICAL)
        _button(dialog, side, "&New...", "Make a new job, starting with its first step.", self.new)
        _button(dialog, side, "&Edit...", "Change the steps of the job you are on.", self.edit)
        _button(dialog, side, "&Rename...", "Give the job you are on a new name.", self.rename)
        _button(dialog, side, "&Delete", "Delete the job you are on, after asking.", self.delete)
        middle.Add(side, 0)
        root.Add(middle, 1, wx.EXPAND | wx.ALL, _PAD)
        close = wx.Button(dialog, wx.ID_CANCEL, "Close")
        close.SetHelpText("Close this window. Every change is already kept.")
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer()
        row.Add(close, 0)
        root.Add(row, 0, wx.EXPAND | wx.ALL, _PAD)
        dialog.SetSizerAndFit(root)
        dialog.SetSize(dip_size(dialog, 560, 400))
        apply_modal_ids(dialog, cancel_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)
        bind_close_button(dialog, close, modeless=False)
        self._refresh(0)
        self.list.SetFocus()

    def show(self) -> int:
        """Through the host's modal route, which announces and brailles."""
        return int(self._show_modal(self.dialog, self.TITLE))

    def _refresh(self, select: int) -> None:
        self.list.Set([_job_row(job) for job in self.jobs])
        if self.jobs:
            self.list.SetSelection(max(0, min(select, len(self.jobs) - 1)))

    def _current(self) -> int:
        index = int(self.list.GetSelection())
        return index if 0 <= index < len(self.jobs) else -1

    def new(self) -> None:
        job = edit_replace_job(self.dialog, ReplaceJob("New job"), self.jobs, -1, self._show_modal)
        if job is not None:
            self.jobs.append(job)
            self.changed = True
            self._refresh(len(self.jobs) - 1)
        self.list.SetFocus()

    def edit(self) -> None:
        index = self._current()
        if index < 0:
            return
        job = edit_replace_job(self.dialog, self.jobs[index], self.jobs, index, self._show_modal)
        if job is not None:
            self.jobs[index] = job
            self.changed = True
            self._refresh(index)
        self.list.SetFocus()

    def rename(self) -> None:
        index = self._current()
        if index < 0:
            return
        name = _ask_name(self.dialog, "Rename Replace Job", self.jobs[index].name, self._show_modal)
        if name is None:
            self.list.SetFocus()
            return
        if not unique_job_name(name, self.jobs, ignore=index):
            problem = (
                "A job needs a name." if not name else f"There is already a job called {name}."
            )
            _tell(self.dialog, problem, "Rename Replace Job", self._show_modal)
        else:
            self.jobs[index] = ReplaceJob(name, self.jobs[index].steps)
            self.changed = True
            self._refresh(index)
        self.list.SetFocus()

    def delete(self) -> None:
        index = self._current()
        if index < 0:
            return
        name = self.jobs[index].name
        if _confirm(self.dialog, f"Delete the job {name}?", "Delete Replace Job", self._show_modal):
            del self.jobs[index]
            self.changed = True
            self._refresh(index)
        self.list.SetFocus()


def manage_replace_jobs(
    parent: Any, jobs: list[ReplaceJob], show_modal: ShowModal
) -> list[ReplaceJob] | None:
    """The manager. Returns the new list when anything changed, else ``None``."""
    manager = _JobManager(parent, jobs, show_modal)
    try:
        manager.show()
        return manager.jobs if manager.changed else None
    finally:
        manager.dialog.Destroy()
