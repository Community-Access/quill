from __future__ import annotations

from collections.abc import Callable

from quill.core.commands import Command, CommandRegistry
from quill.core.features import FeatureManager
from quill.core.palette import (
    load_palette_usage,
    rank_commands,
    record_palette_usage,
    save_palette_usage,
)
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog


class CommandPaletteDialog:
    """Searchable command palette.

    Borrowed UX patterns from ChapterForge's palette:
    - Unavailable commands shown dimmed with ``- `` prefix (discoverability).
    - Per-item screen-reader announcement on Down/Up navigation.
    - Actionable status label: count + top match + keyboard instructions.
    - Cancel button to clear query in one press.
    - Accessible control names readable by NVDA/JAWS without focus.
    - Refuses to run unavailable commands and announces why.
    """

    def __init__(
        self,
        parent: object,
        command_registry: CommandRegistry,
        feature_manager: FeatureManager | None = None,
        announce_fn: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._registry = command_registry
        self._features = feature_manager
        self._announce_fn = announce_fn
        # Show only commands whose feature is visible in the current profile.
        # Commands for OFF features are omitted entirely; the palette should
        # reflect the user's chosen experience, not the full catalogue.
        all_commands = command_registry.list()
        if feature_manager is not None:
            self._commands: list[Command] = [
                cmd for cmd in all_commands if feature_manager.is_visible(cmd.feature_id)
            ]
        else:
            self._commands = all_commands
        self._usage = load_palette_usage()
        self._filtered_commands: list[Command] = rank_commands(self._commands, "", self._usage)

        self.dialog = wx.Dialog(
            parent,
            title="Command Palette",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetName("Command Palette — type to search, Enter to run, Escape to close")
        self.dialog.SetSize((700, 500))

        root = wx.BoxSizer(wx.VERTICAL)
        self.search = wx.SearchCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        self.search.SetName("Search commands")
        self.search.ShowSearchButton(True)
        self.search.ShowCancelButton(True)
        self.search.SetDescriptiveText("Type command (>, :, ?, ~ prefixes supported)")
        root.Add(self.search, 0, wx.EXPAND | wx.ALL, 8)

        self.status = wx.StaticText(self.dialog, label="")
        self.status.SetName("Command palette status")
        root.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.results = wx.ListBox(self.dialog)
        self.results.SetName("Command results — use arrows to navigate, Enter to run")
        root.Add(self.results, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)

        self.search.Bind(wx.EVT_TEXT, self._on_search_changed)
        self.search.Bind(wx.EVT_TEXT_ENTER, self._on_accept)
        self.search.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, lambda _e: self.search.Clear())
        self.results.Bind(wx.EVT_LISTBOX_DCLICK, self._on_accept)
        self.results.Bind(wx.EVT_LISTBOX, self._on_result_selected)
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

        self._refresh_results()

    def _set_status(self, msg: str) -> None:
        self.status.SetLabel(msg)
        if self._announce_fn is not None and msg:
            self._announce_fn(msg)

    def _is_available(self, command: Command) -> bool:
        if self._features is None:
            return True
        is_visible = getattr(self._features, "is_visible", None)
        if callable(is_visible):
            return bool(is_visible(command.feature_id))
        return True

    def show_modal_and_run(self) -> None:
        self.dialog.CentreOnParent()
        try:
            result = show_modal_dialog(self.dialog, "Command Palette")
            if result == self._wx.ID_OK:
                self._run_selected()
        finally:
            self.dialog.Destroy()

    def _on_search_changed(self, _event: object) -> None:
        query = self.search.GetValue()
        self._filtered_commands = rank_commands(self._commands, query, self._usage)
        self._refresh_results()

    def _on_accept(self, _event: object) -> None:
        if self.results.GetCount() == 0:
            return
        self.dialog.EndModal(self._wx.ID_OK)

    def _on_char_hook(self, event: object) -> None:
        key_code = event.GetKeyCode()
        wx = self._wx
        if key_code == wx.WXK_ESCAPE:
            # The palette has no buttons, so SetEscapeId(wx.ID_CANCEL) has
            # nothing to activate; close it explicitly so Escape is not a
            # keyboard trap (WCAG 2.1.2, #124).
            self.dialog.EndModal(wx.ID_CANCEL)
            return
        if key_code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._on_accept(event)
            return
        n = self.results.GetCount()
        if key_code == wx.WXK_DOWN and n > 0:
            cur = self.results.GetSelection()
            nxt = min(cur + 1, n - 1) if cur >= 0 else 0
            self.results.SetSelection(nxt)
            self.results.SetFocus()
            self._announce_at(nxt)
            return
        if key_code == wx.WXK_UP and n > 0:
            cur = self.results.GetSelection()
            nxt = max(cur - 1, 0) if cur >= 0 else n - 1
            self.results.SetSelection(nxt)
            self.results.SetFocus()
            self._announce_at(nxt)
            return
        event.Skip()

    def _announce_at(self, index: int) -> None:
        if 0 <= index < len(self._filtered_commands):
            command = self._filtered_commands[index]
            available = self._is_available(command)
            suffix = "" if available else " (unavailable)"
            msg = f"{command.title}{suffix}"
            if self._announce_fn is not None:
                self._announce_fn(msg)
            else:
                self.status.SetLabel(msg)

    def _refresh_results(self) -> None:
        labels = []
        for command in self._filtered_commands:
            binding = command.keybinding or ""
            label = f"{command.title} [{binding}]" if binding else command.title
            labels.append(label)
        self.results.Set(labels)
        if labels:
            self.results.SetSelection(0)
            top = self._filtered_commands[0]
            available_count = sum(1 for cmd in self._filtered_commands if self._is_available(cmd))
            self._set_status(
                f"{len(labels)} command(s), {available_count} available. "
                f"Top match: {top.title}. "
                "Down/Up to navigate, Enter to run."
            )
            return
        self._set_status("No matching commands")

    def _on_result_selected(self, _event: object) -> None:
        selected = self.results.GetSelection()
        if selected == self._wx.NOT_FOUND or selected < 0:
            return
        if selected < len(self._filtered_commands):
            command = self._filtered_commands[selected]
            available = self._is_available(command)
            suffix = "" if available else " (unavailable)"
            self._set_status(f"Selected: {command.title}{suffix}")

    def _run_selected(self) -> None:
        selected = self.results.GetSelection()
        if selected == self._wx.NOT_FOUND:
            return
        if selected >= len(self._filtered_commands):
            return
        command = self._filtered_commands[selected]
        if not self._is_available(command):
            self._set_status(f"{command.title} is not available in the current context.")
            return
        self._last_run_id: str | None = command.id
        self._registry.run(command.id)
        self._usage = record_palette_usage(self._usage, command.id)
        save_palette_usage(self._usage)

    def last_run_command_id(self) -> str | None:
        return getattr(self, "_last_run_id", None)


class GoToAnythingDialog:
    """§8.1 NAV-4: Extended palette that searches commands, headings, and bookmarks.

    Accepts the same query prefixes as :class:`CommandPaletteDialog` plus a
    ``#`` prefix to restrict results to document headings only.
    Same ChapterForge-inspired UX improvements as CommandPaletteDialog:
    per-item announcement on navigation, actionable status, cancel button,
    accessible control names.
    """

    def __init__(
        self,
        parent: object,
        command_registry: object,
        *,
        feature_manager: object | None = None,
        headings: list[tuple[str, int]] | None = None,
        announce_fn: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._registry = command_registry
        self._features = feature_manager
        self._announce_fn = announce_fn
        self._headings: list[tuple[str, int]] = headings or []

        from quill.core.commands import CommandRegistry

        if isinstance(command_registry, CommandRegistry):
            all_cmds = command_registry.list()
            if feature_manager is not None:
                self._commands = [
                    cmd
                    for cmd in all_cmds
                    if feature_manager.is_visible(getattr(cmd, "feature_id", "core.app"))
                ]
            else:
                self._commands = all_cmds
        else:
            self._commands = []
        self._usage = load_palette_usage()
        self._filtered_results: list[dict[str, object]] = []

        self.dialog = wx.Dialog(
            parent,
            title="Go to Anything",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetName(
            "Go to Anything — type to search headings and commands, Enter to go, Escape to close"
        )
        self.dialog.SetSize((700, 520))

        root = wx.BoxSizer(wx.VERTICAL)
        self.search = wx.SearchCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        self.search.SetName("Search headings and commands")
        self.search.ShowSearchButton(True)
        self.search.ShowCancelButton(True)
        self.search.SetDescriptiveText(
            "Type to search commands, headings, settings  (#headings  >commands)"
        )
        root.Add(self.search, 0, wx.EXPAND | wx.ALL, 8)

        self.status = wx.StaticText(self.dialog, label="")
        self.status.SetName("Go to Anything status")
        root.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.results = wx.ListBox(self.dialog)
        self.results.SetName("Results — use arrows to navigate, Enter to go")
        root.Add(self.results, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.dialog.SetSizer(root)

        from quill.ui.dialog_contract import apply_modal_ids

        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)

        self.search.Bind(wx.EVT_TEXT, self._on_search_changed)
        self.search.Bind(wx.EVT_TEXT_ENTER, self._on_accept)
        self.search.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, lambda _e: self.search.Clear())
        self.results.Bind(wx.EVT_LISTBOX_DCLICK, self._on_accept)
        self.results.Bind(wx.EVT_LISTBOX, self._on_result_selected)
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

        self._refresh_results("")

    def _set_status(self, msg: str) -> None:
        self.status.SetLabel(msg)
        if self._announce_fn is not None and msg:
            self._announce_fn(msg)

    def _cmd_is_available(self, cmd: object) -> bool:
        if self._features is None:
            return True
        is_visible = getattr(self._features, "is_visible", None)
        feature_id = getattr(cmd, "feature_id", None)
        if callable(is_visible) and feature_id is not None:
            return bool(is_visible(feature_id))
        return True

    def show_modal_and_run(self, frame: object) -> None:
        self.dialog.CentreOnParent()
        try:
            from quill.ui.dialog_contract import show_modal_dialog

            result = show_modal_dialog(self.dialog, "Go to Anything")
            if result == self._wx.ID_OK:
                self._activate_selected(frame)
        finally:
            self.dialog.Destroy()

    def _on_search_changed(self, _event: object) -> None:
        self._refresh_results(self.search.GetValue())

    def _on_accept(self, _event: object) -> None:
        if self.results.GetCount() > 0:
            self.dialog.EndModal(self._wx.ID_OK)

    def _on_char_hook(self, event: object) -> None:
        key_code = event.GetKeyCode()
        wx = self._wx
        if key_code == wx.WXK_ESCAPE:
            self.dialog.EndModal(wx.ID_CANCEL)
            return
        if key_code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._on_accept(event)
            return
        n = self.results.GetCount()
        if key_code == wx.WXK_DOWN and n > 0:
            cur = self.results.GetSelection()
            nxt = min(cur + 1, n - 1) if cur >= 0 else 0
            self.results.SetSelection(nxt)
            self.results.SetFocus()
            self._announce_at(nxt)
            return
        if key_code == wx.WXK_UP and n > 0:
            cur = self.results.GetSelection()
            nxt = max(cur - 1, 0) if cur >= 0 else n - 1
            self.results.SetSelection(nxt)
            self.results.SetFocus()
            self._announce_at(nxt)
            return
        event.Skip()

    def _announce_at(self, index: int) -> None:
        if 0 <= index < len(self._filtered_results):
            item = self._filtered_results[index]
            kind = str(item.get("kind", ""))
            label = str(item.get("label", ""))
            msg = f"{kind}: {label}"
            if self._announce_fn is not None:
                self._announce_fn(msg)
            else:
                self.status.SetLabel(msg)

    def _on_result_selected(self, _event: object) -> None:
        sel = self.results.GetSelection()
        if 0 <= sel < len(self._filtered_results):
            item = self._filtered_results[sel]
            kind = str(item.get("kind", ""))
            label = str(item.get("label", ""))
            self._set_status(f"[{kind}] {label}")

    def _refresh_results(self, query: str) -> None:
        q = query.strip()
        heading_only = q.startswith("#")
        command_only = q.startswith(">")
        clean_q = q.lstrip("#>").strip().lower()

        results: list[dict[str, object]] = []

        if not command_only:
            for heading, lineno in self._headings:
                if not clean_q or clean_q in heading.lower():
                    results.append({"kind": "heading", "label": heading, "lineno": lineno})

        if not heading_only:
            ranked = rank_commands(self._commands, clean_q, self._usage)
            for cmd in ranked:
                binding = getattr(cmd, "keybinding", "") or ""
                label = f"{cmd.title} [{binding}]" if binding else cmd.title
                results.append({
                    "kind": "command",
                    "label": label,
                    "cmd_id": cmd.id,
                    "cmd": cmd,
                    "available": True,
                })

        self._filtered_results = results
        labels = [
            (f"  # {r['label']}" if r["kind"] == "heading" else f"  > {r['label']}")
            for r in results
        ]
        self.results.Set(labels)
        if labels:
            self.results.SetSelection(0)
            top = results[0]
            self._set_status(
                f"{len(labels)} result(s). Top: [{top['kind']}] {top['label']}. "
                "Down/Up to navigate, Enter to go."
            )
        else:
            self._set_status("No results")

    def _activate_selected(self, frame: object) -> None:
        sel = self.results.GetSelection()
        if sel < 0 or sel >= len(self._filtered_results):
            return
        item = self._filtered_results[sel]
        if item["kind"] == "heading":
            lineno = int(item.get("lineno", 1))
            go_to_line = getattr(frame, "go_to_line_number", None)
            if callable(go_to_line):
                go_to_line(lineno)
            return
        if item["kind"] == "command":
            if not item.get("available", True):
                cmd = item.get("cmd")
                title = getattr(cmd, "title", str(item.get("cmd_id", "")))
                self._set_status(f"{title} is not available in the current context.")
                return
            cmd_id = str(item.get("cmd_id", ""))
            if cmd_id:
                self._registry.run(cmd_id)
                cmd = item.get("cmd")
                if cmd is not None:
                    self._usage = record_palette_usage(self._usage, cmd_id)
                    save_palette_usage(self._usage)
