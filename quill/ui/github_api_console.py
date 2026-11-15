"""Tools > GitHub API Console in the GitHub Workbench (PRD 22.2, GH-C).

Any GitHub REST request, or any GraphQL query or mutation, through the
Workbench's one door (:class:`quill.core.github.workbench_api.TokenApi`). The
Path box completes from QUILL's vendored copy of GitHub's API description
(Down Arrow lists the matches, with the values already typed kept); the
"What it does" line names the operation, its risk tier and the token scope it
needs, before anything is sent. A read goes at once. A write (any method but
GET, or a GraphQL mutation) needs Full access for this account in the
Workbench and the method typed to confirm (MUTATION for GraphQL), and goes to
Change History. The answer is a tree: each field or list item a node, so it
reads by arrow keys; Copy Value, Copy Path and Export JSON work on it, and a
request can be saved by name and run again later (per account, on this
device).

Modal, through the dialog contract; Close carries no access key and is bound
with bind_close_button. Only outcomes are spoken (GATE-13). The wx-free half
is :mod:`quill.core.github.api_console`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import wx

from quill.core.github.api_console import (
    METHODS,
    AnswerNode,
    ConsoleCommand,
    SavedCommands,
    answer_tree,
    complete_path,
    confirmation_word,
    explain,
    export_json,
    find_operation,
    is_write,
    load_operations,
    parse_body,
)
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button, show_modal_dialog
from quill.ui.dpi import dip_size

__all__ = ["GitHubApiConsole"]


def _labelled(parent: Any, sizer: Any, label: str, control: Any, *, grow: int = 0) -> None:
    text = wx.StaticText(parent, label=label)
    sizer.Add(text, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
    sizer.Add(control, grow, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)


class GitHubApiConsole:
    """The console over one Workbench provider (for its API, account and voice)."""

    def __init__(self, provider: Any, repository: str = "") -> None:
        self.provider = provider
        self.operations = load_operations()
        self.answer: Any = None
        self._nodes: dict[Any, AnswerNode] = {}
        self.account = str(provider.account_name() or "")
        parent = provider.frame.frame if provider.frame is not None else None
        self.dialog = wx.Dialog(
            parent, title="GitHub API Console", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        dialog = self.dialog
        dialog.SetSize(dip_size(dialog, 760, 680))
        dialog.SetHelpText(
            "Send any GitHub REST request or GraphQL query. What it does and what it needs is "
            "said before you send; a read goes at once, a write needs Full access and the "
            "method typed to confirm. The answer is a tree below."
        )
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.method = wx.Choice(dialog, choices=list(METHODS))
        self.method.SetSelection(0)
        self.method.SetHelpText(
            "GET reads; POST, PUT and PATCH change; DELETE removes. GRAPHQL sends the Body box "
            "as a GraphQL document, with the Variables box as its variables."
        )
        self.method.Bind(wx.EVT_CHOICE, lambda _e: self.refresh())
        _labelled(dialog, sizer, "&Method:", self.method)
        start = f"/repos/{repository}" if repository else "/user"
        self.path = wx.ComboBox(dialog, value=start, choices=[])
        self.path.SetHelpText(
            "The request path, such as /repos/owner/name/issues. Type part of it and press "
            "Down Arrow for the matching operations from GitHub's API description; a name in "
            "braces is a value you type in its place. Add ?name=value for a query."
        )
        self.path.Bind(wx.EVT_TEXT, lambda _e: self.refresh(complete=True))
        _labelled(dialog, sizer, "&Path:", self.path)
        self.body = wx.TextCtrl(dialog, style=wx.TE_MULTILINE)
        self.body.SetMinSize(dip_size(dialog, 420, 70))
        self.body.SetHelpText(
            "For a write, the body: a JSON object or one name=value a line. For GRAPHQL, the "
            "query or mutation itself."
        )
        self.body.Bind(wx.EVT_TEXT, lambda _e: self.refresh())
        _labelled(dialog, sizer, "B&ody or GraphQL:", self.body)
        self.variables = wx.TextCtrl(dialog, style=wx.TE_MULTILINE)
        self.variables.SetMinSize(dip_size(dialog, 420, 40))
        self.variables.SetHelpText("GraphQL variables as a JSON object. Not used for REST.")
        _labelled(dialog, sizer, "&Variables:", self.variables)
        self.explanation = wx.TextCtrl(dialog, style=wx.TE_READONLY | wx.TE_MULTILINE)
        self.explanation.SetMinSize(dip_size(dialog, 420, 50))
        self.explanation.SetHelpText(
            "What the request does, how risky it is, the token scope it needs and how it is "
            "confirmed, from GitHub's API description."
        )
        _labelled(dialog, sizer, "&What it does:", self.explanation)
        self.tree = wx.TreeCtrl(dialog, style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT)
        self.tree.SetMinSize(dip_size(dialog, 420, 220))
        self.tree.SetHelpText(
            "GitHub's answer as a tree: Right Arrow opens a field or list, Left Arrow closes "
            "it. Copy Value and Copy Path work on the selected node."
        )
        _labelled(dialog, sizer, "&Answer:", self.tree, grow=1)
        buttons = wx.WrapSizer(wx.HORIZONTAL)
        rows = (
            ("&Send", "Send the request. A write asks you to type the method first.", self.send),
            ("&Copy Value", "Copy the selected node's value.", self.copy_value),
            (
                "Copy Pa&th",
                "Copy the selected node's JSON path, such as $.items[0].title.",
                self.copy_path,
            ),
            ("&Export JSON...", "Save the whole answer as a JSON file.", self.export),
            ("Save Comma&nd...", "Save this request by name, for this account.", self.save_command),
            (
                "Saved Comman&ds...",
                "Choose a saved request to fill the console with it.",
                self.load_command,
            ),
        )
        for label, help_text, handler in rows:
            button = wx.Button(dialog, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, h=handler: h())
            if handler is self.send:
                button.SetDefault()
            buttons.Add(button, 0, wx.ALL, 4)
        close = wx.Button(dialog, wx.ID_CANCEL, "Close")
        close.SetHelpText("Close the console. Escape does the same.")
        bind_close_button(dialog, close, modeless=False)
        buttons.Add(close, 0, wx.ALL, 4)
        sizer.Add(buttons, 0, wx.ALL, 4)
        dialog.SetSizer(sizer)
        apply_modal_ids(dialog)
        dialog.SetEscapeId(wx.ID_CANCEL)
        self.refresh()

    # -- the request ---------------------------------------------------------------

    def chosen_method(self) -> str:
        return METHODS[max(0, self.method.GetSelection())]

    def refresh(self, *, complete: bool = False) -> None:
        method, path = self.chosen_method(), self.path.GetValue().strip()
        operation = find_operation(method, path, self.operations) if method != "GRAPHQL" else None
        self.explanation.ChangeValue(
            explain(method, path, operation, query_text=self.body.GetValue())
        )
        if complete and method != "GRAPHQL":
            matches = complete_path(path, self.operations, method)
            if matches and matches != list(self.path.GetStrings()):
                at = self.path.GetInsertionPoint()
                self.path.Set(matches)
                self.path.ChangeValue(path)
                self.path.SetInsertionPoint(at)

    def _split_query(self, path: str) -> tuple[str, dict[str, str]]:
        from urllib.parse import parse_qsl

        bare, _, query = path.partition("?")
        return bare, dict(parse_qsl(query))

    def _allowed_to_write(self, method: str) -> bool:
        from quill.core.github.permissions import AccessLevel

        level = self.provider.access_level()
        if level is not AccessLevel.FULL:
            self.provider._say(
                f"Writes from the console need Full access; this account is {level.label} in "
                "the Workbench. Account, Roles and Access, Workbench Level changes it."
            )
            return False
        word = confirmation_word(method)
        with wx.TextEntryDialog(
            self.dialog,
            f"{self.explanation.GetValue()}\n\nType {word} to send it.",
            "Confirm GitHub API Write",
        ) as ask:
            ask.SetName(f"Type {word} to send it")
            if show_modal_dialog(ask, "Confirm GitHub API Write") != wx.ID_OK:
                return False
            if ask.GetValue().strip().upper() != word:
                self.provider._say(f"Not sent: type {word} exactly to send a write.")
                return False
        return True

    def send(self) -> None:
        method, path = self.chosen_method(), self.path.GetValue().strip()
        text = self.body.GetValue()
        try:
            if method == "GRAPHQL":
                if not text.strip():
                    self.provider._say("Type a GraphQL query in the Body box first.")
                    return
                raw_vars = self.variables.GetValue().strip()
                variables = json.loads(raw_vars) if raw_vars else {}
                if not isinstance(variables, dict):
                    raise ValueError("The variables must be a JSON object.")
                body: dict[str, Any] = {}
            else:
                if not path.startswith("/"):
                    self.provider._say("Type a path that starts with a slash, such as /user.")
                    return
                body = parse_body(text) if method != "GET" else {}
                variables = {}
        except (ValueError, json.JSONDecodeError) as exc:
            self.provider._say(str(exc))
            return
        writes = is_write(method, text)
        if writes and not self._allowed_to_write(method):
            return
        api = self.provider.github_api()
        bare, query = self._split_query(path)

        def work() -> Any:
            if method == "GRAPHQL":
                return api.graphql(text, variables)
            reply = api.rest(method, bare, body=body or None, query=query or None)
            return reply.data if reply.data is not None else {"status": reply.status}

        def done(answer: Any) -> None:
            self.show_answer(answer)
            target = "GraphQL" if method == "GRAPHQL" else f"{method} {bare}"
            if writes:
                self._record(method, target)
            self.provider._say(f"{target}: answered.")

        def failed(error: BaseException) -> None:
            self.provider._say(f"GitHub did not accept it: {error}")

        self.provider.frame._run_background("GitHub API Console", work, done, failed)

    def _record(self, method: str, target: str) -> None:
        from quill.core.github.change_log import ChangeLog

        try:
            ChangeLog.load().record(
                account=self.account,
                kind="api_console",
                ident={"method": method},
                target=target,
                summary="sent from the GitHub API Console",
                changes=(),
                tier=3,
                confirmed=True,
                can_undo=False,
            )
        except OSError:
            self.provider._say("Sent, but Change History could not be written.")

    # -- the answer ----------------------------------------------------------------

    def show_answer(self, answer: Any) -> None:
        self.answer = answer
        tree = self.tree
        tree.DeleteAllItems()
        self._nodes = {}
        root = tree.AddRoot("Answer")
        node = answer_tree(answer)

        def add(parent: Any, item: AnswerNode) -> Any:
            added = tree.AppendItem(parent, item.label)
            self._nodes[added] = item
            for child in item.children:
                add(added, child)
            return added

        top = add(root, node)
        tree.Expand(top)
        tree.SelectItem(top)

    def selected_node(self) -> AnswerNode | None:
        item = self.tree.GetSelection()
        return self._nodes.get(item) if item and item.IsOk() else None

    def _copy(self, text: str, what: str) -> None:
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
            finally:
                wx.TheClipboard.Close()
            self.provider._say(f"{what} copied.")

    def copy_value(self) -> None:
        node = self.selected_node()
        if node is None:
            self.provider._say("There is no answer yet.")
            return
        self._copy(node.value_text(), "Value")

    def copy_path(self) -> None:
        node = self.selected_node()
        if node is None:
            self.provider._say("There is no answer yet.")
            return
        self._copy(node.path, "Path")

    def export(self) -> None:
        if self.answer is None:
            self.provider._say("There is no answer yet.")
            return
        with wx.FileDialog(
            self.dialog,
            "Export JSON",
            defaultFile="github-answer.json",
            wildcard="JSON files (*.json)|*.json",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as chooser:
            if show_modal_dialog(chooser, "Export JSON") != wx.ID_OK:
                return
            target = Path(chooser.GetPath())
        try:
            target.write_text(export_json(self.answer), encoding="utf-8", newline="\n")
        except OSError as exc:
            self.provider._say(f"Could not save {target.name}: {exc}")
            return
        self.provider._say(f"Saved {target.name}.")

    # -- saved commands ------------------------------------------------------------

    def save_command(self) -> None:
        with wx.TextEntryDialog(self.dialog, "A name for this request:", "Save Command") as ask:
            ask.SetName("A name for this request")
            if show_modal_dialog(ask, "Save Command") != wx.ID_OK:
                return
            name = ask.GetValue().strip()
        if not name:
            return
        saved = SavedCommands.load(self.account)
        saved.put(
            ConsoleCommand(
                name, self.chosen_method(), self.path.GetValue().strip(), self.body.GetValue()
            )
        )
        saved.save()
        self.provider._say(f"Saved {name}.")

    def load_command(self) -> None:
        saved = SavedCommands.load(self.account)
        if not saved.commands:
            self.provider._say("No saved requests yet. Save Command saves this one.")
            return
        labels = [f"{c.name}: {c.method} {c.path}".strip() for c in saved.commands]
        with wx.SingleChoiceDialog(
            self.dialog, "Fill the console with:", "Saved Commands", labels
        ) as chooser:
            chooser.SetName("Saved Commands")
            if show_modal_dialog(chooser, "Saved Commands") != wx.ID_OK:
                return
            command = saved.commands[chooser.GetSelection()]
        self.fill(command)

    def fill(self, command: ConsoleCommand) -> None:
        self.method.SetSelection(METHODS.index(command.method))
        self.path.ChangeValue(command.path)
        self.body.ChangeValue(command.body)
        self.refresh()

    def show(self) -> int:
        try:
            return int(show_modal_dialog(self.dialog, self.dialog.GetTitle()))
        finally:
            self.dialog.Destroy()
