"""QUILL Lite's menu bar, generated from the command table.

Not fifty ``Append`` calls. The bar is built by walking
:data:`quill.core.lite.commands.COMMANDS`, so the keys the menus advertise, the
keys that are bound, and the keys the Keyboard Shortcuts window lists are one
list read three times -- and the uniqueness rules can be asserted against the
table (``tests/unit/core/lite/test_lite_commands.py``) rather than against a
running window.

One family of rows is *dimmed* as the document changes rather than rebuilt:
**Insert > Markdown Tag and Insert > HTML Tag**, of which exactly one can ever
apply. Dimmed rather than removed, and the difference matters by ear: a greyed
row announces itself as unavailable the moment a reader arrives on it, which
answers the question; a row that has vanished leaves somebody hunting the menus
for a feature they know the app has. The state is refreshed on every menu open
(``_on_menu_open``), so it can never be stale -- the language can change between
two presses of Alt.

Two menus are rebuilt as the app changes rather than built once:

* **Open Recent**, which skips entries whose file has gone. Skipped rather than
  greyed out: choosing a missing entry could only ever produce a "does not
  exist" prompt, so offering it costs a keystroke and an announcement for
  nothing.
* **Window**, which lists every open document *by its own number*, with Alt+1
  to Alt+9 on the first nine and a check mark on the one you are in. With MDI
  this is not a convenience -- an MDI child does not appear in Alt+Tab at all,
  so this list and Ctrl+F6 are the only ways between documents, and they have to
  be complete.

Both are rebuilt in *every* window whenever the set changes
(:meth:`~quill.apps.lite.QuillLiteApp.refresh_all_menus`), because a window
listing a stale set of siblings is worse than one listing none.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import wx

from quill.apps.lite_shell import MAX_NUMBERED
from quill.apps.lite_window_markup import MARKUP_COMMANDS
from quill.apps.lite_window_typing import overwrite_now
from quill.core.lite.commands import SUBMENU_SEP, CommandRow, split_menu
from quill.core.lite.format_kinds import FORMAT_COMMAND_KINDS, applies_to
from quill.core.lite.keymap import default_aliases, resolved_commands
from quill.ui.richedit_editing import RICH

__all__ = ["DocumentMenuMixin"]


def _quiet_mark(frame: object) -> bool:
    """Whether the Quiet Mode item should read as checked.

    A module function rather than a method, and that is the whole point:
    :meth:`DocumentMenuMixin._sync_check_items` is called unbound against stub
    frames, so a *sibling method* would be exactly the same trap one step along.

    Unchecked when the host cannot answer.
    :meth:`~quill.apps.lite_window_view.DocumentViewCommandsMixin.sound_is_quiet`
    already swallows its own failures; this covers the host not having it at all.
    """
    quiet = getattr(frame, "sound_is_quiet", None)
    return bool(quiet()) if callable(quiet) else False


def _dictation_mark(frame: object) -> bool:
    """Whether Dictation On should read as checked -- a module function for the
    same reason as :func:`_quiet_mark`, and unchecked when the host cannot say."""
    active = getattr(frame, "dictation_active", None)
    return bool(active()) if callable(active) else False


class DocumentMenuMixin:
    """The menu bar of a :class:`~quill.apps.lite_window.DocumentFrame`."""

    def _build_menus(self) -> None:
        """Build the bar from the command table, in table order.

        Only the areas that are switched on: an item removed from
        :func:`~quill.core.lite.commands.visible_commands` loses its menu row
        *and* its accelerator, because a key that still fires for a feature
        somebody has turned off is the feature not being off.

        The key in the label is the *resolved* one
        (:func:`~quill.core.lite.keymap.resolved_commands`), never the literal
        in the table: what the menu advertises is what the accelerator binds,
        whether or not the user has rebound it.

        Two passes, and the reason is a wxMSW rule rather than a preference: a
        ``wx.Menu`` must be **fully populated before** ``AppendSubMenu``
        attaches it, or the rows added afterwards do not appear. So the rows are
        grouped by menu first, and a submenu is built complete at the moment its
        title row is reached in its parent -- which is what lets a submenu sit
        where the table puts it (Matches under Find) rather than always at the
        bottom of the menu.
        """
        menu_bar = wx.MenuBar()
        self._recent_menu = wx.Menu()
        self._check_items = {}
        self._menu_items = {}
        self._window_menu_items = []
        rows: dict[str, list[CommandRow]] = {}
        top_level: list[str] = []
        for row in resolved_commands(self.app.feature_enabled, self.app.keymap):
            rows.setdefault(row[0], []).append(row)
            parent_label, _child = split_menu(row[0])
            if parent_label not in top_level:
                top_level.append(parent_label)
        menus: dict[str, wx.Menu] = {}
        for path in top_level:
            menu = self._fill_menu(wx.Menu(), path, rows)
            # A menu with nothing in it reads to a screen reader as a menu that
            # is broken rather than one that is empty, so it does not go on the
            # bar at all.
            if not menu.GetMenuItemCount():
                continue
            menus[path] = menu
            menu_bar.Append(menu, path)
        self._window_menu = menus["&Window"]
        self._window_menu.AppendSeparator()
        self.SetMenuBar(menu_bar)
        self._apply_alias_accelerators()
        self.refresh_recent_menu()
        self.refresh_window_menu()
        self._sync_check_items()
        self._sync_enabled_items()

    def _fill_menu(self, menu: wx.Menu, path: str, rows: dict[str, list[CommandRow]]) -> wx.Menu:
        """Put *path*'s rows into *menu*, building its submenus as they arrive."""
        for _menu_path, label, key, handler, kind in rows.get(path, []):
            if kind == "sep":
                menu.AppendSeparator()
                continue
            if kind == "sub":
                child_path = f"{path}{SUBMENU_SEP}{label}"
                # visible_commands drops a title whose submenu emptied, so a
                # missing child here would be a table typo rather than a
                # switched-off area. Skipped rather than raised: a mistyped
                # title must not take the whole menu bar down with it.
                if child_path in rows:
                    menu.AppendSubMenu(self._fill_menu(wx.Menu(), child_path, rows), label)
                continue
            # The tab only when there is a key after it. Every row in the
            # table ships one, but the Keyboard Manager can leave a command
            # unbound -- moving a taken key frees the command that had it --
            # and a label ending in a bare tab is a menu item advertising an
            # accelerator that is not there, which is the exact regression
            # class PRD 8.14's binding/label gate names.
            item = menu.Append(
                wx.ID_ANY,
                f"{label}	{key}" if key else label,
                kind=wx.ITEM_CHECK if kind == "check" else wx.ITEM_NORMAL,
            )
            self.Bind(wx.EVT_MENU, self._dispatch(handler), item)
            self._menu_items[handler] = item
            if kind == "check":
                self._check_items[handler] = item
            if handler == "cmd_open":
                menu.AppendSubMenu(self._recent_menu, "Open Recen&t")
        return menu

    def rebuild_menus(self) -> None:
        """Build the bar again, after the feature set changed.

        A whole new ``wx.MenuBar`` rather than an edit of the old one: working
        out which rows to add and remove is the same walk as building it, with
        an extra chance to leave a stale accelerator behind.
        """
        self._build_menus()

    def _apply_alias_accelerators(self) -> None:
        """Bind the shipped second chords, which a menu label cannot carry.

        wx takes an item's accelerator from the text after the tab in its
        label, and a label holds one. So the alias is a real accelerator table
        pointing at the same menu id -- the item fires either way, and the
        label keeps advertising the primary key rather than growing a second
        one nobody asked to read.

        Rebuilt with the bar because the ids are: an alias left pointing at a
        menu item from the previous build is a key that does nothing, which is
        worse than a key that was never offered.
        """
        entries = []
        for handler, chord in default_aliases().items():
            item = self._menu_items.get(handler)
            if item is None:
                continue  # the command's area is switched off; no id to fire
            parsed = wx.AcceleratorEntry()
            if not parsed.FromString(chord):
                # A chord wx cannot parse is not an accelerator, and binding it
                # would advertise a key that silently never fires -- the exact
                # failure the menu-accelerator gate exists to stop.
                continue
            entries.append(
                wx.AcceleratorEntry(parsed.GetFlags(), parsed.GetKeyCode(), item.GetId())
            )
        self.SetAcceleratorTable(wx.AcceleratorTable(entries))

    def _dispatch(self, handler: str) -> Any:
        def run(_event: wx.CommandEvent) -> None:
            getattr(self, handler)()

        return run

    def _sync_check_items(self) -> None:
        """Make the checkable items agree with the state they mirror.

        Looked up rather than indexed: an item whose area is switched off is not
        on the bar at all, so Check While Typing is simply absent when spelling
        is off. A ``KeyError`` here would take the menu build down with it.
        """
        marks = {
            "cmd_toggle_dark": self.app.settings.theme == "dark",
            "cmd_toggle_wrap": self.app.settings.word_wrap,
            # Per document, not per app: the file-type rule means two windows
            # can honestly disagree about this, and the mark has to read the
            # answer for the document in front of you.
            "cmd_toggle_live_spelling": getattr(self, "_live_spelling", False),
            # F8 extend mode: on while there is an anchor to extend from.
            "cmd_toggle_extend_mode": getattr(self, "_selection_anchor", None) is not None,
            "cmd_toggle_extend_selection_mode": self.extend_selection_active(),
            # Per document too: the control keeps overtype per control.
            "cmd_toggle_overwrite": overwrite_now(self),
            # Checked means Tab types a tab, which is how QUILL Lite starts.
            "cmd_toggle_tab_mode": getattr(self, "_tab_inserts_literal", True),
            # Per app, both of them: the status bar is either on screen or not,
            # and abbreviations either expand or do not, whichever document is
            # in front of you.
            "cmd_toggle_status_bar": getattr(self.app.settings, "show_status_bar", True),
            "cmd_toggle_abbreviations": self.app.feature_enabled("abbreviations"),
            # On while *this* document is being dictated into. There is one
            # microphone, so at most one window's mark is ever on.
            "cmd_toggle_dictation": _dictation_mark(self),
            # Quiet mode is *shared with QUILL*, so the mark cannot be cached on
            # this frame: the key pressed in another window -- or in the other
            # editor -- has already changed it by the time this menu opens.
            #
            # Reached for defensively, like every other row here. This mixin is
            # composed onto a host it does not own, ``sound_is_quiet`` lives on a
            # *different* mixin, and one missing method here does not leave the
            # menu bar one item short -- it raises inside the build and takes the
            # whole bar down, which is an app with no menus at all. It took out
            # two test frames the day it was added, and a test frame is only the
            # cheap version of that failure.
            "cmd_toggle_quiet_mode": _quiet_mark(self),
            # Both caret cues. Per app rather than per document, like the rest of
            # View: what you want said as you move is a habit, not a property of
            # the file in front of you.
            "cmd_toggle_heading_announcements": bool(
                getattr(self.app.settings, "announce_headings", True)
            ),
            "cmd_toggle_list_announcements": bool(
                getattr(self.app.settings, "announce_lists", True)
            ),
        }
        for handler, checked in marks.items():
            item = self._check_items.get(handler)
            if item is not None:
                item.Check(bool(checked))

    def _sync_enabled_items(self) -> None:
        """Grey out the rows this document's markup language cannot support.

        Looked up rather than indexed, for the reason
        :meth:`_sync_check_items` is: a row whose area is switched off is not on
        the bar at all, and a ``KeyError`` here would take the whole menu build
        down with it -- an app with no menus, over a row that was only ever
        going to be dimmed.
        """
        language = getattr(self, "document_language", None)
        current = language() if callable(language) else "plain"
        rich = self.editor.mode == RICH if hasattr(self, "editor") else False
        for handler, languages in MARKUP_COMMANDS.items():
            item = self._menu_items.get(handler)
            if item is not None:
                # Rich text disables both: its headings are a point size and its
                # bold is real bold, so a markup tag inserted into one would put
                # literal angle brackets next to text that is already formatted.
                item.Enable(not rich and current in languages)
        # The Format menu, which in a plain text document was thirty-one enabled
        # rows of which sixteen could only refuse ("if in plain text mode,
        # shouldn't the format menu go away?"). Dimmed rather than removed: the
        # menu bar's shape is what a listener navigates by, and Switch Document
        # Mode and Document Language stay live because they are the way out.
        kind = "rich" if rich else current
        for handler in FORMAT_COMMAND_KINDS:
            item = self._menu_items.get(handler)
            if item is not None:
                item.Enable(applies_to(handler, kind))

    def refresh_recent_menu(self) -> None:
        """Rebuild Open Recent, skipping files that are no longer there.

        Skipped rather than greyed: choosing a missing entry could only ever
        produce a "does not exist" prompt, so offering it wastes a keystroke and
        an announcement.
        """
        for item in list(self._recent_menu.GetMenuItems()):
            self._recent_menu.Delete(item)
        recent = [entry for entry in self.app.settings.recent_files if Path(entry).exists()]
        if not recent:
            placeholder = self._recent_menu.Append(wx.ID_ANY, "No recent files")
            placeholder.Enable(False)
            return
        for index, entry in enumerate(recent[:9], start=1):
            path = Path(entry)
            item = self._recent_menu.Append(
                wx.ID_ANY, f"&{index} {path.name}  ({path.parent})\tAlt+Shift+{index}"
            )
            self.Bind(wx.EVT_MENU, lambda _e, p=entry: self.app.open_path(Path(p)), item)

    def refresh_window_menu(self) -> None:
        """Rebuild the list of open documents, by number.

        The number is the document's own, not its position in the list, so
        "document 3" keeps meaning the same document after document 1 is closed.
        Alt+1 to Alt+9 land on the first nine numbers; past that the list still
        names every document and Ctrl+F6 still walks them all.

        Listed **in number order**, which is not always the order the documents
        were opened in: a closed document's number goes back in the pool, so the
        newest window can be number 2. The numbers are what this menu is written
        in and what Alt+digit presses, so a list that counts 1, 2, 3 down the
        menu is the one a person can follow; open-order would read 1, 3, 2.
        """
        for item_id in self._window_menu_items:
            self._window_menu.Delete(item_id)
        self._window_menu_items = []
        for frame in sorted(self.app.frames, key=lambda f: f.number):
            label = f"{frame.number}: {frame.document_name()}"
            if frame.number <= MAX_NUMBERED:
                label = f"&{frame.number} {frame.document_name()}	Alt+{frame.number}"
            item = self._window_menu.Append(wx.ID_ANY, label, kind=wx.ITEM_CHECK)
            item.Check(frame is self)
            self._window_menu_items.append(item.GetId())
            self.Bind(wx.EVT_MENU, lambda _e, f=frame: self.app.focus_frame(f), item)

    def sync_menu_state(self) -> None:
        """Both sweeps: the marks, and the rows this document can support.

        Public, and called from every moment that changes the answer rather
        than from the menu-open event alone -- because on an MDI child the
        menu-open event is not one of those moments. wxMSW merges a child's bar
        into the **parent** frame, which is where ``EVT_MENU_OPEN`` is then
        delivered; a child that bound it and nothing else refreshed once, at
        build time, and never again.

        That is what was reported. A document created plain and switched to
        Markdown with Alt+Shift+F kept every markup row dimmed -- Promote and
        Demote Heading, both section moves, the six headings, Normal Text, the
        Heading Organizer, bold, italic, underline, lists, and both tag pickers
        -- so Alt+Shift+Left and its neighbours were dead keys in a document
        that could have answered every one of them. Worse by ear than by eye: a
        dimmed row's accelerator does not fire and nothing says why.

        The shell forwards the menu-open event here as well
        (:meth:`quill.apps.lite_shell.QuillLiteShell._on_menu_open`), but the
        sweep no longer depends on that arriving: the state is correct the
        instant the document changes, whether or not a menu is ever opened.
        """
        self._sync_check_items()
        self._sync_enabled_items()

    def _on_menu_open(self, event: wx.MenuEvent) -> None:
        self.sync_menu_state()
        event.Skip()
