"""The Dependabot and CODEOWNERS sheets (GitHub PRD 21.8 and 22.1).

- **Dependabot Configuration** (``.github/dependabot.yml``): the update
  entries as a list, one row each ("pip in /, weekly on Monday, up to 5 pull
  requests"), with Add, Edit, Remove and Move; each entry is a form of its
  ecosystem, directories, schedule, pull request limit, target branch and
  labels. What the form does not show is kept. What Dependabot would refuse
  is listed under the entries and stops Save.
- **Code Owners (CODEOWNERS)**: the rules as a table of pattern and owners,
  in file order, because the last matching rule wins; Add, Edit, Remove and
  Move; Who Owns This Path, answered as GitHub decides; Check Owners, which
  asks GitHub whether each owner exists and can write; and the problems
  GitHub itself reports for the file (``codeowners/errors``).

Nothing is sent from here; each window's :attr:`result` is the text to save,
and the Workbench asks before saving.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.core.github.actions_yaml import COMMENTS_NOTE, ActionsYamlError
from quill.core.github.codeowners_table import (
    CodeownersLines,
    OwnersRow,
    owner_problem,
    pattern_problem,
    who_owns,
)
from quill.core.github.dependabot_config import (
    DAYS,
    ECOSYSTEMS,
    INTERVALS,
    check_config,
    dump_config,
    entry_summary,
    load_config,
    new_entry,
)
from quill.ui.github_authoring_form import Field, RowList, ask_fields
from quill.ui.github_template_sheets_dialog import _Sheet

__all__ = ["CodeownersDialog", "DependabotDialog", "entry_fields", "entry_from"]


def _listed(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return "" if value is None else str(value)


def _split(text: str) -> list[str]:
    return [p.strip() for p in text.replace("\n", ",").split(",") if p.strip()]


def entry_fields(entry: dict[str, Any]) -> list[Field]:
    schedule = entry.get("schedule") if isinstance(entry.get("schedule"), dict) else {}
    places = entry.get("directories", entry.get("directory", "/"))
    limit = entry.get("open-pull-requests-limit")
    return [
        Field(
            "package-ecosystem",
            "Package ecosystem:",
            str(entry.get("package-ecosystem", "github-actions")),
            "The package manager Dependabot reads: pip, npm, github-actions and so on.",
            "choice",
            ECOSYSTEMS,
        ),
        Field(
            "directories",
            "Directories:",
            _listed(places),
            "Where its manifest is, from the repository's root: / for the root. Several, "
            "separated by commas.",
        ),
        Field(
            "interval",
            "How often:",
            str(schedule.get("interval", "weekly")),
            "How often Dependabot checks for new versions.",
            "choice",
            INTERVALS,
        ),
        Field(
            "day",
            "Day, for weekly:",
            str(schedule.get("day", "")),
            "The day a weekly check runs; empty is Monday.",
            "choice",
            ("", *DAYS),
        ),
        Field(
            "time", "Time (hh:mm):", str(schedule.get("time", "")), "Such as 09:00; empty is any."
        ),
        Field(
            "timezone", "Time zone:", str(schedule.get("timezone", "")), "Such as Europe/London."
        ),
        Field("cronjob", "Cron, for cron:", str(schedule.get("cronjob", "")), "Five cron fields."),
        Field(
            "open-pull-requests-limit",
            "Most open pull requests:",
            "" if limit is None else str(limit),
            "Empty is Dependabot's default, 5. 0 turns version updates off for this entry.",
        ),
        Field(
            "target-branch",
            "Target branch:",
            str(entry.get("target-branch", "")),
            "Empty is the default branch.",
        ),
        Field("labels", "Labels:", _listed(entry.get("labels")), "Separated by commas."),
    ]


def entry_from(values: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    """The entry with the form's answers; what the form does not show is kept."""
    kept = dict(entry)
    kept["package-ecosystem"] = values["package-ecosystem"]
    places = _split(str(values.get("directories", ""))) or ["/"]
    kept.pop("directory", None)
    kept.pop("directories", None)
    if len(places) == 1 and "directories" not in entry:
        kept["directory"] = places[0]
    else:
        kept["directories"] = places
    schedule = dict(entry.get("schedule") or {}) if isinstance(entry.get("schedule"), dict) else {}
    schedule["interval"] = values["interval"]
    for key in ("day", "time", "timezone", "cronjob"):
        text = str(values.get(key, "")).strip()
        if text:
            schedule[key] = text
        else:
            schedule.pop(key, None)
    kept["schedule"] = schedule
    limit = str(values.get("open-pull-requests-limit", "")).strip()
    if limit:
        kept["open-pull-requests-limit"] = int(limit) if limit.isdigit() else limit
    else:
        kept.pop("open-pull-requests-limit", None)
    for key in ("target-branch",):
        text = str(values.get(key, "")).strip()
        if text:
            kept[key] = text
        else:
            kept.pop(key, None)
    labels = _split(str(values.get("labels", "")))
    if labels:
        kept["labels"] = labels
    else:
        kept.pop("labels", None)
    order = ["package-ecosystem", "directory", "directories", "schedule"]
    return {
        **{k: kept[k] for k in order if k in kept},
        **{k: v for k, v in kept.items() if k not in order},
    }


