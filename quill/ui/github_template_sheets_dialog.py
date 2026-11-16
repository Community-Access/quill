"""Small sheets for the template chooser and three community files (GitHub PRD 21.3, 21.8).

- **Template Chooser**: Allow blank issues, the contact links as a list
  (Add, Edit, Remove, Move Up, Move Down), and the order the templates show
  in. GitHub orders them by file name, so a new order is saved as renames
  with number prefixes ("01-bug.yml"), and the window says so.
- **FUNDING.yml**: one labelled box per sponsor platform.
- **CITATION.cff**: title, version, DOI, release date, message, and the
  authors one per line as "Family, Given".
- **CODEOWNERS**: the rules as text, and Who Owns This Path, which answers
  with the rule that wins, the way GitHub decides.

The models are :mod:`quill.core.github.template_files`'s. Nothing is sent
from here; each window's :attr:`result` is the text to save, and the
Workbench asks before saving.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.core.github.template_builder import TemplateDraftError
from quill.core.github.template_files import (
    FUNDING_PLATFORMS,
    check_chooser,
    dump_chooser,
    dump_citation,
    dump_funding,
    order_renames,
    owners_for,
    parse_chooser,
    parse_citation,
    parse_funding,
)
from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids, show_modal_dialog
from quill.ui.dpi import dip_size

__all__ = ["ChooserDialog", "CitationDialog", "CodeownersDialog", "FundingDialog"]


def _error_text(exc: BaseException) -> str:
    return str(exc.args[0]) if exc.args else str(exc)


class _Sheet:
    """A dialog with Save and Cancel at the bottom; subclasses fill :meth:`body`."""

    title = "Sheet"

    def __init__(self, parent: object, announce: Callable[[str], None] | None) -> None:
        import wx

        self._wx = wx
        self._announce = announce or (lambda _text: None)
        self.result: str | None = None
        self.dialog = wx.Dialog(
            parent, title=self.title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 560, 480))
        self.root = wx.BoxSizer(wx.VERTICAL)
        self.body()
        self.problem = wx.StaticText(self.dialog, label="")
        self.problem.SetName("Sheet problem")
        self.root.Add(self.problem, 0, wx.EXPAND | wx.ALL, 8)
        buttons = wx.StdDialogButtonSizer()
        save = wx.Button(self.dialog, wx.ID_OK, "Save")
        save.SetHelpText("Ask, then commit this file to GitHub.")
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Close without saving anything.")
        buttons.AddButton(save)
        buttons.AddButton(cancel)
        buttons.Realize()
        self.root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(self.root)
        save.Bind(wx.EVT_BUTTON, self._on_save)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

    def body(self) -> None:
        raise NotImplementedError

    def build(self) -> tuple[str | None, str]:
        """``(text to save, "")`` or ``(None, what is wrong)``."""
        raise NotImplementedError

    def text_box(self, label: str, value: str, help_text: str, *, multiline: bool = False) -> Any:
        wx = self._wx
        caption = wx.StaticText(self.dialog, label=label)
        self.root.Add(caption, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        control = wx.TextCtrl(
            self.dialog, value=value, style=wx.TE_MULTILINE | wx.TE_DONTWRAP if multiline else 0
        )
        control.SetName(label.replace("&", "").rstrip(":"))
        control.SetHelpText(help_text)
        self.root.Add(control, 1 if multiline else 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        return control

    def _on_save(self, event: Any) -> None:
        text, problem = self.build()
        if text is None:
            self.problem.SetLabel(problem)
            self._announce(problem)
            return
        self.result = text
        event.Skip()

    def show(self) -> str | None:
        try:
            if show_modal_dialog(self.dialog, self.title) != self._wx.ID_OK:
                return None
            return self.result
        finally:
            self.dialog.Destroy()


class ChooserDialog(_Sheet):
    """config.yml; :attr:`renames` is the order as ``(old, new)`` file names."""

    title = "Template Chooser"

    def __init__(
        self,
        parent: object,
        text: str,
        filenames: Sequence[str],
        *,
        announce: Callable[[str], None] | None = None,
    ) -> None:
        self.config = parse_chooser(text)
        self.order = list(filenames)
        self.renames: list[tuple[str, str]] = []
        super().__init__(parent, announce)

    def body(self) -> None:
        wx = self._wx
        self.blank = wx.CheckBox(self.dialog, label="Allow &blank issues")
        self.blank.SetValue(self.config.blank_issues_enabled)
        self.blank.SetHelpText("Whether people may open an issue without choosing a template.")
        self.root.Add(self.blank, 0, wx.ALL, 8)
        self.links = self._list("&Contact links:", "Links shown under the templates.")
        self._buttons((
            ("&Add Link...", "Add a contact link.", self._on_add),
            ("&Edit Link...", "Change the selected link.", self._on_edit),
            ("&Remove Link", "Remove the selected link.", lambda _e: self.remove_link()),
            ("Move &Up", "Move the selected link up.", lambda _e: self.move_link(-1)),
            ("Move Do&wn", "Move the selected link down.", lambda _e: self.move_link(1)),
        ))
        apply_listbox_activation(self.links, self._on_edit)
        self.templates = self._list(
            "&Order templates appear in:",
            "GitHub lists templates by file name; a new order is saved as numbered names.",
        )
        self._buttons((
            ("Template Soo&ner", "Show it earlier.", lambda _e: self.move(-1)),
            ("Template La&ter", "Show it later.", lambda _e: self.move(1)),
        ))
        self.refresh()

    def _list(self, label: str, help_text: str) -> Any:
        wx = self._wx
        caption = wx.StaticText(self.dialog, label=label)
        self.root.Add(caption, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        box = wx.ListBox(self.dialog, choices=[])
        box.SetName(label.replace("&", "").rstrip(":"))
        box.SetHelpText(help_text)
        self.root.Add(box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        return box

    def _buttons(self, rows: Sequence[tuple[str, str, Callable[[Any], None]]]) -> None:
        wx = self._wx
        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, help_text, handler in rows:
            button = wx.Button(self.dialog, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, handler)
            row.Add(button, 0, wx.RIGHT, 4)
        self.root.Add(row, 0, wx.ALL, 8)

    def refresh(self, link: int = -1, template: int = -1) -> None:
        self.links.Set([
            f"{x['name'] or '(no name)'}: {x['url']}" for x in self.config.contact_links
        ])
        if self.config.contact_links and link >= 0:
            self.links.SetSelection(min(link, len(self.config.contact_links) - 1))
        self.templates.Set(list(self.order))
        if self.order and template >= 0:
            self.templates.SetSelection(min(template, len(self.order) - 1))

    def add_link(self, name: str, url: str, about: str) -> None:
        self.config.contact_links.append({"name": name, "url": url, "about": about})
        self.refresh(len(self.config.contact_links) - 1)

    def remove_link(self) -> None:
        index = self.links.GetSelection()
        if index >= 0:
            del self.config.contact_links[index]
            self.refresh(index)

    def move_link(self, delta: int) -> None:
        index = self.links.GetSelection()
        target = index + delta
        links = self.config.contact_links
        if index < 0 or not 0 <= target < len(links):
            return
        links[index], links[target] = links[target], links[index]
        self.refresh(target)

    def move(self, delta: int) -> None:
        index = self.templates.GetSelection()
        target = index + delta
        if index < 0 or not 0 <= target < len(self.order):
            self._announce("Already at the end.")
            return
        self.order[index], self.order[target] = self.order[target], self.order[index]
        self.refresh(template=target)

    def _ask_link(self, link: dict[str, str]) -> dict[str, str] | None:
        wx = self._wx
        values: dict[str, str] = {}
        for key, prompt in (
            ("name", "The link's name:"),
            ("url", "Its address (https://...):"),
            ("about", "What it is for, in a line:"),
        ):
            with wx.TextEntryDialog(self.dialog, prompt, "Contact Link", link.get(key, "")) as ask:
                ask.SetName(prompt.rstrip(":"))
                if show_modal_dialog(ask, "Contact Link") != wx.ID_OK:
                    return None
                values[key] = str(ask.GetValue()).strip()
        return values

    def _on_add(self, _event: Any) -> None:
        made = self._ask_link({})
        if made is not None:
            self.add_link(made["name"], made["url"], made["about"])

    def _on_edit(self, _event: Any) -> None:
        index = self.links.GetSelection()
        if index < 0:
            return
        made = self._ask_link(self.config.contact_links[index])
        if made is not None:
            self.config.contact_links[index] = made
            self.refresh(index)

    def build(self) -> tuple[str | None, str]:
        self.config.blank_issues_enabled = bool(self.blank.GetValue())
        problems = [p for p in check_chooser(self.config) if p.severity == "error"]
        if problems:
            return None, problems[0].sentence()
        self.renames = order_renames(self.order)
        return dump_chooser(self.config), ""


class FundingDialog(_Sheet):
    title = "Sponsor Platforms (FUNDING.yml)"

    def __init__(
        self, parent: object, text: str, *, announce: Callable[[str], None] | None = None
    ) -> None:
        try:
            self.values = parse_funding(text)
        except TemplateDraftError as exc:
            self.values, self.unreadable = {}, _error_text(exc)
        else:
            self.unreadable = ""
        self.boxes: dict[str, Any] = {}
        super().__init__(parent, announce)

    def body(self) -> None:
        wx = self._wx
        grid = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        grid.AddGrowableCol(1)
        for key, help_text in FUNDING_PLATFORMS:
            caption = wx.StaticText(self.dialog, label=f"{key.replace('_', ' ').title()}:")
            box = wx.TextCtrl(self.dialog, value=self.values.get(key, ""))
            box.SetName(key.replace("_", " ").title())
            box.SetHelpText(help_text + ". Empty leaves the platform out.")
            grid.Add(caption, 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(box, 1, wx.EXPAND)
            self.boxes[key] = box
        self.root.Add(grid, 1, wx.EXPAND | wx.ALL, 8)

    def build(self) -> tuple[str | None, str]:
        if self.unreadable:
            return None, f"{self.unreadable} Edit it as source instead."
        values = dict(self.values)
        values.update({key: box.GetValue() for key, box in self.boxes.items()})
        text = dump_funding(values)
        return (text, "") if text else (None, "Name at least one sponsor platform.")


class CitationDialog(_Sheet):
    title = "How to Cite (CITATION.cff)"

    def __init__(
        self, parent: object, text: str, *, announce: Callable[[str], None] | None = None
    ) -> None:
        try:
            self.fields, self.authors, self.extra = parse_citation(text)
            self.unreadable = ""
        except TemplateDraftError as exc:
            self.fields, self.authors, self.extra = {}, [], {}
            self.unreadable = _error_text(exc)
        super().__init__(parent, announce)

    def body(self) -> None:
        self.boxes = {
            "title": self.text_box("&Title:", self.fields.get("title", ""), "What to cite."),
            "version": self.text_box("&Version:", self.fields.get("version", ""), "Optional."),
            "doi": self.text_box("&DOI:", self.fields.get("doi", ""), "Optional, 10.xxxx/..."),
            "date-released": self.text_box(
                "&Released on:", self.fields.get("date-released", ""), "YYYY-MM-DD. Optional."
            ),
            "message": self.text_box(
                "&Message:",
                self.fields.get("message", "") or "If you use this, please cite it.",
                "What GitHub shows above the citation.",
            ),
        }
        self.people = self.text_box(
            "&Authors, one per line:",
            "\n".join(self.authors),
            'One author per line, as "Family, Given", or an organization name alone.',
            multiline=True,
        )

    def build(self) -> tuple[str | None, str]:
        if self.unreadable:
            return None, f"{self.unreadable} Edit it as source instead."
        fields = {key: box.GetValue() for key, box in self.boxes.items()}
        authors = [line for line in self.people.GetValue().splitlines() if line.strip()]
        if not fields["title"].strip() or not authors:
            return None, "A citation needs a title and at least one author."
        return dump_citation(fields, authors, self.extra), ""


class CodeownersDialog(_Sheet):
    title = "Code Owners (CODEOWNERS)"

    def __init__(
        self,
        parent: object,
        text: str,
        *,
        announce: Callable[[str], None] | None = None,
        check: Callable[[str, Callable[[list[Any]], None]], None] | None = None,
    ) -> None:
        self.text = text
        #: Starts the owner check in the background and calls back with the
        #: results (PRD 21.8); None where there is no repository to ask.
        self._check = check
        super().__init__(parent, announce)

    def body(self) -> None:
        wx = self._wx
        self.rules = self.text_box(
            "&Rules, one per line:",
            self.text,
            "A path pattern, then its owners (@person, @org/team or an email). "
            "Lines starting with # are notes. The last matching rule wins.",
            multiline=True,
        )
        self.path = self.text_box(
            "&Who owns this path:", "", "Type a path, such as docs/guide.md, then Look Up."
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
                wx.StaticText(self.dialog, label="What the check &found:"),
                0,
                wx.LEFT | wx.RIGHT,
                8,
            )
            self.findings = wx.TextCtrl(
                self.dialog, value="", style=wx.TE_MULTILINE | wx.TE_READONLY
            )
            self.findings.SetName("What the owner check found")
            self.findings.SetHelpText(
                "One line for each owner: whether it exists and can write, what to "
                "fix if not, and any that could not be checked."
            )
            self.root.Add(self.findings, 1, wx.EXPAND | wx.ALL, 8)

    def check_owners(self) -> None:
        if self._check is None:
            return
        self._announce("Checking the owners with GitHub.")
        self._check(self.rules.GetValue(), self.show_findings)

    def show_findings(self, results: list[Any]) -> None:
        from quill.core.github.codeowners_check import summary

        if not self.dialog:  # closed while GitHub was answering
            return
        problems = [r for r in results if r.state != "ok"]
        ordered = problems + [r for r in results if r.state == "ok"]
        self.findings.SetValue("\n".join(r.sentence for r in ordered))
        self._announce(summary(results))

    def look_up(self) -> str:
        path = self.path.GetValue().strip()
        if not path:
            return "Type a path first."
        rule = owners_for(self.rules.GetValue(), path)
        if rule is None:
            said = f"No rule owns {path}; nobody is asked to review it."
        elif not rule.owners:
            said = f"Line {rule.line}, {rule.pattern}, owns {path} with no owners."
        else:
            said = f"Line {rule.line}, {rule.pattern}: {', '.join(rule.owners)} own {path}."
        self.answer.SetLabel(said)
        return said

    def build(self) -> tuple[str | None, str]:
        text = self.rules.GetValue()
        return (text if text.endswith("\n") else text + "\n"), ""
