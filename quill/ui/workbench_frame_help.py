"""Help in the Workbench window: F1 in layers, and the four help keys (Part D).

Split out of :mod:`quill.ui.workbench_frame` (GATE-11), provider-neutral:

- **F1** (D3) says the window's purpose with the selected node's help (layers 1
  and 2), then the focused control's own help, which follows the selection:
  the tree's help is the node's, the list's is the node's plus what its rows
  are and what Enter does (layers 3 and 4).
- **Shift+F1, What Can I Do Here?** (D5) lists every action for the selection
  from the same action table the menus use, in context-menu order, each with
  its key, and greyed ones with why. Enter runs it.
- **Alt+F1, What Is This?** (D6) explains the GitHub word for the selected row.
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
        ActionListDialog(
            self.frame, "What Can I Do Here", "Actions for the selection:", choices
        ).show()

    def what_is_this(self) -> None:
        hook = self._hook("glossary_for")
        term, text = hook(self._row_kind()) if hook else ("", "")
        if not term:
            self._say("No GitHub word for this.")
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
        HelpTextDialog(self.frame, "GitHub Workbench Keys", hook() if hook else "").show()

    def empty_words(self) -> str:
        hook = self._hook("empty_text")
        if hook is None or self.current is None:
            return ""
        return str(hook(self.current, self.node(self.current)))
