"""The Workbench window's menu bar, its keys and its commands (GitHub PRD sections 4 and 8).

Split out of :mod:`quill.ui.workbench_frame` (GATE-11). The frame arranges
panes; this mixin builds the bar from the provider's wx-free table, renders
each row's key from whatever is bound (so a key the person changes follows
the row), greys the rows that do not apply with their reason as the help
string, routes every command, and answers the keys the focused control owns
(Delete, Backspace, Escape, Ctrl+Break) in the tree and the list only.

The provider may answer a few optional hooks, read with ``getattr`` so a
provider that has not grown them yet still works: ``readout(name)`` for the
Alt+number readouts, ``reason(command_id)`` for why a row is greyed,
``remove_command(row_type)`` for Delete, ``explain(text)`` for Explain That,
``recall_place()`` / ``remember_place(place)`` for where the window was,
``recall_layout()`` / ``remember_layout(size, sash)`` for its size, and
``keymap_id`` naming its ``APP_KEYMAPS`` entry.

GATE-13: nothing here speaks on focus or selection. Words are results the
person asked for (a readout, a copy, a refusal), and the last one is kept so
F9 says it again and Shift+F9 explains it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["WorkbenchCommandsMixin", "bound_keys"]

#: The verbs the frame does itself, whatever the provider.
FRAME_VERBS = frozenset({
    "open_on_github",
    "copy_link",
    "copy",
    "properties",
    "refresh",
    "refresh_uncached",
    "refresh_alias",
    "help_view",
    "next_pane",
    "previous_pane",
    "back",
    "forward",
    "go_parent",
    "filter",
    "filter_alias",
    "select_all",
    "where_am_i",
    "say_selection",
    "say_filter",
    "say_loading",
    "close",
    "switch_to_editor",
    "open_address",
    "repeat_result",
    "explain_result",
    "inbox_home",
    "say_item",
    "say_counts",
    "say_access",
    "say_rate",
    "say_account",
    "what_can_i_do",
    "glossary",
    "guide_chapter",
    "search_help",
    "keys",
})


def bound_keys(keymap_id: str, defaults: dict[str, str]) -> dict[str, str]:
    """The keys in force: the person's own bindings over the window's defaults."""
    try:
        from quill.core.keymap import load_keymap

        user = load_keymap()
    except Exception:  # noqa: BLE001 - a broken keymap file must not stop the window
        user = {}
    keys = dict(defaults)
    for command_id, default in defaults.items():
        chosen = user.get(command_id)
        if chosen is not None and chosen != default:
            keys[command_id] = chosen
    return keys


class WorkbenchCommandsMixin:
    """Menu bar, keys and command routing for :class:`~quill.ui.workbench_frame.WorkbenchFrame`."""

    _wx: Any
    provider: Any
    frame: Any
    _splitter: Any
    tree: Any
    list: Any
    filter: Any
    details: Any
    status: Any
    current: Any
    rows: list[object]
    _announce: Callable[[str], None]
    last_result: str = ""

    # -- the bar -------------------------------------------------------------

    def _build_menu(self) -> None:
        from quill.core.workbench.menus import MenuSub, all_rows

        wx = self._wx
        defaults = {row.command_id: row.key for _spec, row in all_rows(self.provider.menu)}
        keys = bound_keys(getattr(self.provider, "keymap_id", ""), defaults)
        self._keys = keys
        self._menu_items: dict[str, Any] = {}
        self._dynamic_menus: dict[str, Any] = {}
        self._dynamic_ids: list[int] = []
        bar = wx.MenuBar()
        for spec in self.provider.menu:
            menu = wx.Menu()
            self.hear_greyed(menu)
            for row in spec.rows:
                if row is None:
                    menu.AppendSeparator()
                elif isinstance(row, MenuSub):
                    sub = wx.Menu()
                    self.hear_greyed(sub)
                    if row.dynamic:
                        self._dynamic_menus[row.dynamic] = sub
                    for inner in row.rows:
                        if inner is None:
                            sub.AppendSeparator()
                        else:
                            self._append_row(sub, inner, keys)
                    menu.AppendSubMenu(sub, row.title, row.help)
                else:
                    self._append_row(menu, row, keys)
            bar.Append(menu, spec.title)
        self.frame.SetMenuBar(bar)
        self.frame.Bind(wx.EVT_MENU_OPEN, self._on_menu_open)

    def _append_row(self, menu: Any, row: Any, keys: dict[str, str]) -> None:
        wx = self._wx
        key = keys.get(row.command_id, "")
        label = f"{row.label}	{key}" if key else row.label
        kind = wx.ITEM_CHECK if row.check else wx.ITEM_RADIO if row.radio else wx.ITEM_NORMAL
        item = menu.Append(wx.ID_ANY, label, row.help, kind)
        self._menu_items[row.command_id] = item
        self._row_labels = getattr(self, "_row_labels", {})
        self._row_labels[row.command_id] = row.label
        self.frame.Bind(wx.EVT_MENU, lambda _e, c=row.command_id: self.run(c), item)

    def fill_dynamic_menus(self) -> None:
        """Fill each dynamic submenu (the person's pins, favorites, searches) afresh."""
        wx = self._wx
        hook = getattr(self.provider, "dynamic_menu", None)
        for key, sub in getattr(self, "_dynamic_menus", {}).items():
            for item in list(sub.GetMenuItems()):
                sub.Delete(item)
            if key == "row_actions":
                self._fill_row_actions(sub)
                continue
            entries = list(hook(key)) if callable(hook) else []
            if not entries:
                empty = sub.Append(wx.ID_ANY, "(None yet)")
                empty.Enable(False)
                continue
            for index, (label, action) in enumerate(entries[:9], start=1):
                item = sub.Append(wx.ID_ANY, f"&{index} {label}")
                self.frame.Bind(wx.EVT_MENU, lambda _e, a=action: a(), item)

    def hear_greyed(self, menu: Any) -> None:
        """Say why a dimmed row is dimmed when it is highlighted (review item 25).

        The screen reader says "unavailable" and nothing more, and the status bar
        that would show the row's help is not where a listener is; so the reason,
        which the app alone knows, is spoken -- once per row, never for a row that
        works, which the reader already describes in full (GATE-13).
        """
        wx = self._wx

        def highlighted(event: Any) -> None:
            ident = event.GetMenuId()
            item = menu.FindItemById(ident) if ident != wx.ID_NONE else None
            if item is not None and not item.IsEnabled() and not item.IsSubMenu():
                said = item.GetHelp() or self.reason("")
                if said and said != getattr(self, "_greyed_said", ""):
                    self._greyed_said = said
                    self._say(said)
            event.Skip()

        menu.Bind(wx.EVT_MENU_HIGHLIGHT, highlighted)

    def _fill_row_actions(self, sub: Any) -> None:
        """Item > Commands for This Row: all the context menu has, More included (item 31)."""
        wx = self._wx
        row = self.selected_row() if self.current is not None else None
        if row is not None:
            top, more = self.row_actions(row)
        else:
            top, more = self.provider.actions.menu_for("node")
        from quill.core.workbench.menus import keep_access_key

        used: set[str] = set()
        rows = [*top, *more]
        if not rows:
            empty = sub.Append(wx.ID_ANY, "(Nothing for this row)")
            empty.Enable(False)
            return
        for action in rows:
            label = self.toggle_words(action.command_id, action.label)
            letter = next((c for c in label.lower() if c.isalnum() and c not in used), "")
            used.add(letter)
            shown = keep_access_key(f"&{letter}", label) if letter else label
            # No chord in the label: the bar's own row already claims it, and a second
            # claim would be a key two items share. The access letter is the route.
            item = sub.Append(wx.ID_ANY, shown, action.help)
            able = self.can_run(action.command_id)
            item.Enable(able)
            if not able:
                item.SetHelp(f"{self.reason(action.command_id)} {action.help}".strip())
            self.frame.Bind(wx.EVT_MENU, lambda _e, c=action.command_id: self.run(c), item)

    def _on_menu_open(self, event: Any) -> None:
        """Grey what does not apply here, with the reason as the row's help."""
        checked = getattr(self.provider, "is_checked", None)
        for command_id, item in getattr(self, "_menu_items", {}).items():
            self._name_toggle(command_id, item)
            able = self.can_run(command_id)
            item.Enable(able)
            row_help = self._row_help(command_id)
            reason = "" if able else self.reason(command_id)
            item.SetHelp(f"{reason} {row_help}".strip() if reason else row_help)
            if item.IsCheckable() and callable(checked):
                item.Check(bool(checked(command_id)))
        self.fill_dynamic_menus()
        event.Skip()

    def toggle_words(self, command_id: str, label: str) -> str:
        """*label*, or what a toggle row will do to the selected row (item 29)."""
        hook = getattr(self.provider, "toggle_label", None)
        words = hook(command_id, self.selected_row()) if callable(hook) else ""
        if not words:
            return label
        from quill.core.workbench.menus import keep_access_key

        return keep_access_key(label, str(words))

    def _name_toggle(self, command_id: str, item: Any) -> None:
        base = getattr(self, "_row_labels", {}).get(command_id, "")
        if not base:
            return
        label = self.toggle_words(command_id, base)
        if item.GetItemLabel().split("\t")[0] != label:
            key = getattr(self, "_keys", {}).get(command_id, "")
            item.SetItemLabel(f"{label}\t{key}" if key else label)

    def _row_help(self, command_id: str) -> str:
        from quill.core.workbench.menus import all_rows

        for _spec, row in all_rows(self.provider.menu):
            if row.command_id == command_id:
                return str(row.help)
        return ""

    def reason(self, command_id: str) -> str:
        """Why *command_id* is greyed here, in a sentence."""
        hook = getattr(self.provider, "reason", None)
        said = hook(command_id) if callable(hook) else ""
        return str(said or "Not available here.")

    # -- routing -------------------------------------------------------------

    def can_run(self, command_id: str) -> bool:
        verb = command_id.rsplit(".", 1)[-1]
        if command_id in self.provider.go_nodes:
            return True
        return verb in FRAME_VERBS or bool(self.provider.supports(command_id))

    def _frame_actions(self) -> dict[str, Callable[[], None]]:
        return {
            "next_pane": lambda: self.cycle_pane(1),
            "previous_pane": lambda: self.cycle_pane(-1),
            "back": self.back,
            "forward": self.go_forward,
            "go_parent": self.go_parent,
            "refresh": lambda: self.reload(report=True),
            "refresh_alias": lambda: self.reload(report=True),
            "refresh_uncached": lambda: self.reload(report=True),
            "filter": self.filter.SetFocus,
            "filter_alias": self.filter.SetFocus,
            "properties": self.show_properties,
            "copy_link": self.copy_link,
            "copy": self.copy_selection,
            "select_all": self.select_all,
            "open_on_github": self.open_in_browser,
            "where_am_i": lambda: self._say(self.where()),
            "say_selection": self.say_selection,
            "say_filter": lambda: self._say(self.filter_words()),
            "say_loading": lambda: self._say(self.loading_words()),
            "close": self.frame.Close,
            "switch_to_editor": self.switch_to_editor,
            "help_view": self.show_layered_help,
            "what_can_i_do": self.what_can_i_do,
            "glossary": self.what_is_this,
            "guide_chapter": self.guide_chapter,
            "search_help": self.search_help,
            "keys": self.show_keys,
            "key_describer": self.toggle_key_describer,
            "open_address": self.open_address,
            "repeat_result": self.repeat_result,
            "explain_result": self.explain_result,
            "inbox_home": lambda: self.go(self._inbox_command()),
            **{
                f"say_{name}": (lambda n=name: self.readout(n))
                for name in ("item", "counts", "access", "rate", "account")
            },
        }

    def _inbox_command(self) -> str:
        return next(
            (cid for cid, (_t, key) in self.provider.go_nodes.items() if key == "inbox"), ""
        )

    def run(self, command_id: str) -> None:
        """Do *command_id*: a menu row, a context-menu row or a key."""
        verb = command_id.rsplit(".", 1)[-1]
        actions = self._frame_actions()
        walk = getattr(self, "walk", None)  # a walk moves on when a command is done
        if command_id in self.provider.go_nodes:
            self.go(command_id)
            self.walk_moved_on(walk)
        elif verb in actions:
            actions[verb]()
        elif self.current is not None and self.provider.run(
            command_id, self.current, self.selected_row()
        ):
            self.walk_moved_on(walk)
            return
        else:
            self._say(self.reason(command_id))

    # -- readouts and results ------------------------------------------------

    def filter_words(self) -> str:
        from quill.core.workbench.filters import describe

        return describe(self.query) if not self.query.is_empty else "No filter"

    def loading_words(self) -> str:
        if self.loading:
            return "Loading"
        return f"Up to date, loaded at {self.loaded_at}" if self.loaded_at else "Nothing loaded"

    def readout(self, name: str) -> None:
        """Alt+3 to Alt+9: a fact, said, nothing moved (Part C, C4)."""
        hook = getattr(self.provider, "readout", None)
        said = hook(name) if callable(hook) else ""
        if said is None:
            return  # the provider answers later, with the result itself
        self._say(str(said or "Nothing to say here."))

    def _say(self, text: str) -> None:
        if text:
            self.last_result = text
        self._announce(text)

    def repeat_result(self) -> None:
        self._announce(self.last_result or "Nothing has happened yet.")

    def explain_result(self) -> None:
        hook = getattr(self.provider, "explain", None)
        text = hook(self.last_result) if callable(hook) and self.last_result else ""
        self._announce(text or "Nothing to explain yet. F9 says the last result.")

    # -- focus-aware copy and select ------------------------------------------

    def _focused_text(self) -> Any:
        focused = self._wx.Window.FindFocus()
        return focused if isinstance(focused, self._wx.TextCtrl) else None

    def copy_selection(self) -> None:
        """Ctrl+C: a text box copies its own selection; the list copies its rows."""
        text_box = self._focused_text()
        if text_box is not None:
            text_box.Copy()
            return
        chosen = [self.rows[i] for i in self.selected_indices()]
        if not chosen:
            self._say("Nothing selected to copy.")
            return
        columns = self._columns or ("name",)
        lines = [", ".join(c for c in self.provider.cells(row, columns) if c) for row in chosen]
        self.copy_text("\n".join(lines))

    def select_all(self) -> None:
        text_box = self._focused_text()
        if text_box is not None:
            text_box.SelectAll()
            return
        for index in range(self.list.GetItemCount()):
            self.list.Select(index)
        self.list.SetFocus()
        self.status.refresh()

    # -- keys the focused control owns -----------------------------------------

    def _on_char_hook(self, event: Any) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        focused = wx.Window.FindFocus()
        if self.status.has_focus():
            event.Skip()
            return
        plain = not event.HasAnyModifiers()
        on_lists = focused in (self.tree, self.list)
        if self.describe_key(event):
            return
        if code == wx.WXK_ESCAPE and plain and self.stop_walk():
            return
        if code == wx.WXK_ESCAPE and plain:
            # Escape clears the filter first. From Details it returns to the list, so
            # leaving that pane never jumps the tree to another node (UX review item 36);
            # anywhere else it goes Back.
            if self.filter.GetValue():
                self.clear_filter()
            elif focused is not None and focused is getattr(self, "details", None):
                self.list.SetFocus()
            else:
                self.back()
            return
        if code == wx.WXK_BACK and plain and on_lists:
            self.back()
            return
        from quill.ui.workbench_frame_keys import keep_list_key

        if focused is not self.list and keep_list_key(self, event, focused):
            return  # a provider's list-only key (WordPress's Delete), outside the list
        removes = callable(getattr(self.provider, "remove_command", None))
        if code == wx.WXK_DELETE and plain and focused is self.list and removes:
            self._remove_selected()
            return
        if code == wx.WXK_CANCEL and event.ControlDown() and on_lists:
            self.run("github.workbench.cancel_run")
            return
        if code == wx.WXK_HOME and event.AltDown() and not event.ControlDown():
            self.run("github.workbench.inbox_home")
            return
        # The second keys, on exactly these modifiers and only when no menu row has
        # the chord: they used to swallow Ctrl+Alt+Shift+F and Ctrl+Alt+R as well.
        from quill.ui.workbench_frame_keys import chord_of, menu_claims

        letter = chr(code).upper() if code in (ord("F"), ord("f"), ord("R"), ord("r")) else ""
        chord = chord_of(self, event, letter) if letter else ""
        if chord == "Ctrl+Shift+F" and not menu_claims(self, chord):
            self.filter.SetFocus()
            return
        if chord == "Ctrl+R" and not menu_claims(self, chord):
            self.reload()
            return
        event.Skip()

    def _remove_selected(self) -> None:
        """Delete: the selected row's safe removal, never immediate (C3)."""
        row = self.selected_row()
        if row is None or self.current is None:
            return
        hook = getattr(self.provider, "remove_command", None)
        kind = self.provider.row_type(self.node(self.current), row)
        command = hook(kind) if callable(hook) else ""
        if not command:
            self._say("Nothing to remove here.")
            return
        self.run(command)

    # -- where the window was ---------------------------------------------------

    def restore_place(self) -> Any:
        """Expand the nodes open last time; return the node to select, or None."""
        recall = getattr(self.provider, "recall_place", None)
        place = recall() if callable(recall) else None
        if not place:
            return None
        expanded, last = place
        for ref in expanded:
            item = self._items.get(ref)
            if item is not None:
                self.tree.Expand(item)
        return last if last in self._items else None

    def remember_place(self) -> None:
        keep = getattr(self.provider, "remember_place", None)
        if not callable(keep):
            return
        expanded = [ref for ref, item in self._items.items() if self.tree.IsExpanded(item)]
        try:
            keep((expanded, self.current))
        except OSError:
            pass  # a place not remembered costs one arrow press, never the close

    def restore_layout(self) -> None:
        """Last time's window size and tree-pane width, when the provider keeps them."""
        recall = getattr(self.provider, "recall_layout", None)
        if not callable(recall):
            return
        try:
            size, sash = recall()
        except (OSError, TypeError, ValueError):
            return
        if size:
            self.frame.SetSize(self.frame.FromDIP(self._wx.Size(*size)))
        if sash:
            self._splitter.SetSashPosition(self.frame.FromDIP(sash))

    def remember_layout(self) -> None:
        keep = getattr(self.provider, "remember_layout", None)
        if not callable(keep) or self.frame.IsMaximized() or self.frame.IsIconized():
            return
        size = self.frame.ToDIP(self.frame.GetSize())
        try:
            keep(
                (int(size.GetWidth()), int(size.GetHeight())),
                int(self.frame.ToDIP(self._splitter.GetSashPosition())),
            )
        except OSError:
            pass  # a size not remembered costs a drag, never the close
