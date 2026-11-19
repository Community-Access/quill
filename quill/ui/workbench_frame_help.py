"""Help in the Workbench window: F1 in layers, and the four help keys (Part D).

Split out of :mod:`quill.ui.workbench_frame` (GATE-11), provider-neutral:

- **F1** (D3) says the window's purpose with the selected node's help (layers 1
  and 2), then the focused control's own help, which follows the selection:
  the tree's help is the node's, the list's is the node's plus what its rows
  are and what Enter does (layers 3 and 4).
- **Shift+F1, What Can I Do Here?** (D5) lists every action for the selection
  from the same action table the menus use, in context-menu order, each with
  its key, and greyed ones with why. Enter runs it.
- **Alt+F1, What Is This?** (D6) explains the provider's word for the selected row
  (GitHub's or WordPress's).
- **Ctrl+F1** opens the guide at the chapter for this node.
- **Ctrl+Shift+F1, Search Help** (D7) finds places, commands, words and tasks.
- **Alt+Shift+F1** lists the keys.

Provider hooks, read with ``getattr`` so a provider without one still works:
``help_purpose()``, ``glossary_for(row_type)``, ``open_guide(ref)``,
``search_help(words, commands)``, ``key_text()`` and ``empty_text(ref, node)``.
Nothing here speaks on its own (GATE-13): each key opens a window the reader
reads.
"""

from __future__ import annotations

from typing import Any

from quill.core.workbench.menus import all_rows
from quill.ui.workbench_help_dialogs import (
    ActionChoice,
    ActionListDialog,
    HelpTextDialog,
    SearchHelpDialog,
)

__all__ = ["WorkbenchHelpMixin"]


