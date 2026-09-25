"""The chooser for last session's documents: which ones, and which to forget.

Shared by QUILL and QuillLite, because it is the same question in both and the
answers are computed in one wx-free place (``quill/core/session_restore.py``).

**Why a list with checkboxes rather than a Yes/No.** Yes/No is what both editors
effectively had -- the boolean setting -- and it cannot express the thing people
actually want, which is "that one and that one, not the other two". Four windows
appearing at once is four things to identify before any work; being asked to name
them first is faster than arrowing through them afterwards, and it is the only
version where the answer can be *partial*.

**Every answer is reversible, and none is destructive.** Not Now keeps the list
exactly as it was. Forget drops rows from the list and **touches nothing on
disk** -- the sentence under the buttons says so rather than a warning box saying
it, because a warning on a harmless action is how people learn to click through
the warnings that matter (decided with Jeff, 2026-09-19).

**Never Ask Again has a twin, and that is what makes it reversible.** It used to
be the one door in this window that only opened one way: it set the preference to
*never*, nothing else in either editor wrote that preference back, and the button's
own help text sent you to look for a setting ("Reopen last session") that is a
different setting and does a different thing. So the window stopped appearing and
there was no supported way to get it back -- from a button somebody presses in a
hurry, which is exactly the population that then needs it back. **Ask Me Next
Time** puts the preference back to the shipped answer, and exactly one of the pair
is ever enabled: the other is greyed rather than hidden, so a reader arriving on it
is told it is unavailable instead of hunting a window for a button that was removed.

**A missing file is a row, not an omission.** The silent path skipped a file that
had gone, which is fine for one deleted on purpose and useless for one that
*moved*: nothing was said, nothing appeared, and that is indistinguishable from
"it opened and I have not found it yet". Those rows say so, cannot be checked for
opening, and are the ones Forget is usually for.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import wx

from quill.core.session_restore import (
    ASK_NEVER,
    ASK_WHEN_IT_MATTERS,
    SessionEntry,
    describe_session_plan,
    missing,
    summarise,
)
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name, show_modal_dialog

__all__ = ["SessionRestoreAnswer", "ask_session_restore"]

#: Uniform padding, matching the other shared dialogs.
_PAD = 8

#: The answers the dialog can give back. ``wx`` ids for the three that end it
#: through the standard machinery; the rest are handled in the loop.
_ID_OPEN_CHECKED = wx.ID_OK
_ID_NOT_NOW = wx.ID_CANCEL
_ID_OPEN_ALL = wx.ID_APPLY
_ID_NEVER_ASK = wx.ID_IGNORE
_ID_ASK_AGAIN = wx.ID_RETRY


@dataclass(slots=True)
class SessionRestoreAnswer:
    """What the person decided.

    ``open_paths`` is what to open now, in the order the list held them.
    ``remembered`` is the list to save back -- always set, because Forget and
    Clear change it even when nothing is opened. ``ask_mode`` is a new value for
    the preference, or ``""`` to leave it alone.
    """

    open_paths: tuple[str, ...] = ()
    remembered: tuple[str, ...] = ()
    ask_mode: str = ""
    #: What to say afterwards. The dialog builds it because it is the only place
    #: that knows both what was asked and what was answered.
    spoken: str = ""
    forgotten: int = 0
    _entries: tuple[SessionEntry, ...] = field(default=(), repr=False)


def ask_session_restore(
    parent: object,
    entries: tuple[SessionEntry, ...],
    *,
    mode: str = ASK_WHEN_IT_MATTERS,
) -> SessionRestoreAnswer:
    """Ask which of *entries* to reopen, and which to forget.

    Returns a :class:`SessionRestoreAnswer` whose ``remembered`` is what the
    caller should save, whatever the person chose -- so a caller that saves it
    unconditionally is correct, and one that forgets to is the only way a Forget
    can be lost.

    *mode* is the caller's current ``session_restore_ask``. It decides which
    half of the Never Ask Again / Ask Me Next Time pair is offered; the default
    is the shipped value, so an older caller behaves exactly as it did.
    """
    if not entries:
        return SessionRestoreAnswer(remembered=(), spoken="")

    dialog = wx.Dialog(
        parent,  # type: ignore[arg-type]
        title="Reopen Last Session",
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )
    root = wx.BoxSizer(wx.VERTICAL)

    intro = wx.StaticText(dialog, label=summarise(entries))
    intro.SetHelpText(
        "How many documents were open when this app last closed, and how many of "
        "their files are no longer where they were."
    )
    root.Add(intro, 0, wx.ALL, _PAD)

    # One real wx.CheckBox per row inside a scrolled panel, NOT a
    # wx.CheckListBox (A11Y-SR-1, and the banned-pattern gate caught this
    # version of the window before it shipped): a screen reader does not
    # announce the checked state of a check-list row as you arrow through it,
    # which in this window would hide the single fact the whole window is about.
    # Tab and the arrow keys reach a real checkbox, and it says "checked" or
    # "not checked" every time.
    panel = wx.ScrolledWindow(dialog, style=wx.TAB_TRAVERSAL)
    panel.SetScrollRate(0, 12)
    panel.SetName("Documents from last time")
    panel.SetHelpText(
        "The documents that were open last time, one checkbox each. Space ticks and "
        "unticks. Ticked rows are the ones Open Checked opens and Forget Checked "
        "removes from this list. A row whose file has gone says so and cannot be "
        "reopened."
    )
    rows = wx.BoxSizer(wx.VERTICAL)
    boxes: list[wx.CheckBox] = []
    for entry in entries:
        box = wx.CheckBox(panel, label=entry.label)
        # Everything that can be opened starts ticked: the person who wants all
        # of it presses Enter, and the person who wants two unticks two. A row
        # that cannot be opened starts unticked and stays unticked, so Open
        # Checked never promises something it must then decline.
        box.SetValue(entry.exists)
        box.Enable(True)
        box.SetHelpText(
            (
                f"{entry.name}, at {entry.path}. Ticked means Open Checked opens it "
                "and Forget Checked takes it off this list."
            )
            if entry.exists
            else (
                f"{entry.name} is no longer at {entry.path}, so it cannot be "
                "reopened. Forget Checked takes the row off this list; the row is "
                "all that goes."
            )
        )
        set_accessible_name(box, entry.label)
        rows.Add(box, 0, wx.ALL, _PAD // 2)
        boxes.append(box)
    panel.SetSizer(rows)
    root.Add(panel, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, _PAD)

    # The twin of the recovery chooser's field, added the same day and for the
    # same reason: the checkboxes say what is here, one row at a time, and
    # nothing in the window says what pressing a button would actually do. A
    # read-only multiline TextCtrl rather than a StaticText, because a text
    # control is focusable -- it can be Tabbed to and read at the reader's own
    # pace with the arrow keys, where a long StaticText can only be heard once,
    # whole, if it happens to be announced at all.
    summary_label = wx.StaticText(dialog, label="What this woul&d do:")
    root.Add(summary_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
    summary = wx.TextCtrl(
        dialog,
        value="",
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
        size=(-1, 160),
    )
    summary.SetHelpText(
        "A read-only description of this whole window: every remembered "
        "document, whether its file is still there, and exactly what each "
        "button would do with the boxes as they are ticked right now. It is "
        "rewritten every time you tick or untick a row. Read it with the arrow "
        "keys; nothing here can be typed into or changed."
    )
    set_accessible_name(summary, "What this would do")
    root.Add(summary, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)

    note = wx.StaticText(
        dialog,
        label=(
            "Forgetting only removes a row from this list. The documents "
            "themselves are never touched."
        ),
    )
    note.SetHelpText(
        "Nothing in this window can delete a file or change what is in one. "
        "Forget Checked and Clear the List only change what this app offers to "
        "reopen next time."
    )
    root.Add(note, 0, wx.ALL, _PAD)

    # Two rows of buttons: what to open, then what to remember. Opening is what
    # somebody came here to do, so it is first and it holds the default.
    opening = wx.BoxSizer(wx.HORIZONTAL)
    open_checked = wx.Button(dialog, _ID_OPEN_CHECKED, "&Open Checked")
    open_checked.SetHelpText("Open the ticked documents and leave the list as it is.")
    open_all = wx.Button(dialog, _ID_OPEN_ALL, "Open &All")
    open_all.SetHelpText(
        "Open every document whose file is still there, whether or not it is ticked."
    )
    # No access key on Not Now: it is the Escape answer, and Escape already
    # serves it (GATE-14).
    not_now = wx.Button(dialog, _ID_NOT_NOW, "Not Now")
    not_now.SetHelpText(
        "Open nothing and change nothing. The same documents are offered next time."
    )
    for button in (open_checked, open_all, not_now):
        opening.Add(button, 0, wx.RIGHT, _PAD // 2)
    root.Add(opening, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)

    keeping = wx.BoxSizer(wx.HORIZONTAL)
    forget_checked = wx.Button(dialog, wx.ID_DELETE, "&Forget Checked")
    forget_checked.SetHelpText(
        "Remove the ticked rows from this list so they stop being offered. The "
        "files stay exactly where they are."
    )
    clear_list = wx.Button(dialog, wx.ID_CLEAR, "&Clear the List")
    clear_list.SetHelpText(
        "Forget every row. Nothing is reopened next time until you open "
        "something yourself. No file is touched."
    )
    never_ask = wx.Button(dialog, _ID_NEVER_ASK, "&Never Ask Again")
    never_ask.SetHelpText(
        "Reopen last session's documents from now on without asking, and open "
        "the ticked ones now. Ask Me Next Time, beside this button, is how you "
        "undo it: open this window from File, Reopen Last Session and press that."
    )
    ask_again = wx.Button(dialog, _ID_ASK_AGAIN, "Ask Me Ne&xt Time")
    ask_again.SetHelpText(
        "Undo Never Ask Again: be asked about last session again, the way a new "
        "install does -- when there are several documents, or one whose file has "
        "moved. The ticked documents open now as well."
    )
    # Exactly one of the pair is live, and the other is greyed rather than
    # removed. A button that vanishes leaves somebody hunting the window for it;
    # a greyed one announces itself as unavailable the moment they arrive on it,
    # which is the same choice the two tag pickers make.
    asking_now = mode != ASK_NEVER
    never_ask.Enable(asking_now)
    ask_again.Enable(not asking_now)
    for button in (forget_checked, clear_list, never_ask, ask_again):
        keeping.Add(button, 0, wx.RIGHT, _PAD // 2)
    root.Add(keeping, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)

    # Only ID_OK and ID_CANCEL end a modal by themselves; the other four have
    # to say so, or the button looks dead.
    for button, answer in (
        (open_all, _ID_OPEN_ALL),
        (never_ask, _ID_NEVER_ASK),
        (ask_again, _ID_ASK_AGAIN),
        (forget_checked, wx.ID_DELETE),
        (clear_list, wx.ID_CLEAR),
    ):
        button.Bind(
            wx.EVT_BUTTON,
            lambda _event, _answer=answer: dialog.EndModal(_answer),
        )

    dialog.SetSizerAndFit(root)
    apply_modal_ids(
        dialog,
        affirmative_id=_ID_OPEN_CHECKED,
        affirmative_label="&Open Checked",
        cancel_id=_ID_NOT_NOW,
        cancel_label="Not Now",
    )
    dialog.SetDefaultItem(open_checked)
    if boxes:
        boxes[0].SetFocus()
    else:
        open_checked.SetFocus()

    live = list(entries)
    forgotten_total = 0

    def _checked() -> tuple[SessionEntry, ...]:
        return tuple(entry for entry, box in zip(live, boxes, strict=False) if box.GetValue())

    def _refresh_summary(_event: object = None) -> None:
        """Rewrite the read-only description for the boxes as they stand now.

        ``ChangeValue`` rather than ``SetValue``: the latter fires a text event,
        and a read-only field that announced itself on every tick would talk
        over the reader saying "checked" -- which is the announcement the person
        asked for by pressing Space (GATE-13).
        """
        summary.ChangeValue(
            describe_session_plan(
                tuple(live),
                tuple(box.GetValue() for box in boxes),
            )
        )

    for box in boxes:
        box.Bind(wx.EVT_CHECKBOX, _refresh_summary)
    _refresh_summary()

    def _refill() -> None:
        """Rebuild the rows after a Forget, and put focus somewhere real.

        Destroying the row that had focus is how a dialog goes silent: the reader
        announces nothing because nothing is focused. Focus moves to the first
        surviving row, or to the button that is about to be the only thing left.
        """
        for box in boxes:
            box.Destroy()
        boxes.clear()
        for entry in live:
            box = wx.CheckBox(panel, label=entry.label)
            box.SetValue(entry.exists)
            set_accessible_name(box, entry.label)
            box.Bind(wx.EVT_CHECKBOX, _refresh_summary)
            rows.Add(box, 0, wx.ALL, _PAD // 2)
            boxes.append(box)
        panel.SetSizer(rows)
        panel.Layout()
        rows.Layout()
        _refresh_summary()
        if boxes:
            boxes[0].SetFocus()
        else:
            not_now.SetFocus()

    try:
        while True:
            result = show_modal_dialog(dialog, "Reopen Last Session")

            if result == wx.ID_DELETE or result == wx.ID_CLEAR:
                doomed = tuple(live) if result == wx.ID_CLEAR else _checked()
                if not doomed:
                    # Says so rather than doing nothing: a button that answers
                    # silently is one somebody presses twice.
                    intro.SetLabel("Nothing is ticked, so nothing was forgotten.")
                    continue
                dropped = {entry.path for entry in doomed}
                live = [entry for entry in live if entry.path not in dropped]
                forgotten_total += len(doomed)
                _refill()
                intro.SetLabel(summarise(tuple(live)))
                if not live:
                    break
                continue

            if result == _ID_OPEN_ALL:
                chosen = tuple(entry for entry in live if entry.exists)
                return _answer(chosen, live, forgotten_total, ask_mode="")

            if result == _ID_NEVER_ASK:
                return _answer(_checked(), live, forgotten_total, ask_mode=ASK_NEVER)

            if result == _ID_ASK_AGAIN:
                return _answer(_checked(), live, forgotten_total, ask_mode=ASK_WHEN_IT_MATTERS)

            if result == _ID_OPEN_CHECKED:
                return _answer(_checked(), live, forgotten_total, ask_mode="")

            # Not Now, Escape, or the close button.
            return _answer((), live, forgotten_total, ask_mode="", opened_nothing=True)
    finally:
        dialog.Destroy()

    return _answer((), live, forgotten_total, ask_mode="", opened_nothing=True)


def _answer(
    chosen: tuple[SessionEntry, ...],
    live: list[SessionEntry],
    forgotten: int,
    *,
    ask_mode: str,
    opened_nothing: bool = False,
) -> SessionRestoreAnswer:
    """Assemble the answer, including the sentence to say afterwards."""
    from quill.core.session_restore import describe_forgotten

    remembered = tuple(entry.path for entry in live)
    parts: list[str] = []
    if forgotten:
        parts.append(describe_forgotten(forgotten, len(remembered)))
    if opened_nothing and not chosen:
        parts.append("Nothing reopened. The same documents are offered next time.")
    if ask_mode == ASK_NEVER:
        parts.append(
            "Last session will reopen without asking from now on. "
            "Ask Me Next Time, in this window, puts that back."
        )
    if ask_mode == ASK_WHEN_IT_MATTERS:
        parts.append("You will be asked about last session again when it matters.")
    skipped = len(missing(tuple(live)))
    if chosen and skipped:
        noun = "file" if skipped == 1 else "files"
        parts.append(f"{skipped} {noun} in the list are no longer there and were left alone.")
    return SessionRestoreAnswer(
        open_paths=tuple(entry.path for entry in chosen),
        remembered=remembered,
        ask_mode=ask_mode,
        spoken=" ".join(parts),
        forgotten=forgotten,
        _entries=tuple(live),
    )
