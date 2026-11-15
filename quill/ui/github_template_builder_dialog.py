"""Build a GitHub template with the keyboard: fields as a list, the source, a preview.

GitHub PRD 21.3 and 21.4. The model, the checks and the starters are
:mod:`quill.core.github.template_builder`'s; this is only the window.

An issue form or a discussion category form opens as the **builder**: the
form's own keys (name, description, title prefix, labels, assignees) as
labelled text boxes, then the fields as one list -- each row "Steps to
reproduce, long text, required" -- with Add Field..., Edit Field..., Move Up,
Move Down and Remove Field beside it. Edit Source... shows the YAML; what is
typed there comes back into the list, and YAML that cannot be read is said
and kept, never thrown away. Preview... fills the form exactly as a person
filing it would and shows the body GitHub will write. The Checks box lists
every problem, and Save refuses while one is an error.

Anything else -- a Markdown template, a pull request template, the chooser,
a community file, or a form too large or broken to build -- opens as **the
source** alone: one text box, its checks and Save. That is the honest
fallback: the draft is never lost because the builder cannot show it.

Nothing is sent from here. :attr:`TemplateBuilderDialog.result` holds the
text to save and :attr:`use_pull_request` the route; the Workbench asks and
saves (quill/ui/github_workbench_templates.py).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from quill.core.github.template_builder import (
    FIELD_KIND_NAMES,
    FormDraft,
    TemplateDraftError,
    TemplateProblem,
    check,
    dump_draft,
    field_summary,
    load_draft,
)
from quill.ui.dialog_contract import apply_modal_ids, show_message_box, show_modal_dialog
from quill.ui.dpi import dip_size
from quill.ui.github_template_field_dialog import FieldDialog

__all__ = ["FieldDialog", "TemplateBuilderDialog", "check_source"]

_KIND_ORDER = ("input", "textarea", "dropdown", "checkboxes", "markdown")


def _error_text(exc: BaseException) -> str:
    return str(exc.args[0]) if exc.args else str(exc)


def check_source(kind: str, text: str) -> list[TemplateProblem]:
    """The checks for a template edited as source (not a form)."""
    problems: list[TemplateProblem] = []
    if not text.strip():
        problems.append(TemplateProblem("Source", "the file is empty"))
    if kind == "chooser":
        try:
            import yaml  # type: ignore[import-untyped]

            data = yaml.safe_load(text)
            if data is not None and not isinstance(data, dict):
                problems.append(TemplateProblem("Source", "the chooser is not a set of keys"))
        except Exception as exc:  # noqa: BLE001 - YAML errors are the check
            problems.append(TemplateProblem("Source", f"not valid YAML: {exc}"))
    if kind == "issue_template":
        from quill.core.github.issue_templates import _front_matter

        metadata, _body = _front_matter(text)
        for key in ("name", "about"):
            if not metadata.get(key):
                problems.append(
                    TemplateProblem(
                        "Front matter", f"a Markdown issue template needs {key}:", "warning"
                    )
                )
    if len(text.encode("utf-8")) > 1_000_000:
        problems.append(TemplateProblem("Source", "the file is over 1 MB; GitHub will refuse it"))
    return problems


class TemplateBuilderDialog:
    """A template's builder or source; :attr:`result` is the text to save."""

    def __init__(
        self,
        parent: object,
        *,
        text: str,
        kind: str,
        path: str,
        repository: str,
        announce: Callable[[str], None] | None = None,
        other_names: Iterable[str] = (),
        known_labels: Iterable[str] | None = None,
        known_assignees: Iterable[str] | None = None,
        protected: bool = False,
    ) -> None:
        import wx

        self._wx = wx
        self.kind = kind
        self.path = path
        self.repository = repository
        self._announce = announce or (lambda _text: None)
        self._other_names = tuple(other_names)
        self._known_labels = None if known_labels is None else tuple(known_labels)
        self._known_assignees = None if known_assignees is None else tuple(known_assignees)
        self.result: str | None = None
        self.use_pull_request = protected
        self.draft: FormDraft | None = None
        #: Why the builder could not read the form ("" when it could).
        self.fallback = ""
        if kind in ("issue_form", "discussion_form"):
            try:
                self.draft = load_draft(text, kind=kind)
            except TemplateDraftError as exc:
                self.fallback = _error_text(exc)
        self._title = f"Template: {path.rsplit('/', 1)[-1]}"
        self.dialog = wx.Dialog(
            parent, title=self._title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 640, 600))
        self.dialog.SetSize(dip_size(self.dialog, 760, 720))
        root = wx.BoxSizer(wx.VERTICAL)
        where = f"{path} in {repository}."
        if self.fallback:
            where += (
                f" The builder cannot show this form ({self.fallback}), so it opens as source; "
                "nothing you type here is lost."
            )
        intro = wx.StaticText(
            self.dialog,
            label=where + " Save asks before anything is sent to GitHub.",
        )
        intro.Wrap(700)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 8)
        self._top: dict[str, Any] = {}
        self.fields: Any = None
        self.source: Any = None
        if self.draft is not None:
            self._build_form(root)
        else:
            caption = wx.StaticText(self.dialog, label="&Source:")
            root.Add(caption, 0, wx.LEFT | wx.RIGHT, 8)
            self.source = wx.TextCtrl(
                self.dialog, value=text, style=wx.TE_MULTILINE | wx.TE_DONTWRAP
            )
            self.source.SetName("Source")
            self.source.SetHelpText("The file as GitHub holds it. Edit it here and Save.")
            root.Add(self.source, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        checks_label = wx.StaticText(self.dialog, label="Chec&ks:")
        root.Add(checks_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.checks = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        self.checks.SetName("Checks")
        self.checks.SetHelpText(
            "Every problem GitHub would report after saving, found before it. "
            "Errors stop Save; warnings do not."
        )
        root.Add(self.checks, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self.pull = wx.CheckBox(self.dialog, label="Save through a pull re&quest")
        self.pull.SetValue(protected)
        self.pull.SetHelpText(
            "Save to a new branch and open a pull request into the default branch. "
            "Checked already when the default branch is protected."
        )
        root.Add(self.pull, 0, wx.ALL, 8)
        buttons = wx.StdDialogButtonSizer()
        save = wx.Button(self.dialog, wx.ID_OK, "Save")
        save.SetHelpText("Check the template, then ask before committing it to GitHub.")
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Close without saving anything.")
        buttons.AddButton(save)
        buttons.AddButton(cancel)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        save.Bind(wx.EVT_BUTTON, self._on_save)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self.refresh_checks()

    # -- the builder ------------------------------------------------------------

    def _build_form(self, root: Any) -> None:
        wx = self._wx
        draft = self.draft
        assert draft is not None
        grid = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        grid.AddGrowableCol(1)
        keys = [
            ("description", "&Description:", "What the form is for; shown in the chooser."),
            ("title", "&Title prefix:", "Starts every title, such as [Bug]: ."),
            ("labels", "&Labels:", "Labels it adds, separated by commas."),
            ("assignees", "Ass&ignees:", "People it assigns, separated by commas."),
        ]
        if draft.kind == "issue_form":
            keys.insert(0, ("name", "&Name:", "The form's name in the template chooser."))
        else:
            keys = [k for k in keys if k[0] in ("title", "labels")]
        for key, label, help_text in keys:
            caption = wx.StaticText(self.dialog, label=label)
            control = wx.TextCtrl(self.dialog, value=draft.get(key))
            control.SetName(label.replace("&", "").rstrip(":"))
            control.SetHelpText(help_text)
            control.Bind(wx.EVT_TEXT, lambda _e, k=key, c=control: self._set_top(k, c))
            grid.Add(caption, 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(control, 1, wx.EXPAND)
            self._top[key] = control
        root.Add(grid, 0, wx.EXPAND | wx.ALL, 8)
        pickers = wx.BoxSizer(wx.HORIZONTAL)
        for key, label, known in (
            ("labels", "C&hoose Labels...", self._known_labels),
            ("assignees", "Choose Assi&gnees...", self._known_assignees),
        ):
            if known is None or key not in self._top:
                continue
            button = wx.Button(self.dialog, label=label)
            button.SetHelpText(f"Pick from the repository's {key} instead of typing them.")
            button.Bind(wx.EVT_BUTTON, lambda _e, k=key: self._on_pick(k))
            pickers.Add(button, 0, wx.RIGHT, 4)
        root.Add(pickers, 0, wx.LEFT | wx.RIGHT, 8)
        caption = wx.StaticText(self.dialog, label="&Fields:")
        root.Add(caption, 0, wx.LEFT | wx.RIGHT, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.fields = wx.ListBox(self.dialog, choices=[])
        self.fields.SetName("Fields")
        self.fields.SetHelpText(
            "The form's fields in order. Enter edits one; the buttons beside add, move and remove."
        )
        row.Add(self.fields, 1, wx.EXPAND | wx.RIGHT, 8)
        side = wx.BoxSizer(wx.VERTICAL)
        for label, help_text, handler in (
            ("&Add Field...", "Add a field after the selected one.", self._on_add),
            ("&Edit Field...", "Change the selected field.", self._on_edit),
            ("Move &Up", "Move the selected field up one.", lambda _e: self.move(-1)),
            ("Move Do&wn", "Move the selected field down one.", lambda _e: self.move(1)),
            ("&Remove Field", "Remove the selected field.", lambda _e: self.remove()),
            ("&Preview...", "Fill the form as people will, and see the body.", self._on_preview),
            ("Edit &Source...", "The form's YAML, to read or edit.", self._on_source),
        ):
            button = wx.Button(self.dialog, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, handler)
            side.Add(button, 0, wx.EXPAND | wx.BOTTOM, 4)
        row.Add(side, 0)
        root.Add(row, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        from quill.ui.dialog_contract import apply_listbox_activation

        apply_listbox_activation(self.fields, self._on_edit)
        self.refresh_fields(0)

    def pick(self, key: str, chosen: Iterable[str]) -> None:
        """Set the labels or assignees to *chosen* (what the picker returns)."""
        control = self._top.get(key)
        if control is None:
            return
        control.ChangeValue(", ".join(chosen))
        self._set_top(key, control)

    def _on_pick(self, key: str) -> None:
        wx = self._wx
        known = list((self._known_labels if key == "labels" else self._known_assignees) or ())
        if not known:
            self._announce(f"The repository has no {key} to choose from.")
            return
        current = {part.strip().casefold() for part in self._top[key].GetValue().split(",")}
        title = "Choose Labels" if key == "labels" else "Choose Assignees"
        with wx.MultiChoiceDialog(
            self.dialog, f"The {key} this form applies:", title, known
        ) as ask:
            ask.SetName(title)
            ask.SetSelections([i for i, name in enumerate(known) if name.casefold() in current])
            if show_modal_dialog(ask, title) != wx.ID_OK:
                return
            self.pick(key, [known[i] for i in ask.GetSelections()])

    def _set_top(self, key: str, control: Any) -> None:
        if self.draft is not None:
            self.draft.set(key, control.GetValue())
            self.refresh_checks()

    def refresh_fields(self, select: int = -1) -> None:
        if self.draft is None or self.fields is None:
            return
        self.fields.Set([field_summary(raw) for raw in self.draft.fields])
        if self.draft.fields:
            self.fields.SetSelection(max(0, min(select, len(self.draft.fields) - 1)))
        self.refresh_checks()

    def selected(self) -> int:
        return int(self.fields.GetSelection()) if self.fields is not None else -1

    def add_field(self, raw: dict[str, Any]) -> None:
        assert self.draft is not None
        at = self.selected() + 1 if self.selected() >= 0 else len(self.draft.fields)
        self.draft.fields.insert(at, raw)
        self.refresh_fields(at)

    def replace_field(self, index: int, raw: dict[str, Any]) -> None:
        assert self.draft is not None
        self.draft.fields[index] = raw
        self.refresh_fields(index)

    def move(self, delta: int) -> None:
        if self.draft is None or self.selected() < 0:
            return
        index = self.selected()
        moved = self.draft.move(index, delta)
        if moved == index:
            self._announce("Already at the top." if delta < 0 else "Already at the bottom.")
            return
        self.refresh_fields(moved)

    def remove(self) -> None:
        if self.draft is None or self.selected() < 0:
            return
        index = self.selected()
        self.draft.remove(index)
        self.refresh_fields(index)

    def _on_add(self, _event: Any) -> None:
        wx = self._wx
        names = [f"{FIELD_KIND_NAMES[k].capitalize()} ({k})" for k in _KIND_ORDER]
        with wx.SingleChoiceDialog(self.dialog, "What kind of field:", "Add Field", names) as ask:
            ask.SetName("Add Field")
            if show_modal_dialog(ask, "Add Field") != wx.ID_OK:
                return
            kind = _KIND_ORDER[ask.GetSelection()]
        assert self.draft is not None
        made = FieldDialog(
            self.dialog, kind, taken=self.draft.ids(), announce=self._announce
        ).show()
        if made is not None:
            self.add_field(made)

    def _on_edit(self, _event: Any) -> None:
        index = self.selected()
        if self.draft is None or index < 0:
            return
        raw = self.draft.fields[index]
        kind = str(raw.get("type") or "")
        if kind not in FIELD_KIND_NAMES:
            self._announce("QUILL cannot edit this kind of field; use Edit Source.")
            return
        made = FieldDialog(
            self.dialog, kind, raw, taken=self.draft.ids(skip=index), announce=self._announce
        ).show()
        if made is not None:
            self.replace_field(index, made)

    def apply_source(self, text: str) -> str:
        """Read *text* back into the builder; returns the problem ("" when read)."""
        assert self.draft is not None
        try:
            self.draft = load_draft(text, kind=self.draft.kind)
        except TemplateDraftError as exc:
            return _error_text(exc)
        for key, control in self._top.items():
            control.ChangeValue(self.draft.get(key))
        self.refresh_fields(self.selected())
        return ""

    def _on_source(self, _event: Any) -> None:
        wx = self._wx
        assert self.draft is not None
        text = dump_draft(self.draft)
        while True:
            with wx.TextEntryDialog(
                self.dialog,
                "The form's YAML. OK reads it back into the builder.",
                "Edit Source",
                text,
                style=wx.OK | wx.CANCEL | wx.TE_MULTILINE,
            ) as ask:
                ask.SetName("Form source")
                if show_modal_dialog(ask, "Edit Source") != wx.ID_OK:
                    return
                text = str(ask.GetValue())
            problem = self.apply_source(text)
            if not problem:
                return
            # Keep what was typed: reopen it with the reason, never discard it.
            self._announce(f"{problem} Your text is kept; fix it or cancel.")

    def preview_form(self) -> Any:
        from quill.core.github.issue_forms import parse_issue_form

        assert self.draft is not None
        return parse_issue_form(dump_draft(self.draft), self.path.rsplit("/", 1)[-1])

    def _on_preview(self, _event: Any) -> None:
        from quill.ui.github_issue_form_dialog import IssueFormDialog

        form = self.preview_form()
        if form.unsupported:
            self._announce(form.unsupported)
            return
        window = IssueFormDialog(
            self.dialog,
            form,
            repository=self.repository,
            announce=self._announce,
            noun="preview",
            action_label="Show Body",
        )
        if window.show() and window.result is not None:
            title, body = window.result
            show_message_box(
                f"Title: {title}\n\n{body[:4000]}",
                "Body GitHub Would Write",
                self._wx.OK,
                self.dialog,
            )

    # -- checks and saving ---------------------------------------------------------

    def text(self) -> str:
        if self.draft is not None:
            return dump_draft(self.draft)
        return str(self.source.GetValue()) if self.source is not None else ""

    def problems(self) -> list[TemplateProblem]:
        if self.draft is not None:
            return check(
                self.draft,
                other_names=self._other_names,
                known_labels=self._known_labels,
                known_assignees=self._known_assignees,
            )
        found = check_source(self.kind, self.text())
        if self.fallback:
            found.insert(0, TemplateProblem("Form", self.fallback, "warning"))
        return found

    def refresh_checks(self) -> list[TemplateProblem]:
        found = self.problems()
        if hasattr(self, "checks"):
            self.checks.ChangeValue("\n".join(p.sentence() for p in found) or "No problems found.")
        return found

    def _on_save(self, event: Any) -> None:
        found = self.refresh_checks()
        errors = [p for p in found if p.severity == "error"]
        if errors:
            self._announce(
                f"{len(errors)} problem{'s' if len(errors) != 1 else ''} to fix first: "
                f"{errors[0].sentence()}"
            )
            self.checks.SetFocus()
            return
        self.result = self.text()
        self.use_pull_request = bool(self.pull.GetValue())
        event.Skip()

    def show(self) -> str | None:
        try:
            if show_modal_dialog(self.dialog, self._title) != self._wx.ID_OK:
                return None
            return self.result
        finally:
            self.dialog.Destroy()
