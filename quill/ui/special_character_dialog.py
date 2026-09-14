"""Insert Special Character: one picker, both editors.

Three hundred and fifty characters is past the size a plain list works at. Forty
rows you arrow through; three hundred and fifty you get lost in, and the ones
that sound alike -- four spaces, two hyphens that are not hyphens, twenty-four
letters "with acute" -- are exactly the ones a listener cannot skim past. So
this is the shape the emoji picker already proved
(:mod:`quill.ui.main_frame_emoji_picker`): **search across everything, or browse
one group**, with a description of whatever row you are on.

What is deliberate here:

* **The search box is also the code-point prompt.** Typing ``2014``, ``U+2014``
  or ``d8212`` puts the em dash at the top of the results, and a code point in
  no group at all still resolves to its character -- so the picker reaches every
  character Unicode has, and the separate "type a code point" prompt this
  command used to be is gone rather than bolted on beside it.
* **A Character column, and a Code point column beside it.** Half the catalogue
  has no glyph, so the character column shows a speakable stand-in for those
  (:func:`quill.core.char_describe.display_glyph`), and the code point is what
  tells "Thin space" from "Hair space" when the name is all a listener has.
* **The description updates on every selection, not on demand.** It is the same
  text Describe Character gives for the character once it is in the document, so
  choosing one and then inspecting it later answer in the same words.
* **Nothing is announced from here.** The reader says the dialog title, the
  control names and the row you land on; this only fills in what it alone knows,
  through the status line and the description pane, both of which are read
  because they are labelled controls rather than because anybody spoke them
  (GATE-13).

Shared rather than duplicated, because "QuillLite may never be ahead of QUILL":
one dialog, one catalogue, and neither editor can offer a character the other
cannot.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core import special_characters as catalogue
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name, show_modal_dialog

__all__ = ["SpecialCharacterDialog", "choose_special_character"]

TITLE = "Insert Special Character"

_PAD = 8


class SpecialCharacterDialog:
    """The picker. :meth:`show` returns the chosen character, or ``None``."""

    def __init__(
        self,
        parent: wx.Window,
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        self._categories = catalogue.list_categories()
        self._rows: list[catalogue.SpecialCharacter] = []
        self._announce = announce_cb or (lambda _message: None)
        # Whether the last fill was empty, so "nothing matched" is said once on
        # the way into that state rather than on every further keystroke.
        self._was_empty = False

        self.dialog = wx.Dialog(
            parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((640, 460))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        # Each label is constructed immediately before the control it names:
        # Windows screen readers take a control's accessible name from the
        # static text built directly before it, and getting that order wrong is
        # silent -- the control still appears, announced as "edit" with no name.
        search_label = wx.StaticText(panel, label="&Search by name or code point:")
        self._search = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        set_accessible_name(self._search, "Search by name or code point")
        self._search.SetHelpText(catalogue.SEARCH_HELP)
        root.Add(search_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self._search, 0, wx.EXPAND | wx.ALL, _PAD)

        body = wx.BoxSizer(wx.HORIZONTAL)

        group_col = wx.BoxSizer(wx.VERTICAL)
        group_label = wx.StaticText(panel, label="&Group")
        self._groups = wx.ListBox(panel, choices=self._categories)
        set_accessible_name(self._groups, "Group")
        self._groups.SetHelpText(
            "The kinds of character this picker carries: whitespace, dashes, quotes, "
            "invisibles, typography, marks, currency, maths, fractions, superscripts, "
            "arrows, accented letters, Greek, and punctuation from other languages. "
            "Choose one to see its characters. Searching overrides the group until you "
            "clear the search box."
        )
        group_col.Add(group_label, 0, wx.BOTTOM, 4)
        group_col.Add(self._groups, 1, wx.EXPAND)
        body.Add(group_col, 1, wx.EXPAND | wx.RIGHT, _PAD)

        list_col = wx.BoxSizer(wx.VERTICAL)
        list_label = wx.StaticText(panel, label="&Characters")
        self._results = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        set_accessible_name(self._results, "Characters")
        self._results.SetHelpText(
            "The characters in the group you chose, or the ones your search found. "
            "Arrow through them to hear each one described, and press Enter to put the "
            "one you are on into the document at the cursor."
        )
        self._results.InsertColumn(0, "Character", width=90)
        self._results.InsertColumn(1, "Name", width=300)
        self._results.InsertColumn(2, "Code point", width=100)
        list_col.Add(list_label, 0, wx.BOTTOM, 4)
        list_col.Add(self._results, 1, wx.EXPAND)
        body.Add(list_col, 2, wx.EXPAND)

        root.Add(body, 3, wx.EXPAND | wx.LEFT | wx.RIGHT, _PAD)

        detail_label = wx.StaticText(panel, label="&Description")
        self._detail = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        set_accessible_name(self._detail, "Description")
        self._detail.SetHelpText(
            "Everything known about the character you are on: its name, its code point "
            "in hexadecimal and decimal, what kind of character it is, and a note for "
            "the ones that are easy to miss in a document."
        )
        root.Add(detail_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self._detail, 1, wx.EXPAND | wx.ALL, _PAD)

        # A labelled read-only readout rather than an announcement: how many
        # rows there are is a fact the reader will not say on its own, and
        # speaking it would talk over the list it is describing (GATE-12/13).
        self._status = wx.StaticText(panel, label="")
        set_accessible_name(self._status, "Status")
        root.Add(self._status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)

        buttons = self.dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, _PAD)

        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.SetSize((760, 560))

        self._search.Bind(wx.EVT_TEXT, self._on_search)
        self._search.Bind(wx.EVT_TEXT_ENTER, self._on_search_enter)
        self._groups.Bind(wx.EVT_LISTBOX, self._on_group)
        self._results.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_selected)
        self._results.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_activated)

        if self._categories:
            self._groups.SetSelection(0)
            self._show(catalogue.list_by_category(self._categories[0]))

    # ------------------------------------------------------------------ #
    # Showing it
    # ------------------------------------------------------------------ #

    def show(self) -> str | None:
        """Run the dialog. Returns the chosen character, or ``None``."""
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Insert",
            cancel_id=wx.ID_CANCEL,
        )
        # Focus starts in the search box, which is the fastest route for anybody
        # who knows what they want, and one Shift+Tab from the group list for
        # anybody who wants to look around instead.
        self._search.SetFocus()
        try:
            if show_modal_dialog(self.dialog, TITLE) != wx.ID_OK:
                return None
            return self._selected_char()
        finally:
            self.dialog.Destroy()

    # ------------------------------------------------------------------ #
    # Filling the list
    # ------------------------------------------------------------------ #

    def _show(self, rows: list[catalogue.SpecialCharacter], *, status: str = "") -> None:
        self._rows = rows
        self._results.DeleteAllItems()
        for index, row in enumerate(rows):
            self._results.InsertItem(index, row.display)
            self._results.SetItem(index, 1, row.name)
            self._results.SetItem(index, 2, row.code_point)
        self._status.SetLabel(status or self._count_text(len(rows)))
        self._detail.SetValue("")
        if rows:
            self._results.Select(0)
            self._results.Focus(0)

    @staticmethod
    def _count_text(count: int) -> str:
        noun = "character" if count == 1 else "characters"
        return (
            f"{count} {noun}." if count else "Nothing matched. Try part of a name, or a code point."
        )

    def _selected_char(self) -> str | None:
        index = self._results.GetFirstSelected()
        if 0 <= index < len(self._rows):
            return self._rows[index].char
        return None

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #

    def _on_search(self, _event: wx.CommandEvent) -> None:
        query = self._search.GetValue().strip()
        if query:
            self._show(catalogue.search(query))
            return
        selection = self._groups.GetSelection()
        index = selection if selection != wx.NOT_FOUND else 0
        if self._categories:
            self._show(catalogue.list_by_category(self._categories[index]))

    def _on_search_enter(self, _event: wx.CommandEvent) -> None:
        """Enter in the search box moves to the results rather than accepting.

        Accepting would insert whatever happened to be first, which for a
        half-typed query is a character the user has not heard named yet.
        """
        if self._rows:
            self._results.SetFocus()

    def _on_group(self, _event: wx.CommandEvent) -> None:
        # A live search stays in charge until the box is cleared: changing the
        # group under a search would silently answer a question nobody asked.
        if self._search.GetValue().strip():
            return
        selection = self._groups.GetSelection()
        if selection != wx.NOT_FOUND:
            self._show(catalogue.list_by_category(self._categories[selection]))

    def _on_selected(self, event: wx.ListEvent) -> None:
        index = int(event.GetIndex())
        if 0 <= index < len(self._rows):
            self._detail.SetValue(catalogue.describe(self._rows[index]).detail)

    def _on_activated(self, _event: wx.ListEvent) -> None:
        if self._selected_char() is not None:
            self.dialog.EndModal(wx.ID_OK)


def choose_special_character(
    parent: wx.Window,
    *,
    announce_cb: Callable[[str], None] | None = None,
) -> str | None:
    """Open the picker over *parent*. Returns the chosen character, or ``None``.

    The one entry point both editors call, so neither can drift into its own
    arrangement of the same list. *announce_cb* is the host's own announcer, so
    the one thing this window has to speak reaches the same bridge as the rest
    of the app rather than a second one of its own.
    """
    return SpecialCharacterDialog(parent, announce_cb=announce_cb).show()