class DependabotDialog(_Sheet):
    title = "Dependabot Configuration"

    def __init__(
        self, parent: object, text: str, *, announce: Callable[[str], None] | None = None
    ) -> None:
        self.unreadable = ""
        try:
            self.draft = load_config(text)
        except ActionsYamlError as exc:
            self.draft = load_config("")
            self.unreadable = str(exc.args[0]) if exc.args else str(exc)
        super().__init__(parent, announce)

    def body(self) -> None:
        wx = self._wx
        self.rows = RowList(
            self.dialog,
            self.root,
            "Up&dates:",
            "Each ecosystem and folder Dependabot keeps up to date. Enter edits the selected one.",
            (
                ("&Add Entry...", "Add an ecosystem and folder to keep up to date.", self.add),
                ("&Edit Entry...", "Change the selected entry.", self.edit),
                ("&Remove Entry", "Remove the selected entry.", self.remove),
                ("Move &Up", "Move the selected entry earlier.", lambda: self.move(-1)),
                ("Move Do&wn", "Move the selected entry later.", lambda: self.move(1)),
            ),
        )
        self.root.Add(
            wx.StaticText(self.dialog, label="What Dependabot would &say:"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            8,
        )
        self.checks = wx.TextCtrl(self.dialog, value="", style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.checks.SetName("What Dependabot would say")
        self.checks.SetHelpText(
            "Each reason Dependabot would refuse this file, or that it is fine."
        )
        self.root.Add(self.checks, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        note = wx.StaticText(self.dialog, label=self.unreadable or COMMENTS_NOTE)
        note.SetName("About this file")
        self.root.Add(note, 0, wx.EXPAND | wx.ALL, 8)
        self.refresh(0)

    def ask(self, title: str, fields: Sequence[Field]) -> dict[str, Any] | None:
        return ask_fields(self.dialog, title, fields, announce=self._announce)

    def refresh(self, select: int = -1) -> None:
        self.rows.set_rows([entry_summary(e) for e in self.draft.entries], select)
        problems = check_config(self.draft)
        self.checks.SetValue(
            "\n".join(problems) if problems else "Dependabot would take this file."
        )

    def add(self) -> None:
        entry = new_entry()
        values = self.ask("Add Entry", entry_fields(entry))
        if values is not None:
            self.draft.entries.append(entry_from(values, entry))
            self.refresh(len(self.draft.entries) - 1)

    def edit(self) -> None:
        index = self.rows.selection()
        if index < 0:
            return
        entry = self.draft.entries[index]
        values = self.ask("Entry", entry_fields(entry))
        if values is not None:
            self.draft.entries[index] = entry_from(values, entry)
            self.refresh(index)

    def remove(self) -> None:
        index = self.rows.selection()
        if index >= 0:
            del self.draft.entries[index]
            self.refresh(index)

    def move(self, delta: int) -> None:
        index = self.rows.selection()
        entries = self.draft.entries
        target = index + delta
        if index < 0 or not 0 <= target < len(entries):
            return
        entries[index], entries[target] = entries[target], entries[index]
        self.refresh(target)

    def build(self) -> tuple[str | None, str]:
        if self.unreadable:
            return None, f"{self.unreadable} Edit it as source instead."
        problems = check_config(self.draft)
        if problems:
            return None, f"Dependabot would refuse this file. First: {problems[0]}"
        return dump_config(self.draft), ""


class CodeownersDialog(_Sheet):
    title = "Code Owners (CODEOWNERS)"

    def __init__(
        self,
        parent: object,
        text: str,
        *,
        announce: Callable[[str], None] | None = None,
        check: Callable[[str, Callable[[list[Any]], None]], None] | None = None,
        errors: Callable[[Callable[[list[str]], None]], None] | None = None,
    ) -> None:
        self.lines = CodeownersLines(text)
        #: Starts the owner check in the background and calls back with the
        #: results (PRD 21.8); None where there is no repository to ask.
        self._check = check
        self._errors = errors
        super().__init__(parent, announce)
        if errors is not None:
            errors(self.show_github_problems)

    def body(self) -> None:
        wx = self._wx
        self.root.Add(
            wx.StaticText(self.dialog, label="&Rules (the last matching rule wins):"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            8,
        )
        self.table = wx.ListCtrl(self.dialog, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.table.SetName("Rules")
        self.table.SetHelpText(
            "Each rule: its line, the path pattern, and its owners. A later rule wins over an "
            "earlier one for the same path. Enter edits the selected rule."
        )
        for column, (heading, width) in enumerate((
            ("Line", 60),
            ("Pattern", 220),
            ("Owners", 320),
        )):
            self.table.InsertColumn(column, heading, width=self.dialog.FromDIP(width))
        self.table.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: self.edit())
        self.root.Add(self.table, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, help_text, handler in (
            (
                "&Add Rule...",
                "Add a rule at the end, where it wins over the rules above.",
                self.add,
            ),
            ("&Edit Rule...", "Change the selected rule's pattern or owners.", self.edit),
            ("Remo&ve Rule", "Remove the selected rule.", self.remove),
            (
                "Move &Up",
                "Move the selected rule earlier, so later rules win over it.",
                lambda: self.move(-1),
            ),
            (
                "Move Do&wn",
                "Move the selected rule later, so it wins over more.",
                lambda: self.move(1),
            ),
        ):
            button = wx.Button(self.dialog, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, run=handler: run())
            row.Add(button, 0, wx.RIGHT, 4)
        self.root.Add(row, 0, wx.ALL, 8)
        self.path = self.text_box(
            "Who owns this &path:", "", "Type a path, such as docs/guide.md, then Look Up."
        )
        look = wx.Button(self.dialog, label="&Look Up")
        look.SetHelpText("Say which rule owns the path above, and its owners.")
        look.Bind(wx.EVT_BUTTON, lambda _e: self._announce(self.look_up()))
        self.root.Add(look, 0, wx.ALL, 8)
        self.answer = wx.StaticText(self.dialog, label="")
        self.answer.SetName("Who owns it")
        self.root.Add(self.answer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        if self._check is not None:
            check = wx.Button(self.dialog, label="Check &Owners")
            check.SetHelpText(
                "Ask GitHub whether every owner exists and can write to this "
                "repository. GitHub skips one that cannot, without saying so."
            )
            check.Bind(wx.EVT_BUTTON, lambda _e: self.check_owners())
            self.root.Add(check, 0, wx.ALL, 8)
        self.root.Add(
            wx.StaticText(self.dialog, label="Pro&blems found:"), 0, wx.LEFT | wx.RIGHT, 8
        )
        self.findings = wx.TextCtrl(self.dialog, value="", style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.findings.SetName("Problems found")
        self.findings.SetHelpText(
            "Rules GitHub would skip by their shape, the problems GitHub reports for the file "
            "on the default branch, and what Check Owners found."
        )
        self.root.Add(self.findings, 1, wx.EXPAND | wx.ALL, 8)
        self._github: list[str] = []
        self._owners: list[str] = []
        self.refresh(0)

    def ask(self, title: str, fields: Sequence[Field]) -> dict[str, Any] | None:
        def problem(values: dict[str, Any]) -> str:
            said = pattern_problem(str(values["pattern"]).strip())
            if said:
                return said
            for owner in str(values["owners"]).replace(",", " ").split():
                said = owner_problem(owner)
                if said:
                    return said
            return ""

        return ask_fields(self.dialog, title, fields, check=problem, announce=self._announce)

    def rows(self) -> list[OwnersRow]:
        return self.lines.rows()

    def refresh(self, select: int = -1) -> None:
        self.table.DeleteAllItems()
        rows = self.rows()
        for index, row in enumerate(rows):
            self.table.InsertItem(index, str(row.line))
            self.table.SetItem(index, 1, row.pattern)
            self.table.SetItem(index, 2, ", ".join(row.owners) or "no owners")
        if rows and select >= 0:
            chosen = min(select, len(rows) - 1)
            self.table.Select(chosen)
            self.table.Focus(chosen)
        self._show_findings()

    def _show_findings(self) -> None:
        shape = self.lines.problems()
        said = shape + [f"GitHub reports: {line}" for line in self._github] + self._owners
        self.findings.SetValue("\n".join(said) if said else "No problems found.")

    def selected(self) -> OwnersRow | None:
        index = self.table.GetFirstSelected()
        rows = self.rows()
        return rows[index] if 0 <= index < len(rows) else None

    @staticmethod
    def _fields(pattern: str, owners: Sequence[str]) -> list[Field]:
        return [
            Field(
                "pattern",
                "Path pattern:",
                pattern,
                "* for everything, /docs/ for a folder at the root, *.js for every JavaScript "
                "file, docs/**/*.md for Markdown anywhere under docs.",
            ),
            Field(
                "owners",
                "Owners:",
                " ".join(owners),
                "@person, @organization/team or an email address, separated by spaces. Leave "
                "empty to say nobody owns it.",
            ),
        ]

    def add(self) -> None:
        values = self.ask("Add Rule", self._fields("", ()))
        if values is None:
            return
        self.lines.add_rule(values["pattern"].strip(), values["owners"].replace(",", " ").split())
        self.refresh(len(self.rows()) - 1)

    def edit(self) -> None:
        row = self.selected()
        if row is None:
            return
        values = self.ask("Rule", self._fields(row.pattern, row.owners))
        if values is None:
            return
        self.lines.set_rule(
            row, values["pattern"].strip(), values["owners"].replace(",", " ").split()
        )
        self.refresh(self.table.GetFirstSelected())

    def remove(self) -> None:
        row = self.selected()
        if row is not None:
            index = self.table.GetFirstSelected()
            self.lines.remove_rule(row)
            self._announce(f"Removed the rule for {row.pattern}.")
            self.refresh(index)

    def move(self, delta: int) -> None:
        row = self.selected()
        if row is not None and self.lines.move_rule(row, delta):
            self.refresh(self.table.GetFirstSelected() + delta)

    def check_owners(self) -> None:
        if self._check is None:
            return
        self._announce("Checking the owners with GitHub.")
        self._check(self.lines.text(), self.show_owner_results)

    def show_owner_results(self, results: list[Any]) -> None:
        from quill.core.github.codeowners_check import summary

        if not self.dialog:  # closed while GitHub was answering
            return
        problems = [r for r in results if r.state != "ok"]
        ordered = problems + [r for r in results if r.state == "ok"]
        self._owners = [r.sentence for r in ordered]
        self._show_findings()
        self._announce(summary(results))

    def show_github_problems(self, said: list[str]) -> None:
        if not self.dialog:
            return
        self._github = list(said)
        self._show_findings()
        if said:
            count = len(said)
            self._announce(
                f"GitHub reports {count} problem{'s' if count != 1 else ''} in this file."
            )

    def look_up(self) -> str:
        path = self.path.GetValue().strip()
        if not path:
            return "Type a path first."
        said = who_owns("this file", self.lines.text(), path)
        self.answer.SetLabel(said)
        return said

    def build(self) -> tuple[str | None, str]:
        return self.lines.text(), ""