class WorkbenchHelpMixin:
    """F1 and the help keys for :class:`~quill.ui.workbench_frame.WorkbenchFrame`."""

    _wx: Any
    provider: Any
    frame: Any
    tree: Any
    list: Any
    current: Any
    walk: Any = None
    """The Walk Me Through It in progress, or None (D12)."""

    # -- the words -------------------------------------------------------------

    def _hook(self, name: str) -> Any:
        hook = getattr(self.provider, name, None)
        return hook if callable(hook) else None

    def _row_kind(self) -> str:
        row = self.selected_row()
        if row is None or self.current is None:
            return "node"
        return str(self.provider.row_type(self.node(self.current), row))

    def refresh_control_help(self) -> None:
        """Keep the tree's and the list's F1 words on the selected node (D3)."""
        if self.current is None:
            return
        node_words = self.provider.node_help(self.current, self.node(self.current))
        self.tree.SetHelpText(node_words)
        kind = self.node(self.current).row_type or self._row_kind()
        rows = (
            self.provider.actions.rows_for(kind) if kind in self.provider.actions.row_types else ()
        )
        default = f" Enter on a row: {rows[0].label}." if rows else ""
        self.list.SetHelpText(
            f"{node_words}{default} Shift+F1 lists everything you can do with the "
            "selected row, Alt+Enter shows all about it."
        )

    def show_layered_help(self) -> None:
        """F1: the window's purpose and this node, then the focused control."""
        walk = getattr(self, "walk", None)
        if walk is not None:  # during Walk Me Through It, F1 says the step again
            self._announce(walk.current())
            return
        try:
            from quill.core.help import HelpTopic
            from quill.ui import app_context_help
            from quill.ui.context_help import ContextHelpDialog
            from quill.ui.dialog_contract import show_modal_dialog

            self.refresh_control_help()
            _surface, control = app_context_help.topics_for(self.frame, self._wx)
            purpose_hook = self._hook("help_purpose")
            purpose = purpose_hook() if purpose_hook else ""
            where = ""
            if self.current is not None:
                where = self.provider.node_help(self.current, self.node(self.current))
            body = "\n\n".join(part for part in (purpose, f"Where you are: {where}") if part)
            route = app_context_help.guide_route_for(self.frame.GetTitle())
            label, opener = route if route is not None else ("", None)
            dialog = ContextHelpDialog(
                self.frame,
                dialog_topic=HelpTopic(id="", title=self.frame.GetTitle(), body=body),
                ctrl_topic=control,
                user_guide_opener=(lambda _section=None: opener()) if opener else None,
                guide_label=label,
            )
            try:
                show_modal_dialog(dialog, "Context Help")
            finally:
                dialog.Destroy()
        except Exception:  # noqa: BLE001 - help must never take the window down
            return

    # -- the help keys -----------------------------------------------------------

    def what_can_i_do(self) -> None:
        """Shift+F1: every action for the selection, its key, and why any is greyed."""
        walk = getattr(self, "walk", None)
        if walk is not None:  # during Walk Me Through It, Shift+F1 lists the steps
            self._announce(walk.listing())
            return
        kind = self._row_kind()
        table = self.provider.actions
        if kind not in table.row_types:
            kind = "node"
        keys = getattr(self, "_keys", {})
        choices = []
        for row in table.rows_for(kind):
            able = self.can_run(row.command_id)
            key = keys.get(row.command_id, "")
            text = row.label + (f", {key}" if key else "")
            if not able:
                text += f", greyed: {self.reason(row.command_id)}"
            choices.append(ActionChoice(text, able, lambda c=row.command_id: self.run(c), row.help))
        why = self._hook("why_text")  # D13: Why? comes first when something happened on its own
        said = str(why() or "") if why else ""
        if said:
            choices.insert(
                0, ActionChoice("Why?", True, lambda: self._announce(said), "Why this is so.")
            )
        hook = self._hook("role_words")  # who you are here, when the provider knows (item 25)
        role = str(hook() or "") if hook else ""
        prompt = f"{role} Actions for the selection:".strip()
        ActionListDialog(self.frame, "What Can I Do Here", prompt, choices).show()

    def what_is_this(self) -> None:
        hook = self._hook("glossary_for")
        term, text = hook(self._row_kind()) if hook else ("", "")
        if not term:
            self._say("There is no glossary word for this.")
            return
        HelpTextDialog(self.frame, "What Is This", f"{term}\n\n{text}").show()

    def guide_chapter(self) -> None:
        hook = self._hook("open_guide")
        if hook is None or self.current is None:
            self._say("This window has no guide.")
            return
        hook(self.current)

    def search_help(self) -> None:
        hook = self._hook("search_help")
        if hook is None:
            self._say("This window has no help to search.")
            return
        commands = {
            row.command_id: (
                row.label.replace("&", "").rstrip("."),
                getattr(self, "_keys", {}).get(row.command_id, ""),
            )
            for _spec, row in all_rows(self.provider.menu)
        }

        def search(words: str) -> list[ActionChoice]:
            return [
                ActionChoice(hit.spoken(), True, lambda h=hit: self._follow(h), hit.body)
                for hit in hook(words, commands)
            ]

        SearchHelpDialog(self.frame, search).show()

    def _follow(self, hit: Any) -> None:
        """Do what a Search Help result says: go there, run it, or read it."""
        from quill.ui.workbench_frame import NodeRef

        if hit.kind == "command":
            self.run(hit.target)
            return
        if hit.kind in ("node", "task") and hit.target:
            template, _, key = hit.target.partition(":")
            instance = next(iter(self.provider.instances(template)), "") if template else ""
            if self.select(NodeRef(template, key, instance)):
                self.tree.SetFocus()
                if hit.kind == "node":
                    return
        HelpTextDialog(self.frame, "What Is This", f"{hit.title}\n\n{hit.body}").show()

    def show_keys(self) -> None:
        hook = self._hook("key_text")
        name = str(getattr(self.provider, "name", "") or "Workbench")
        HelpTextDialog(self.frame, f"{name} Keys", hook() if hook else "").show()

    # -- the Key Describer (GitHub PRD 7.3) ----------------------------------------

    describing_keys: bool = False

    def toggle_key_describer(self) -> None:
        """Ctrl+Alt+K: keys say what they do here instead of doing it, until Escape."""
        self.describing_keys = not self.describing_keys
        self._announce(
            "Key Describer on. Press a key to hear what it does here; Escape stops."
            if self.describing_keys
            else "Key Describer off."
        )

    def describe_key(self, event: Any) -> bool:
        """While the describer is on, say *event*'s key and swallow it; False otherwise."""
        if not self.describing_keys:
            return False
        from quill.core.key_describer import describe
        from quill.core.workbench.menus import all_rows

        wx = self._wx
        code = event.GetKeyCode()
        if code == wx.WXK_ESCAPE and not event.HasAnyModifiers():
            self.toggle_key_describer()
            return True
        accelerator = _accelerator(wx, event)
        if not accelerator:
            event.Skip()  # a modifier on its own: wait for the key it goes with
            return True
        keys = dict(getattr(self, "_keys", {}))
        labels = {
            row.command_id: row.label.replace("&", "").rstrip(".")
            for _spec, row in all_rows(getattr(self.provider, "menu", ()))
        }
        why_not = {cmd: self.reason(cmd) for cmd in keys if not self.can_run(cmd)}
        self._announce(describe(accelerator, keys, labels, why_not=why_not))
        return True

    # -- Walk Me Through It (D12) ------------------------------------------------

    def start_walk(self, title: str, text: str) -> None:
        """Say a task's first step and wait for a command before the next one."""
        from quill.core.workbench.walk import Walk, steps_of

        steps = steps_of(text)
        if not steps:
            self._announce("This topic has no steps to walk through.")
            return
        self.walk = Walk(title, steps)
        self._announce(self.walk.opening())

    def walk_moved_on(self, walk: Any) -> None:
        """A command ran during *walk*: say the next step after the command's own words."""
        if walk is None or getattr(self, "walk", None) is not walk:
            return
        said = walk.advance()
        if walk.finished:
            self.walk = None
        self._wx.CallAfter(self._announce, said)

    def stop_walk(self) -> bool:
        """Escape during a walk ends it; False when there was none."""
        walk = getattr(self, "walk", None)
        if walk is None:
            return False
        self.walk = None
        self._announce(f"Stopped walking through {walk.title}.")
        return True

    def empty_words(self) -> str:
        hook = self._hook("empty_text")
        if hook is None or self.current is None:
            return ""
        return str(hook(self.current, self.node(self.current)))


