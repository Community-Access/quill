"""The workflow editor: a workflow file as linear controls (GitHub PRD 22.1).

One window, top to bottom: the workflow's name; its **triggers** as a list
(Add, Edit, Remove), each trigger's filters, schedule or inputs in a form of
its own; the workflow's **permissions**; the **jobs** as a list, each row
saying what it runs on and what it runs after, with Edit Job (id, name,
runner, which jobs it needs as check boxes, condition), Steps (a list of
steps, each a form: name, the action it uses or the commands it runs, its
inputs and variables), Permissions, Remove and Move; then **when the jobs
run**, the dependency graph in words ("First Test and Lint, together. Then
Build."); and **what GitHub would say**, the checks of
:mod:`quill.core.github.workflow_checks`, kept current after every change.

Save refuses while GitHub would reject the file, and otherwise hands the
YAML back (:attr:`result`); the Workbench asks, then commits it to the
default branch or, when that is protected or Save Through a Pull Request is
checked, to a new branch with a pull request. Nothing is sent from here.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.core.github.actions_yaml import COMMENTS_NOTE
from quill.core.github.workflow_authoring import (
    WorkflowDraft,
    dispatch_inputs,
    dump_workflow,
    input_summary,
    job,
    job_ids,
    job_name,
    job_summary,
    make_job_id,
    move_job,
    needs_of,
    order_sentence,
    permissions_summary,
    remove_job,
    remove_trigger,
    replace_job,
    set_trigger,
    step_summary,
    trigger_summary,
    triggers,
)
from quill.core.github.workflow_checks import check_workflow
from quill.ui.github_authoring_form import Field, ItemsDialog, RowList, ask_fields
from quill.ui.github_template_sheets_dialog import _Sheet
from quill.ui.github_workflow_parts import (
    EVENT_CHOICES,
    filters_fields,
    filters_from,
    input_fields,
    input_from,
    inputs_settings,
    permissions_fields,
    permissions_from,
    schedule_fields,
    schedule_from,
    step_fields,
    step_from,
)

__all__ = ["WorkflowEditorDialog"]


class WorkflowEditorDialog(_Sheet):
    title = "Workflow Editor"

    def __init__(
        self,
        parent: object,
        draft: WorkflowDraft,
        *,
        path: str,
        protected: bool = False,
        announce: Callable[[str], None] | None = None,
    ) -> None:
        self.draft = draft
        self.path = path
        self.protected = protected
        self.use_pull_request = protected
        super().__init__(parent, announce)
        self.dialog.SetTitle(f"Workflow Editor: {path}")

    # -- the window ---------------------------------------------------------------------

    def body(self) -> None:
        wx = self._wx
        name = self.draft.data.get("name")
        self.name = self.text_box(
            "Workflow &name:", str(name or ""), "The name GitHub shows in the Actions list."
        )
        self.pull = wx.CheckBox(self.dialog, label="Save through a &pull request")
        self.pull.SetValue(self.protected)
        self.pull.SetHelpText(
            "Commit to a new branch and open a pull request, so the change is reviewed first. "
            "Always on when the default branch is protected."
        )
        if self.protected:
            self.pull.Disable()
        self.root.Add(self.pull, 0, wx.ALL, 8)
        self.trigger_rows = RowList(
            self.dialog,
            self.root,
            "&Triggers:",
            "What starts the workflow, one row each. Enter edits the selected trigger.",
            (
                ("Add Tri&gger...", "Add an event that starts it.", self.add_trigger),
                ("Edit Trigge&r...", "Change the selected trigger's settings.", self.edit_trigger),
                ("Remo&ve Trigger", "Remove the selected trigger.", self.remove_trigger),
            ),
        )
        self.permissions = wx.Button(self.dialog, label="Workflow Per&missions...")
        self.permissions.SetHelpText(
            "What GITHUB_TOKEN may do in every job, unless a job sets its own."
        )
        self.permissions.Bind(wx.EVT_BUTTON, lambda _e: self.edit_permissions(None))
        self.root.Add(self.permissions, 0, wx.ALL, 8)
        self.job_rows = RowList(
            self.dialog,
            self.root,
            "&Jobs:",
            "Each job, what it runs on and what it runs after. Enter edits the selected job.",
            (
                ("Add Jo&b...", "Add a job.", self.add_job),
                ("Ed&it Job...", "Change the selected job's id, runner and needs.", self.edit_job),
                ("Job &Steps...", "The selected job's steps, in order.", self.edit_steps),
                (
                    "Job Permissions...",
                    "What GITHUB_TOKEN may do in the selected job.",
                    lambda: self.edit_permissions(self._selected_job()),
                ),
                ("Remove J&ob", "Remove the selected job.", self.remove_job),
                (
                    "Move Job &Up",
                    "Move the selected job earlier in the file.",
                    lambda: self.move(-1),
                ),
                (
                    "Move Job Do&wn",
                    "Move the selected job later in the file.",
                    lambda: self.move(1),
                ),
            ),
        )
        self.order = self._readout(
            "Wh&en jobs run:", "The jobs in the order GitHub starts them, from their needs."
        )
        self.checks = self._readout(
            "What GitHub would sa&y:",
            "Each reason GitHub would reject this file, or that it is fine.",
        )
        note = wx.StaticText(self.dialog, label=COMMENTS_NOTE)
        note.SetName("About comments")
        self.root.Add(note, 0, wx.EXPAND | wx.ALL, 8)
        self.refresh()

    def _readout(self, label: str, help_text: str) -> Any:
        wx = self._wx
        self.root.Add(wx.StaticText(self.dialog, label=label), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        box = wx.TextCtrl(self.dialog, value="", style=wx.TE_MULTILINE | wx.TE_READONLY)
        box.SetName(label.replace("&", "").rstrip(":"))
        box.SetHelpText(help_text)
        self.root.Add(box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        return box

    def refresh(self, trigger: int = -1, job_index: int = -1) -> None:
        found = triggers(self.draft)
        self.trigger_rows.set_rows(
            [trigger_summary(event, settings) for event, settings in found.items()], trigger
        )
        self.job_rows.set_rows([job_summary(self.draft, i) for i in job_ids(self.draft)], job_index)
        self.permissions.SetLabel(
            "Workflow Per&missions: "
            + permissions_summary(self.draft.data.get("permissions"))
            + "..."
        )
        self.order.SetValue(order_sentence(self.draft))
        problems = check_workflow(self.draft)
        self.checks.SetValue(
            "\n".join(p.text() for p in problems) if problems else "GitHub would take this file."
        )

    # -- forms, overridable in tests ----------------------------------------------------------

    def ask(self, title: str, fields: Sequence[Field]) -> dict[str, Any] | None:
        return ask_fields(self.dialog, title, fields, announce=self._announce)

    def choose(self, title: str, prompt: str, choices: Sequence[str]) -> int:
        wx = self._wx
        with wx.SingleChoiceDialog(self.dialog, prompt, title, list(choices)) as pick:
            if self._show(pick, title) != wx.ID_OK:
                return -1
            return int(pick.GetSelection())

    def ask_items(self, dialog: ItemsDialog) -> list[Any] | None:
        return dialog.show()

    def _show(self, window: Any, title: str) -> int:
        from quill.ui.dialog_contract import show_modal_dialog

        return int(show_modal_dialog(window, title))

    # -- triggers ------------------------------------------------------------------------

    def _selected_event(self) -> str:
        index = self.trigger_rows.selection()
        events = list(triggers(self.draft))
        return events[index] if 0 <= index < len(events) else ""

    def add_trigger(self) -> None:
        index = self.choose(
            "Add Trigger", "What starts the workflow:", [r for r, _e in EVENT_CHOICES]
        )
        if index < 0:
            return
        event = EVENT_CHOICES[index][1]
        if not event:
            typed = self.ask("Add Trigger", [Field("event", "Event name:", "", "Such as label.")])
            event = str((typed or {}).get("event", "")).strip()
        if not event:
            return
        if event in triggers(self.draft):
            self._announce(f"{event} is already a trigger; edit it instead.")
            return
        set_trigger(self.draft, event, None)
        self.edit_trigger(event)

    def edit_trigger(self, event: str = "") -> None:
        event = event or self._selected_event()
        if not event:
            return
        settings = triggers(self.draft).get(event)
        if event == "schedule":
            values = self.ask("Schedule", schedule_fields(settings))
            if values is not None:
                set_trigger(self.draft, event, schedule_from(values))
        elif event in ("workflow_dispatch", "workflow_call"):
            self._edit_inputs(event, settings)
        else:
            values = self.ask(f"Trigger: {event}", filters_fields(event, settings))
            if values is not None:
                set_trigger(self.draft, event, filters_from(values, settings))
        events = list(triggers(self.draft))
        self.refresh(trigger=events.index(event) if event in events else -1)

    def _edit_inputs(self, event: str, settings: Any) -> None:
        def edit(item: Any) -> Any:
            name, spec = item if item is not None else ("", {"type": "string"})
            values = self.ask("Input", input_fields(name, spec))
            if values is None:
                return None
            made = input_from(values, spec)
            return made if made[0] else None

        window = ItemsDialog(
            self.dialog,
            "Inputs",
            "input",
            list(dispatch_inputs(settings).items()),
            lambda item, _n: input_summary(item[0], item[1]),
            edit,
            help_text="What a person fills in when they run it by hand, in order.",
        )
        found = self.ask_items(window)
        if found is not None:
            set_trigger(self.draft, event, inputs_settings(settings, dict(found)))

    def remove_trigger(self) -> None:
        event = self._selected_event()
        if event:
            remove_trigger(self.draft, event)
            self._announce(f"Removed the {event} trigger.")
            self.refresh(trigger=0)

    # -- permissions ----------------------------------------------------------------------

    def edit_permissions(self, job_id: str | None) -> None:
        owner = self.draft.data if job_id is None else job(self.draft, job_id)
        if job_id is not None and not owner:
            return
        title = "Workflow Permissions" if job_id is None else f"Permissions: {job_id}"
        values = self.ask(title, permissions_fields(owner.get("permissions")))
        if values is None:
            return
        chosen = permissions_from(values)
        if chosen is None:
            owner.pop("permissions", None)
        else:
            owner["permissions"] = chosen
        self.refresh(job_index=self.job_rows.selection())

    # -- jobs -----------------------------------------------------------------------------

    def _selected_job(self) -> str:
        index = self.job_rows.selection()
        ids = job_ids(self.draft)
        return ids[index] if 0 <= index < len(ids) else ""

    def _job_fields(self, job_id: str, spec: dict[str, Any]) -> list[Field]:
        others = tuple(i for i in job_ids(self.draft) if i != job_id)
        runs_on = spec.get("runs-on", "ubuntu-latest" if not spec else "")
        return [
            Field("id", "Job id:", job_id, "Letters, digits, - and _; other jobs' needs use it."),
            Field(
                "name", "Job name:", spec.get("name", ""), "What GitHub shows; empty uses the id."
            ),
            Field(
                "runs-on",
                "Runs on:",
                ", ".join(runs_on) if isinstance(runs_on, list) else str(runs_on or ""),
                "The runner: ubuntu-latest, windows-latest, macos-latest, or labels of your own.",
            ),
            Field(
                "needs",
                "Runs after these jobs:",
                needs_of(spec),
                "Check each job that must finish first. None checked: it starts at once.",
                "checks",
                others,
            ),
            Field("if", "Only if:", spec.get("if", ""), "A condition; empty runs it always."),
        ]

    def add_job(self) -> None:
        values = self.ask("Add Job", self._job_fields("", {}))
        if values is None:
            return
        job_id = make_job_id(str(values["id"]) or str(values["name"]), job_ids(self.draft))
        spec = self._job_from(
            values, {"steps": [{"name": "Check out the code", "uses": "actions/checkout@v4"}]}
        )
        replace_job(self.draft, job_id, job_id, spec)
        self.refresh(job_index=job_ids(self.draft).index(job_id))

    def edit_job(self) -> None:
        job_id = self._selected_job()
        if not job_id:
            return
        spec = dict(job(self.draft, job_id))
        values = self.ask(f"Job: {job_id}", self._job_fields(job_id, spec))
        if values is None:
            return
        new_id = str(values["id"]).strip() or job_id
        if new_id != job_id and new_id in job_ids(self.draft):
            self._announce(f"There is already a job {new_id}; nothing was changed.")
            return
        replace_job(self.draft, job_id, new_id, self._job_from(values, spec))
        self.refresh(job_index=job_ids(self.draft).index(new_id))

    @staticmethod
    def _job_from(values: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
        kept = dict(spec)
        for key in ("name", "if"):
            text = str(values.get(key, "")).strip()
            if text:
                kept[key] = text
            else:
                kept.pop(key, None)
        runner = [
            part.strip() for part in str(values.get("runs-on", "")).split(",") if part.strip()
        ]
        if runner:
            kept["runs-on"] = runner[0] if len(runner) == 1 else runner
        else:
            kept.pop("runs-on", None)
        needs = list(values.get("needs") or [])
        if needs:
            kept["needs"] = needs
        else:
            kept.pop("needs", None)
        order = ["name", "permissions", "needs", "if", "runs-on"]
        return {
            **{k: kept[k] for k in order if k in kept},
            **{k: v for k, v in kept.items() if k not in order},
        }

    def edit_steps(self) -> None:
        job_id = self._selected_job()
        if not job_id:
            return
        spec = job(self.draft, job_id)
        if spec.get("uses"):
            self._announce(f"{job_id} calls a reusable workflow, which has no steps of its own.")
            return

        def edit(step: Any) -> Any:
            values = self.ask("Step", step_fields(step or {}))
            return step_from(values, step or {}) if values is not None else None

        window = ItemsDialog(
            self.dialog,
            f"Steps: {job_name(self.draft, job_id)}",
            "step",
            list(spec.get("steps") or []),
            lambda step, number: step_summary(step, number),
            edit,
            help_text="The job's steps, run one after another. Enter edits the selected step.",
        )
        found = self.ask_items(window)
        if found is not None:
            spec["steps"] = list(found)
            self.refresh(job_index=self.job_rows.selection())

    def remove_job(self) -> None:
        job_id = self._selected_job()
        if not job_id:
            return
        freed = remove_job(self.draft, job_id)
        said = f"Removed {job_id}."
        if freed:
            said += f" {', '.join(freed)} no longer wait for it."
        self._announce(said)
        self.refresh(job_index=0)

    def move(self, delta: int) -> None:
        job_id = self._selected_job()
        if job_id and move_job(self.draft, job_id, delta):
            self.refresh(job_index=job_ids(self.draft).index(job_id))

    # -- saving ---------------------------------------------------------------------------

    def build(self) -> tuple[str | None, str]:
        name = self.name.GetValue().strip()
        if name and "name" not in self.draft.data:
            self.draft.data = {"name": name, **self.draft.data}
        elif name:
            self.draft.data["name"] = name
        else:
            self.draft.data.pop("name", None)
        self.use_pull_request = bool(self.pull.GetValue()) or self.protected
        problems = check_workflow(self.draft)
        if problems:
            self.refresh()
            count = len(problems)
            return None, (
                f"GitHub would reject this file ({count} problem{'s' if count != 1 else ''}). "
                f"First: {problems[0].text()}"
            )
        return dump_workflow(self.draft), ""
