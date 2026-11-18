"""An organization's roles and rulesets, in two windows (GitHub PRD 18.3.1 and 18.6).

Opened from an organization's row in the GitHub Workbench: **Roles...** and
**Rulesets...**. The GitHub work is in :mod:`quill.core.github.org_admin`.

* **Roles in <org>.** The organization's roles; choosing one lists who holds
  it, each row starting with "Person:" or "Team:" and saying when the role
  comes through a team. Give to Person (Alt+P), Give to Team (Alt+T), and Take
  Away (Alt+A), which asks whether to take this role or every role.
* **Rulesets in <org>.** The organization's rulesets; choosing one reads it in
  plain words in Details. Enforcement (Alt+E) chooses Active, Evaluate or
  Disabled; History (Alt+H) and Rule Insights (Alt+I) fill Details with its
  changes and the pushes it judged; Delete (Alt+L) asks for the name typed.

Every change runs off the UI thread and is read back from GitHub before the
window says it happened.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.org_admin import (
    ENFORCEMENTS,
    INSIGHT_PERIODS,
    GitHubOrgAdmin,
    Holder,
    Role,
    RulesetRow,
)
from quill.ui.dialog_contract import (
    apply_modal_ids,
    bind_close_button,
    dialog_alive,
    show_modal_dialog,
)
from quill.ui.dpi import dip_size

__all__ = ["OrgRolesDialog", "OrgRulesetsDialog"]


class _OrgWindow:
    """What both windows share: a status line, asking, and work off the UI thread."""

    def __init__(
        self,
        parent: object,
        api: GitHubOrgAdmin,
        org: str,
        dialog: Any,
        announce_cb: Callable[[str], None] | None,
        ask_text: Callable[[str, str], str | None] | None,
        confirm: Callable[[str, str], bool] | None,
        choose: Callable[[str, str, list[str]], int] | None,
    ) -> None:
        import wx

        self._wx = wx
        self._api = api
        self._org = org
        self._announce = announce_cb or (lambda _message: None)
        self._ask_text = ask_text or self._default_ask
        self._confirm = confirm or self._default_confirm
        self._choose = choose or self._default_choose
        self._busy = False
        self.dialog = dialog
        self.dialog.SetMinSize(dip_size(self.dialog, 520, 400))
        self.panel = wx.Panel(self.dialog)
        self.root = wx.BoxSizer(wx.VERTICAL)

    def _finish(self, buttons: list[Any], status_name: str) -> None:
        wx = self._wx
        row = wx.BoxSizer(wx.HORIZONTAL)
        for button in buttons:
            row.Add(button, 0, wx.RIGHT, 6)
        row.AddStretchSpacer()
        close = wx.Button(self.panel, wx.ID_CANCEL, "Close")
        close.SetHelpText("Closes this window. Every change has already been sent.")
        row.Add(close)
        self.root.Add(row, 0, wx.EXPAND | wx.ALL, 8)
        self._status = wx.StaticText(self.panel, label="")
        self._status.SetName(status_name)
        self.root.Add(self._status, 0, wx.EXPAND | wx.ALL, 8)
        self.panel.SetSizer(self.root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(self.panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.SetSize(dip_size(self.dialog, 640, 480))
        bind_close_button(self.dialog, close, modeless=False)

    def _say(self, message: str) -> None:
        self._status.SetLabel(message)
        self._announce(message)

    def _default_ask(self, title: str, prompt: str) -> str | None:
        wx = self._wx
        box = wx.TextEntryDialog(self.dialog, prompt, title)
        try:
            return str(box.GetValue()) if show_modal_dialog(box, title) == wx.ID_OK else None
        finally:
            box.Destroy()

    def _default_confirm(self, title: str, message: str) -> bool:
        wx = self._wx
        box = wx.MessageDialog(
            self.dialog, message, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION
        )
        try:
            return bool(show_modal_dialog(box, title) == wx.ID_YES)
        finally:
            box.Destroy()

    def _default_choose(self, title: str, prompt: str, labels: list[str]) -> int:
        wx = self._wx
        box = wx.SingleChoiceDialog(self.dialog, prompt, title, labels)
        try:
            return int(box.GetSelection()) if show_modal_dialog(box, title) == wx.ID_OK else -1
        finally:
            box.Destroy()

    def _run(self, doing: str, work: Callable[[], Any], done: Callable[[Any], None]) -> None:
        """Do *work* off the UI thread, then hand its result to *done* on it."""
        if self._busy:
            self._say("Wait for the last change to finish.")
            return
        self._busy = True
        self._status.SetLabel(doing)

        def worker() -> None:
            result: Any
            try:
                result = work()
            except GitHubItemsError as exc:
                result = exc
            except Exception as exc:  # noqa: BLE001 - say any failure
                result = GitHubItemsError(f"That did not work: {exc}")
            self._wx.CallAfter(self._done, result, done)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: GitHub write.

    def _done(self, result: Any, done: Callable[[Any], None]) -> None:
        if not dialog_alive(self.dialog):
            return
        self._busy = False
        if isinstance(result, GitHubItemsError):
            self._say(str(result.args[0]) if result.args else str(result))
            return
        done(result)


class OrgRolesDialog(_OrgWindow):
    """Who holds each organization role, with give and take away."""

    def __init__(
        self,
        parent: object,
        api: GitHubOrgAdmin,
        *,
        org: str,
        roles: list[Role],
        announce_cb: Callable[[str], None] | None = None,
        ask_text: Callable[[str, str], str | None] | None = None,
        confirm: Callable[[str, str], bool] | None = None,
        choose: Callable[[str, str, list[str]], int] | None = None,
    ) -> None:
        import wx

        dialog = wx.Dialog(
            parent, title=f"Roles in {org}", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        super().__init__(parent, api, org, dialog, announce_cb, ask_text, confirm, choose)
        self._roles = roles
        self._holders: list[Holder] = []
        panel, root = self.panel, self.root
        root.Add(wx.StaticText(panel, label="R&oles:"), 0, wx.LEFT | wx.TOP, 8)
        self._role_list = wx.ListBox(panel, choices=[r.label() for r in roles] or ["No roles."])
        self._role_list.SetName("Roles")
        self._role_list.SetHelpText(
            "The organization's roles. Choose one to hear who holds it, in the list below."
        )
        root.Add(self._role_list, 1, wx.EXPAND | wx.ALL, 8)
        root.Add(wx.StaticText(panel, label="&Who holds it:"), 0, wx.LEFT, 8)
        self._holder_list = wx.ListBox(panel, choices=[])
        self._holder_list.SetName("Who holds it")
        self._holder_list.SetHelpText(
            "The people and teams holding the chosen role. A person who holds it through a "
            "team says which team; take it from the team to take it from them."
        )
        root.Add(self._holder_list, 1, wx.EXPAND | wx.ALL, 8)
        self._give_person = wx.Button(panel, label="Give to &Person...")
        self._give_person.SetHelpText("Gives the chosen role to a person, by GitHub username.")
        self._give_team = wx.Button(panel, label="Give to &Team...")
        self._give_team.SetHelpText("Gives the chosen role to a team, by the team's short name.")
        self._take = wx.Button(panel, label="T&ake Away...")
        self._take.SetHelpText(
            "Takes the chosen role, or every organization role, from the selected person or team."
        )
        self._finish([self._give_person, self._give_team, self._take], "Roles status")
        self._role_list.Bind(wx.EVT_LISTBOX, lambda _e: self.load_holders())
        self._give_person.Bind(wx.EVT_BUTTON, lambda _e: self.give("person"))
        self._give_team.Bind(wx.EVT_BUTTON, lambda _e: self.give("team"))
        self._take.Bind(wx.EVT_BUTTON, lambda _e: self.take_away())
        if roles:
            self._role_list.SetSelection(0)
            self.load_holders()
        self._role_list.SetFocus()

    def show(self) -> None:
        wx = self._wx
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_CANCEL,
            affirmative_label="Close",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
            escape_id=wx.ID_CANCEL,
        )
        try:
            show_modal_dialog(self.dialog, self.dialog.GetTitle(), announce=self._announce)
        finally:
            self.dialog.Destroy()

    def _role(self) -> Role | None:
        index = self._role_list.GetSelection()
        return self._roles[index] if 0 <= index < len(self._roles) else None

    def _show_holders(self, role: Role, holders: list[Holder], said: str = "") -> None:
        self._holders = holders
        self._holder_list.Set([h.label() for h in holders] or ["Nobody holds this role."])
        self._say(said or f"{role.name}: {len(holders)} holding it.")

    def load_holders(self) -> None:
        role = self._role()
        if role is None:
            return
        self._run(
            f"Reading who holds {role.name}...",
            lambda: self._api.holders(self._org, role),
            lambda holders: self._show_holders(role, holders),
        )

    def give(self, kind: str) -> None:
        role = self._role()
        if role is None:
            self._say("Choose a role first.")
            return
        what = "username" if kind == "person" else "team's short name"
        name = (self._ask_text("Give Role", f"Give {role.name} to (the {what}):") or "").strip()
        if not name:
            return

        def work() -> list[Holder]:
            self._api.assign(self._org, kind, name, role)
            return self._api.holders(self._org, role)

        self._run(
            "Giving the role...",
            work,
            lambda holders: self._show_holders(role, holders, f"{name} now has {role.name}."),
        )

    def take_away(self) -> None:
        role = self._role()
        index = self._holder_list.GetSelection()
        if role is None or not 0 <= index < len(self._holders):
            self._say("Select a person or team in Who holds it first.")
            return
        holder = self._holders[index]
        if holder.how == "indirect":
            self._say(
                f"{holder.name} holds {role.name} through {', '.join(holder.through)}; "
                "take it from that team instead."
            )
            return
        which = self._choose(
            "Take Away",
            f"What should {holder.name} lose?",
            [f"Only {role.name}", "Every organization role"],
        )
        if which < 0:
            return

        def work() -> list[Holder]:
            if which == 0:
                self._api.unassign(self._org, holder.kind, holder.name, role)
            else:
                self._api.unassign_all(self._org, holder.kind, holder.name)
            return self._api.holders(self._org, role)

        said = (
            f"{holder.name} no longer has {role.name}."
            if which == 0
            else f"{holder.name} no longer has any organization role."
        )
        self._run("Taking the role away...", work, lambda h: self._show_holders(role, h, said))


class OrgRulesetsDialog(_OrgWindow):
    """The organization's rulesets, read in words, with enforcement, history and delete."""

    def __init__(
        self,
        parent: object,
        api: GitHubOrgAdmin,
        *,
        org: str,
        rulesets: list[RulesetRow],
        announce_cb: Callable[[str], None] | None = None,
        ask_text: Callable[[str, str], str | None] | None = None,
        confirm: Callable[[str, str], bool] | None = None,
        choose: Callable[[str, str, list[str]], int] | None = None,
    ) -> None:
        import wx

        dialog = wx.Dialog(
            parent, title=f"Rulesets in {org}", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        super().__init__(parent, api, org, dialog, announce_cb, ask_text, confirm, choose)
        self._rulesets = rulesets
        panel, root = self.panel, self.root
        root.Add(wx.StaticText(panel, label="R&ulesets:"), 0, wx.LEFT | wx.TOP, 8)
        self._list = wx.ListBox(panel, choices=[])
        self._list.SetName("Rulesets")
        self._list.SetHelpText(
            "The organization's rulesets, each with its enforcement. Choose one to read it "
            "in plain words in Details."
        )
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 8)
        root.Add(wx.StaticText(panel, label="&Details:"), 0, wx.LEFT, 8)
        self._details = wx.ListBox(panel, choices=[])
        self._details.SetName("Details")
        self._details.SetHelpText(
            "The chosen ruleset in plain words, or its history, or the pushes it judged."
        )
        root.Add(self._details, 1, wx.EXPAND | wx.ALL, 8)
        self._enforce = wx.Button(panel, label="&Enforcement...")
        self._enforce.SetHelpText(
            "Makes the ruleset Active, Evaluate (it reports what it would block and blocks "
            "nothing) or Disabled."
        )
        self._history = wx.Button(panel, label="&History")
        self._history.SetHelpText("Lists the ruleset's changes, newest first, in Details.")
        self._insights = wx.Button(panel, label="Rule &Insights...")
        self._insights.SetHelpText(
            "Lists recent pushes the organization's rulesets passed, blocked or let through "
            "on a bypass, for the day, week or month."
        )
        self._delete = wx.Button(panel, label="De&lete...")
        self._delete.SetHelpText(
            "Deletes the ruleset across every repository it covers. You type its name to confirm."
        )
        self._finish(
            [self._enforce, self._history, self._insights, self._delete], "Rulesets status"
        )
        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self.read_selected())
        self._enforce.Bind(wx.EVT_BUTTON, lambda _e: self.change_enforcement())
        self._history.Bind(wx.EVT_BUTTON, lambda _e: self.show_history())
        self._insights.Bind(wx.EVT_BUTTON, lambda _e: self.show_insights())
        self._delete.Bind(wx.EVT_BUTTON, lambda _e: self.delete_selected())
        self._fill()
        self._list.SetFocus()

    def show(self) -> None:
        wx = self._wx
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_CANCEL,
            affirmative_label="Close",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
            escape_id=wx.ID_CANCEL,
        )
        try:
            show_modal_dialog(self.dialog, self.dialog.GetTitle(), announce=self._announce)
        finally:
            self.dialog.Destroy()

    def _fill(self) -> None:
        self._list.Set([r.label() for r in self._rulesets] or ["No rulesets."])
        if self._rulesets:
            self._list.SetSelection(0)
            self.read_selected()

    def _ruleset(self) -> RulesetRow | None:
        index = self._list.GetSelection()
        return self._rulesets[index] if 0 <= index < len(self._rulesets) else None

    def _show_details(self, lines: list[str], said: str) -> None:
        self._details.Set(lines or ["Nothing to show."])
        self._say(said)

    def _reloaded(self, rulesets: list[RulesetRow], said: str) -> None:
        self._rulesets = rulesets
        self._details.Set([])
        self._list.Set([r.label() for r in rulesets] or ["No rulesets."])
        if rulesets:
            self._list.SetSelection(0)
        self._say(said)

    def read_selected(self) -> None:
        ruleset = self._ruleset()
        if ruleset is None:
            return
        self._run(
            f"Reading {ruleset.name}...",
            lambda: self._api.ruleset_summary(self._org, ruleset),
            lambda text: self._show_details([text], f"{ruleset.name} read into Details."),
        )

    def change_enforcement(self) -> None:
        ruleset = self._ruleset()
        if ruleset is None:
            self._say("Choose a ruleset first.")
            return
        which = self._choose(
            "Enforcement", f"How should {ruleset.name} be enforced?", [w for _c, w in ENFORCEMENTS]
        )
        if which < 0:
            return
        code, words = ENFORCEMENTS[which]

        def work() -> list[RulesetRow]:
            self._api.set_enforcement(self._org, ruleset, code)
            return self._api.rulesets(self._org)

        said = f"{ruleset.name} is now {words.split(':', 1)[0]}."
        self._run("Changing the enforcement...", work, lambda rows: self._reloaded(rows, said))

    def show_history(self) -> None:
        ruleset = self._ruleset()
        if ruleset is None:
            self._say("Choose a ruleset first.")
            return
        self._run(
            "Reading the history...",
            lambda: self._api.history(self._org, ruleset),
            lambda lines: self._show_details(lines, f"{len(lines)} versions of {ruleset.name}."),
        )

    def show_insights(self) -> None:
        which = self._choose("Rule Insights", "Show pushes from:", [w for _c, w in INSIGHT_PERIODS])
        if which < 0:
            return
        period = INSIGHT_PERIODS[which][0]
        self._run(
            "Reading rule insights...",
            lambda: self._api.insights(self._org, period),
            lambda lines: self._show_details(lines, f"{len(lines)} pushes judged."),
        )

    def delete_selected(self) -> None:
        ruleset = self._ruleset()
        if ruleset is None:
            self._say("Choose a ruleset first.")
            return
        typed = self._ask_text(
            "Delete Ruleset",
            f"Deleting {ruleset.name} removes its rules from every repository it covers, "
            "and cannot be undone. Type its name to delete it:",
        )
        if typed is None:
            return
        if typed.strip() != ruleset.name:
            self._say("That is not the ruleset's name, so nothing was deleted.")
            return

        def work() -> list[RulesetRow]:
            self._api.delete_ruleset(self._org, ruleset)
            return self._api.rulesets(self._org)

        said = f"{ruleset.name} deleted."
        self._run("Deleting the ruleset...", work, lambda rows: self._reloaded(rows, said))