def _accelerator(wx: Any, event: Any) -> str:
    """*event* as the keymap writes keys ("Ctrl+Shift+M"), or "" for a bare modifier."""
    code = event.GetKeyCode()
    names = {
        **{getattr(wx, f"WXK_F{n}", -100 - n): f"F{n}" for n in range(1, 13)},
        wx.WXK_RETURN: "Enter",
        wx.WXK_NUMPAD_ENTER: "Enter",
        wx.WXK_TAB: "Tab",
        wx.WXK_ESCAPE: "Escape",
        wx.WXK_SPACE: "Space",
        wx.WXK_BACK: "Backspace",
        wx.WXK_DELETE: "Delete",
        wx.WXK_INSERT: "Insert",
        wx.WXK_HOME: "Home",
        wx.WXK_END: "End",
        wx.WXK_PAGEUP: "PageUp",
        wx.WXK_PAGEDOWN: "PageDown",
        wx.WXK_LEFT: "Left",
        wx.WXK_RIGHT: "Right",
        wx.WXK_UP: "Up",
        wx.WXK_DOWN: "Down",
        wx.WXK_CANCEL: "Pause",
    }
    if code in (wx.WXK_CONTROL, wx.WXK_SHIFT, wx.WXK_ALT, getattr(wx, "WXK_RAW_CONTROL", -1)):
        return ""
    name = names.get(code) or (chr(code).upper() if 33 <= code <= 126 else "")
    if not name:
        return ""
    held = [
        word
        for word, down in (
            ("Ctrl", event.ControlDown()),
            ("Alt", event.AltDown()),
            ("Shift", event.ShiftDown()),
        )
        if down
    ]
    return "+".join([*held, name])
