"""Tools > REST Console in the WordPress Workbench (PRD 15.9, W7).

Any route on the current site, the guarantee behind "anything WordPress can
do": the Route box completes from the site's own index (Down Arrow lists the
matches), the Method choice, the parameters or body as ``name=value`` lines
or JSON, and a read-only line naming the capability the request needs. Send
reads at once; a write first shows a preview naming the site, the method and
the route, and goes to the Workbench's Change History. The answer is a tree:
each field or list item a node, values in the labels, so it reads by arrow
keys rather than as a wall of JSON (Copy Answer copies the JSON).

Modal, through the dialog contract; OK and Cancel carry no access keys, and
Close is bound with bind_close_button. Only the outcome is spoken (GATE-13).
"""

from __future__ import annotations

import json
from typing import Any

import wx

from quill.core.wordpress.workbench_io import (
    answer_tree,
    complete_route,
    needed_capability,
    parse_params,
)
from quill.core.workbench.history import Change
from quill.ui import wordpress_workbench_dialogs as wdlg
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button
from quill.ui.dpi import dip_size
from quill.ui.spoken_name import set_spoken_name
from quill.ui.wordpress_dialogs import labelled_row

__all__ = ["METHODS", "RestConsole"]

METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")


class RestConsole:
    """The console for one site."""

    def __init__(self, provider: Any, site: str, ctx: Any) -> None:
        self.provider = provider
        self.site = site
        self.ctx = ctx
        self.routes = list(ctx.info.routes) if ctx.info is not None else []
        self.answer: Any = None
        self.dialog = wx.Dialog(
            provider.parent,
            title=f"REST Console - {site}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize(dip_size(self.dialog, 720, 620))
        self.dialog.SetHelpText(
            "Send any request to the site's REST API. Reads go at once; a write shows a "
            "preview first and goes to Change History. The answer is a tree below."
        )
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.route = wx.ComboBox(self.dialog, choices=complete_route("", self.routes))
        self.route.SetHelpText(
            "The route, such as wp/v2/posts. Type part of it and press Down Arrow for the "
            "site's own routes that match; a value in the address, such as a number, you "
            "type in its place."
        )
        self.route.Bind(wx.EVT_TEXT, self._on_route)
        labelled_row(sizer, self.dialog, "&Route:", self.route)
        self.method = wx.Choice(self.dialog, choices=list(METHODS))
        self.method.SetSelection(0)
        self.method.SetHelpText("GET reads; POST, PUT and PATCH change; DELETE removes.")
        self.method.Bind(wx.EVT_CHOICE, lambda _e: self._on_route(None))
        labelled_row(sizer, self.dialog, "&Method:", self.method)
        self.params = wx.TextCtrl(self.dialog, style=wx.TE_MULTILINE)
        self.params.SetMinSize(dip_size(self.dialog, 420, 80))
        self.params.SetHelpText(
            "One name=value a line, or a JSON object. For GET they are the query; for a "
            "write they are the body."
        )
        labelled_row(sizer, self.dialog, "&Parameters or body:", self.params)
        self.needs = wx.TextCtrl(self.dialog, style=wx.TE_READONLY)
        self.needs.SetHelpText("The capability WordPress checks for this request.")
        labelled_row(sizer, self.dialog, "&Needs:", self.needs)
        self.tree = wx.TreeCtrl(self.dialog, style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT)
        set_spoken_name(self.tree, "Answer")
        self.tree.SetMinSize(dip_size(self.dialog, 420, 240))
        self.tree.SetHelpText(
            "The site's answer as a tree: Right Arrow opens a field or list, Left Arrow closes it."
        )
        labelled_row(sizer, self.dialog, "&Answer:", self.tree)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        send = wx.Button(self.dialog, label="&Send")
        send.SetHelpText("Send the request. A write shows a preview first.")
        send.Bind(wx.EVT_BUTTON, lambda _e: self.send())
        send.SetDefault()
        copy = wx.Button(self.dialog, label="Copy &JSON")
        copy.SetHelpText("Copy the answer as JSON.")
        copy.Bind(wx.EVT_BUTTON, lambda _e: self._copy())
        close = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close.SetHelpText("Close the console. Escape does the same.")
        bind_close_button(self.dialog, close, modeless=False)
        for button in (send, copy, close):
            buttons.Add(button, 0, wx.RIGHT, 8)
        sizer.Add(buttons, 0, wx.ALL, 8)
        self.dialog.SetSizer(sizer)
        apply_modal_ids(self.dialog)
        self.dialog.SetEscapeId(wx.ID_CANCEL)
        self._on_route(None)

    def _on_route(self, _event: Any) -> None:
        method = METHODS[max(0, self.method.GetSelection())]
        route = self.route.GetValue().strip()
        need = needed_capability(method, route) if route else ""
        self.needs.ChangeValue(need or "nothing beyond signing in")
        if _event is not None and route:
            matches = complete_route(route, self.routes)
            if matches and matches != list(self.route.GetStrings()):
                selection = self.route.GetInsertionPoint()
                self.route.Set(matches)
                self.route.ChangeValue(route)
                self.route.SetInsertionPoint(selection)

    def request(self) -> tuple[str, str, dict[str, Any]]:
        method = METHODS[max(0, self.method.GetSelection())]
        route = self.route.GetValue().strip().strip("/")
        return method, route, parse_params(self.params.GetValue())

    def send(self) -> None:
        try:
            method, route, given = self.request()
        except ValueError as exc:
            self.provider.say(str(exc))
            return
        if not route:
            self.provider.say("Type a route first.")
            return
        api = self.ctx.api
        if method not in ("GET", "OPTIONS"):
            if not wdlg.ask_preview(
                self.dialog,
                self.provider.show_modal,
                title="Send to the Site",
                summary=f"{method} {route} on {self.site}. This can change the site. "
                f"It needs: {self.needs.GetValue()}.",
                lines=[f"{k}: {json.dumps(v)}" for k, v in given.items()],
                yes="Send",
            ):
                return

        def work() -> Any:
            if method == "GET":
                return api.request("GET", route, params=given or None).payload
            if method == "OPTIONS":
                return api.request("OPTIONS", route).payload
            if method == "DELETE":
                return api.request("DELETE", route, params=given or None).payload
            return api.request(method, route, json_body=given).payload

        def done(answer: Any) -> None:
            self.show_answer(answer)
            if method not in ("GET", "OPTIONS"):
                self.provider.history.record(
                    Change(route, f"{method} {route} on {self.site} from the REST Console.")
                )
            self.provider.say(f"{method} {route}: answered.")

        self.provider.background(f"{method} {route}", work, done)

    def show_answer(self, answer: Any) -> None:
        self.answer = answer
        tree = self.tree
        tree.DeleteAllItems()
        root = tree.AddRoot("Answer")
        node = answer_tree(answer)

        def add(parent: Any, item: Any) -> None:
            for child in item.children:
                added = tree.AppendItem(parent, child.label)
                add(added, child)

        top = tree.AppendItem(root, node.label)
        add(top, node)
        tree.Expand(top)
        tree.SelectItem(top)

    def _copy(self) -> None:
        if self.answer is None:
            self.provider.say("There is no answer yet.")
            return
        self.provider.frame.copy_text(json.dumps(self.answer, ensure_ascii=False, indent=2))

    def show(self) -> int:
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            return int(show_modal_dialog(self.dialog, self.dialog.GetTitle()))
        finally:
            self.dialog.Destroy()
