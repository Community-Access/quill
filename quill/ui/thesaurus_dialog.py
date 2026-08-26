"""The Thesaurus picker: senses on the left, that sense's words on the right.

Replaces a single flat list. The list was the wrong shape for the data: "light"
has 45 usable senses and 168 members, and one list mixes weight, colour and
illumination with nothing to say where one ends and the next begins. Reaching a
word in the third sense took fifteen keystrokes and gave no way to tell you had
arrived.

Three decisions here are load-bearing, and each is easy to undo by accident.

**Nothing is announced when the sense selection changes.** QUILL speaks through
``prism_bridge``, which calls ``speak(message, interrupt=False)`` -- so an
announcement *queues behind* whatever the screen reader is already saying
rather than replacing it. One announcement per arrow-press leaves somebody
holding Down five utterances behind their own cursor, hearing the first sense
while sitting on the sixth. Silence here is correct: the reader has already
read the row, which is the only thing that changed.

**The synonym pane's context arrives through its label, not through speech.**
On wxMSW a list box takes its accessible name from the static text created
immediately before it, queried live when focus lands -- ``SetName`` is inert
there (see :mod:`quill.ui.accessible_names`). So the label is rewritten on
every sense change: silent while focus is elsewhere, spoken exactly once when
the user tabs in. **The two labels must keep being created immediately before
their own list**, because "immediately before" means Z-order, and Z-order here
is creation order.

**This holds a ``wx.Dialog``; it does not subclass one.**
``MainFrame._show_modal_dialog`` lands initial focus on the primary content
control rather than the OK button, but it is guarded by ``type(dialog) is
wx.Dialog`` -- an identity check, not ``isinstance``. A subclass silently loses
initial focus and the dialog opens on a button instead of the senses.

The whole speech budget for this surface is one announcement, on Copy, when
nothing else is talking.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.ui.accessible_names import set_accessible_name
from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids


class ThesaurusDialog:
    """A two-pane thesaurus picker.

    Parameters
    ----------
    parent:
        wx parent window.
    word:
        The headword being looked up, for the title and the labels.
    senses:
        :class:`quill.core.thesaurus.SenseRow` values, already grouped and
        ordered by the core module. This class decides nothing about which
        words are offered or in what order -- that policy is pure, wx-free and
        unit-tested in ``core.thesaurus.sense_rows``.
    allow_replace:
        False when the lookup came from a typed word rather than the document,
        so there is nothing to replace. Replace is then disabled and Copy
        becomes the default button -- a disabled default button is a dead Enter
        key, which is a worse trap in a dialog than in a form.
    show_modal_dialog:
        ``MainFrame._show_modal_dialog``. Passed in rather than reached for, so
        this class owns its own presentation and every modal in the app still
        goes through the one hardened gate.
    on_copy:
        Called with the chosen term. Returns True when the clipboard accepted
        it, so the announcement can tell the truth.
    announce:
        Speech callback, used exactly once (on Copy).
    """

    def __init__(
        self,
        parent: Any,
        word: str,
        senses: Sequence[Any],
        *,
        allow_replace: bool,
        show_modal_dialog: Callable[..., int],
        on_copy: Callable[[str], bool],
        announce: Callable[[str], None],
    ) -> None:
        import wx

        self._wx = wx
        self._word = word
        self._senses = list(senses)
        self._show_modal = show_modal_dialog
        self._on_copy = on_copy
        self._announce = announce
        #: The term to insert, set only when the user chooses Replace.
        self.chosen_term: str = ""

        self.dialog = wx.Dialog(
            parent,
            title=f'Thesaurus: "{word}"',
            size=(760, 460),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        root = wx.BoxSizer(wx.VERTICAL)
        panes = wx.BoxSizer(wx.HORIZONTAL)

        # -- senses ------------------------------------------------------
        # The label is created before its list box and stays that way: on
        # wxMSW the accessible name comes from the preceding static control.
        senses_box = wx.BoxSizer(wx.VERTICAL)
        self._senses_label = wx.StaticText(self.dialog, label=self._senses_label_text())
        senses_box.Add(self._senses_label, 0, wx.BOTTOM, 4)
        self._sense_list = wx.ListBox(
            self.dialog, choices=[sense.label for sense in self._senses], style=wx.LB_SINGLE
        )
        set_accessible_name(self._sense_list, self._senses_label)
        senses_box.Add(self._sense_list, 1, wx.EXPAND)
        panes.Add(senses_box, 1, wx.EXPAND | wx.RIGHT, 8)

        # -- the selected sense's words ----------------------------------
        words_box = wx.BoxSizer(wx.VERTICAL)
        self._words_label = wx.StaticText(self.dialog, label="&Words:")
        words_box.Add(self._words_label, 0, wx.BOTTOM, 4)
        self._word_list = wx.ListBox(self.dialog, choices=[], style=wx.LB_SINGLE)
        set_accessible_name(self._word_list, self._words_label)
        words_box.Add(self._word_list, 1, wx.EXPAND)
        panes.Add(words_box, 1, wx.EXPAND)

        root.Add(panes, 1, wx.EXPAND | wx.ALL, 10)

        # -- actions -----------------------------------------------------
        buttons = wx.StdDialogButtonSizer()
        self._replace_btn = wx.Button(self.dialog, wx.ID_OK, "&Replace")
        self._copy_btn = wx.Button(self.dialog, wx.ID_COPY, "&Copy")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        buttons.AddButton(self._replace_btn)
        buttons.AddButton(close_btn)
        buttons.Realize()
        # Copy sits outside the standard sizer: it is neither the affirmative
        # nor the escape action, and StdDialogButtonSizer would reposition it.
        # A stretch spacer rather than wx.ALIGN_RIGHT, which the banned-pattern
        # gate refuses in quill/ui (A11Y-4): an aligned sizer does not expand,
        # so the row stops tracking the dialog when it is resized.
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer(1)
        row.Add(self._copy_btn, 0, wx.RIGHT, 8)
        row.Add(buttons, 0)
        root.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.dialog.SetSizer(root)

        self._replace_allowed = bool(allow_replace)
        if self._replace_allowed:
            self._replace_btn.SetDefault()
        else:
            self._replace_btn.Enable(False)
            self._copy_btn.SetDefault()

        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="&Replace",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
        )

        self._sense_list.Bind(wx.EVT_LISTBOX, self._on_sense_changed)
        # Enter on a sense means "drill in", not "replace": a sense is not a
        # word. This gives Enter and Tab the same meaning.
        apply_listbox_activation(self._sense_list, lambda _event: self._word_list.SetFocus())
        apply_listbox_activation(self._word_list, lambda _event: self._activate_word())
        self._copy_btn.Bind(wx.EVT_BUTTON, lambda _event: self._copy_selected())
        self._replace_btn.Bind(wx.EVT_BUTTON, lambda _event: self._replace_selected())

        if self._senses:
            self._sense_list.SetSelection(0)
            self._show_sense(0)

    # ------------------------------------------------------------------
    # labels
    # ------------------------------------------------------------------

    def _senses_label_text(self) -> str:
        count = len(self._senses)
        return f'Se&nses of "{self._word}" ({count}):'

    def _on_sense_changed(self, _event: Any) -> None:
        """Repopulate the words pane. Deliberately silent -- see the module docstring."""
        self._show_sense(self._sense_list.GetSelection())

    def _show_sense(self, index: int) -> None:
        wx = self._wx
        if index == wx.NOT_FOUND or not (0 <= index < len(self._senses)):
            self._word_list.Set([])
            return
        sense = self._senses[index]
        self.dialog.Freeze()
        try:
            # Set() and SetSelection() are programmatic and emit no EVT_LISTBOX,
            # so there is no reentrancy to guard against here.
            self._word_list.Set([label for label, _ in sense.rows])
            if sense.rows:
                self._word_list.SetSelection(0)
            # The context the user hears when they tab in. Layout() because the
            # label's width changes with the text and a wider string is
            # otherwise clipped -- cosmetic, but it looks broken.
            self._words_label.SetLabel(
                f"&Words for {sense.part_of_speech} sense {index + 1} ({len(sense.rows)}):"
            )
            set_accessible_name(self._word_list, self._words_label)
            self.dialog.Layout()
        finally:
            self.dialog.Thaw()

    # ------------------------------------------------------------------
    # actions
    # ------------------------------------------------------------------

    def _selected_term(self) -> str:
        """The term to act on -- never the displayed label.

        The two differ on purpose: a label may read "opposite: heavy", and
        replacing "light" with "opposite: heavy" would be a funny bug in a
        serious place.
        """
        wx = self._wx
        sense_index = self._sense_list.GetSelection()
        word_index = self._word_list.GetSelection()
        if wx.NOT_FOUND in (sense_index, word_index):
            return ""
        if not (0 <= sense_index < len(self._senses)):
            return ""
        rows = self._senses[sense_index].rows
        if not (0 <= word_index < len(rows)):
            return ""
        return rows[word_index][1]

    def _activate_word(self) -> None:
        """Enter on a word: replace when there is somewhere to replace, else copy."""
        if self._replace_allowed:
            self._replace_selected()
        else:
            self._copy_selected()

    def _replace_selected(self) -> None:
        term = self._selected_term()
        if not term or not self._replace_allowed:
            return
        self.chosen_term = term
        self.dialog.EndModal(self._wx.ID_OK)

    def _copy_selected(self) -> None:
        """Copy and stay open -- somebody comparing words wants a second look.

        The one announcement this dialog makes. It is safe here and nowhere
        else: the user has just pressed a key, focus is settled, and nothing
        else is speaking, so it cannot queue behind a row announcement.
        """
        term = self._selected_term()
        if not term:
            return
        if self._on_copy(term):
            self._announce(f'Copied "{term}" to the clipboard.')

    # ------------------------------------------------------------------

    def show_modal(self) -> str:
        """Show the picker; return the term to insert, or "" for anything else.

        "Anything else" covers Close, Escape, and the case where the user only
        copied -- Copy reports for itself and leaves the dialog open, so
        reaching here after one means they were done.
        """
        result = self._show_modal(self.dialog, "Thesaurus")
        return self.chosen_term if result == self._wx.ID_OK else ""

    def Destroy(self) -> None:
        self.dialog.Destroy()
