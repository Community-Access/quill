"""The chooser for last session's unsaved work: which of it, and what to drop.

Shared, and shaped exactly like ``session_restore_dialog`` on purpose -- the two
questions arrive within a second of each other at launch, and a person who has
learned one window should not have to learn the other. The decisions behind the
list are wx-free in ``quill/core/recovery_triage.py``.

**Why this replaced a Yes/No.** The old question was one message box: "QuillLite
has unsaved work from 69 documents ... Open them now?" Yes opened sixty-nine
windows. No offered them again next launch. There was no way to say "that one",
no way to say "never these", and no way to find out that sixty-seven of the
sixty-nine were the same four characters -- which was the only fact that made the
decision easy. A message box cannot hold a list, and this question is a list.

**Discarding here really does delete.** Not like Forget in the session window,
which only drops a row: these rows *are* the only copy of the work, so the note
under the buttons says so in those words, and Discard Everything asks once. The
per-row Discard does not ask, because ticking the row is the deliberate act and
a confirmation on every small deletion is how people learn to confirm without
reading.
"""

from __future__ import annotations

from dataclasses import dataclass

import wx

from quill.core.recovery_triage import (
    Recoverable,
    Triage,
    describe_plan,
    is_untitled,
    row_label,
    summarise_recovery,
)
from quill.ui.dialog_contract import (
    apply_modal_ids,
    set_accessible_name,
    show_message_box,
    show_modal_dialog,
)

__all__ = ["RecoveryAnswer", "ask_recovery"]

#: Uniform padding, matching the other shared dialogs.
_PAD = 8

_ID_RESTORE_CHECKED = wx.ID_OK
_ID_NOT_NOW = wx.ID_CANCEL
_ID_RESTORE_ALL = wx.ID_APPLY
_ID_NEVER_UNTITLED = wx.ID_IGNORE
_ID_DISCARD_CHECKED = wx.ID_DELETE
_ID_DISCARD_ALL = wx.ID_CLEAR


@dataclass(slots=True)
class RecoveryAnswer:
    """What the person decided.

    ``restore`` is what to open now. ``discard`` is what to delete -- always the
    caller's job, so the window stays testable without a store to sacrifice.
    ``offer_untitled`` is a new value for the preference, or ``None`` to leave it
    alone. ``spoken`` is the sentence to say afterwards, built here because this
    is the only place that knows both the question and the answer.
    """

    restore: tuple[Recoverable, ...] = ()
    discard: tuple[Recoverable, ...] = ()
    offer_untitled: bool | None = None
    spoken: str = ""


def ask_recovery(parent: object, result: Triage) -> RecoveryAnswer:
    """Ask which of the recovered documents to restore, and which to drop.

    *result* is a :class:`~quill.core.recovery_triage.Triage`, so the rows are
    already deduplicated and the sentence at the top already says what was folded
    away before anybody was asked anything.
    """
    entries = list(result.offer)
    if not entries:
        return RecoveryAnswer()

    dialog = wx.Dialog(
        parent,  # type: ignore[arg-type]
        title="Unsaved Work from Last Time",
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )
    root = wx.BoxSizer(wx.VERTICAL)

    intro = wx.StaticText(dialog, label=summarise_recovery(result))
    intro.SetHelpText(
        "How many documents had unsaved work when this app last closed, and what "
        "was folded away before the list was built -- identical copies, and "
        "anything older than a month."
    )
    root.Add(intro, 0, wx.ALL, _PAD)

    # Real checkboxes in a scrolled panel, never a wx.CheckListBox: a screen
    # reader does not announce the checked state of a check-list row as you
    # arrow through it, which here would hide the one fact the window is about
    # (A11Y-SR-1, and the banned-pattern gate enforces it).
    panel = wx.ScrolledWindow(dialog, style=wx.TAB_TRAVERSAL)
    panel.SetScrollRate(0, 12)
    panel.SetName("Unsaved documents")
    panel.SetHelpText(
        "The unsaved work found from last time, one checkbox each. Space ticks "
        "and unticks. Each row says how much text it holds and when it was last "
        "written, which is how you tell a note you were writing from a scratch "
        "window you abandoned."
    )
    rows = wx.BoxSizer(wx.VERTICAL)
    boxes: list[wx.CheckBox] = []

    def _label(slot: Recoverable) -> str:
        return row_label(slot, result.copies_of(slot))

    for slot in entries:
        box = wx.CheckBox(panel, label=_label(slot))
        # Everything starts ticked, so the person who wants all of it presses
        # Enter and the person who wants one unticks the rest. The old Yes/No
        # could only express this answer, so it stays the cheapest one.
        box.SetValue(True)
        box.SetHelpText(
            "Ticked means Restore Checked opens this document in a window, and "
            "Discard Checked deletes the saved-aside copy. Restoring does not "
            "save anything: the window opens with the work in it and you decide "
            "where it goes."
        )
        set_accessible_name(box, _label(slot))
        rows.Add(box, 0, wx.ALL, _PAD // 2)
        boxes.append(box)
    panel.SetSizer(rows)
    root.Add(panel, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, _PAD)

    # The whole window as a paragraph, rewritten on every tick (asked for by
    # name, 2026-09-21). A list of checkboxes answers "what is here" one row at
    # a time and never answers "what happens when I press the button" at all --
    # and that second question is the one somebody is actually asking, because
    # the buttons are the irreversible part. Sighted users assemble the answer
    # by glancing down the list; assembling it by ear costs a pass through every
    # row, and the pass has to be repeated after every tick.
    #
    # A read-only multiline TextCtrl rather than a StaticText: a text control is
    # focusable, so it can be Tabbed to and read at the reader's own pace with
    # arrow keys, and a long StaticText can only be heard once, whole, when it
    # happens to be announced. TE_READONLY, so nothing here can be typed into.
    summary_label = wx.StaticText(dialog, label="What this would &do:")
    root.Add(summary_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
    summary = wx.TextCtrl(
        dialog,
        value="",
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
        size=(-1, 160),
    )
    summary.SetHelpText(
        "A read-only description of everything in this window: what was tidied "
        "away before the list was built, what each row holds and when it was "
        "written, and exactly what each button would do with the boxes as they "
        "are ticked right now. It is rewritten every time you tick or untick a "
        "row, so it always describes what would happen if you pressed a button "
        "at this moment. Read it with the arrow keys; nothing here can be typed "
        "into or changed."
    )
    set_accessible_name(summary, "What this would do")
    root.Add(summary, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)

    note = wx.StaticText(
        dialog,
        label=(
            "Restoring opens the work in a window; it is still unsaved until you "
            "save it. Discarding deletes the saved-aside copy, and nothing else "
            "has one."
        ),
    )
    note.SetHelpText(
        "The two halves of this window. Restoring is always safe. Discarding is "
        "the only action here that loses anything, and what it loses is the "
        "copy this window is offering."
    )
    root.Add(note, 0, wx.ALL, _PAD)

    restoring = wx.BoxSizer(wx.HORIZONTAL)
    restore_checked = wx.Button(dialog, _ID_RESTORE_CHECKED, "&Restore Checked")
    restore_checked.SetHelpText("Open the ticked documents. Everything else is kept for next time.")
    restore_all = wx.Button(dialog, _ID_RESTORE_ALL, "Restore &All")
    restore_all.SetHelpText("Open every document in this list, whether or not it is ticked.")
    # No access key on Not Now: Escape already serves it (GATE-14).
    not_now = wx.Button(dialog, _ID_NOT_NOW, "Not Now")
    not_now.SetHelpText(
        "Open nothing and delete nothing. The same work is offered again next time."
    )
    for button in (restore_checked, restore_all, not_now):
        restoring.Add(button, 0, wx.RIGHT, _PAD // 2)
    root.Add(restoring, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)

    dropping = wx.BoxSizer(wx.HORIZONTAL)
    discard_checked = wx.Button(dialog, _ID_DISCARD_CHECKED, "&Discard Checked")
    discard_checked.SetHelpText(
        "Delete the saved-aside copy of the ticked documents. The files they came "
        "from, if any, are not touched."
    )
    discard_all = wx.Button(dialog, _ID_DISCARD_ALL, "Discard &Everything")
    discard_all.SetHelpText(
        "Delete every saved-aside copy in this list, so none of it is offered "
        "again. Asks once before it does."
    )
    never_untitled = wx.Button(dialog, _ID_NEVER_UNTITLED, "&Never Offer Untitled")
    never_untitled.SetHelpText(
        "Restore the ticked documents, then stop offering unsaved work from "
        "windows that never had a file -- now and in future, which means those "
        "copies are discarded rather than kept. The setting is Offer untitled "
        "unsaved work, in preferences."
    )
    for button in (discard_checked, discard_all, never_untitled):
        dropping.Add(button, 0, wx.RIGHT, _PAD // 2)
    root.Add(dropping, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)

    # Only ID_OK and ID_CANCEL end a modal by themselves; the rest must say so,
    # or the button looks dead.
    for button, answer in (
        (restore_all, _ID_RESTORE_ALL),
        (never_untitled, _ID_NEVER_UNTITLED),
        (discard_checked, _ID_DISCARD_CHECKED),
        (discard_all, _ID_DISCARD_ALL),
    ):
        button.Bind(
            wx.EVT_BUTTON,
            lambda _event, _answer=answer: dialog.EndModal(_answer),
        )

    dialog.SetSizerAndFit(root)
    apply_modal_ids(
        dialog,
        affirmative_id=_ID_RESTORE_CHECKED,
        affirmative_label="&Restore Checked",
        cancel_id=_ID_NOT_NOW,
        cancel_label="Not Now",
    )
    dialog.SetDefaultItem(restore_checked)
    if boxes:
        boxes[0].SetFocus()
    else:
        restore_checked.SetFocus()

    live = list(entries)
    discarded: list[Recoverable] = []

    def _checked() -> tuple[Recoverable, ...]:
        return tuple(slot for slot, box in zip(live, boxes, strict=False) if box.GetValue())

    def _refresh_summary(_event: object = None) -> None:
        """Rewrite the read-only description for the boxes as they stand now.

        Bound to every checkbox, and called again after a discard rebuilds the
        rows. ``ChangeValue`` rather than ``SetValue``: the latter fires a text
        event, and a read-only field that announces itself on every tick would
        talk over the reader saying "checked" -- which is the announcement the
        person actually asked for by pressing Space (GATE-13).
        """
        summary.ChangeValue(
            describe_plan(
                _live_triage(),
                tuple(box.GetValue() for box in boxes),
            )
        )

    def _live_triage() -> Triage:
        """The triage as it now stands, after any discards in this window.

        Rebuilt rather than kept, because ``result`` describes the list the
        window opened with and rows can leave it. The counts of what was tidied
        beforehand are carried across: they are still true, and they are the
        part somebody most needs to not have silently vanish.
        """
        return Triage(
            offer=tuple(live),
            duplicates=result.duplicates,
            stale=result.stale,
            untitled=result.untitled,
            copies=result.copies,
        )

    for box in boxes:
        box.Bind(wx.EVT_CHECKBOX, _refresh_summary)
    _refresh_summary()

    def _refill() -> None:
        """Rebuild the rows after a discard, and put focus somewhere real.

        Destroying the row that had focus is how a dialog goes silent: nothing
        is focused, so the reader announces nothing.
        """
        for box in boxes:
            box.Destroy()
        boxes.clear()
        for slot in live:
            box = wx.CheckBox(panel, label=_label(slot))
            box.SetValue(True)
            set_accessible_name(box, _label(slot))
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
            outcome = show_modal_dialog(dialog, "Unsaved Work from Last Time")

            if outcome == _ID_DISCARD_CHECKED:
                doomed = _checked()
                if not doomed:
                    # Says so rather than doing nothing: a button that answers
                    # silently is one somebody presses twice.
                    intro.SetLabel("Nothing is ticked, so nothing was discarded.")
                    continue
                discarded.extend(doomed)
                dropped = {id(slot) for slot in doomed}
                live = [slot for slot in live if id(slot) not in dropped]
                _refill()
                intro.SetLabel(_after_discard(len(doomed), len(live)))
                if not live:
                    break
                continue

            if outcome == _ID_DISCARD_ALL:
                if not _confirm_discard_all(dialog, len(live)):
                    continue
                discarded.extend(live)
                count = len(live)
                live = []
                _refill()
                intro.SetLabel(_after_discard(count, 0))
                break

            if outcome == _ID_RESTORE_ALL:
                return _answer(tuple(live), tuple(discarded), None)

            if outcome == _ID_NEVER_UNTITLED:
                chosen = _checked()
                # The preference says untitled work is not offered, which means
                # not kept either -- the setting's own wording says so, and
                # keeping it would be a promise nothing could ever redeem.
                kept = {id(slot) for slot in chosen}
                doomed = tuple(slot for slot in live if is_untitled(slot) and id(slot) not in kept)
                return _answer(chosen, tuple(discarded) + doomed, False)

            if outcome == _ID_RESTORE_CHECKED:
                return _answer(_checked(), tuple(discarded), None)

            # Not Now, Escape, or the close button.
            return _answer((), tuple(discarded), None, restored_nothing=True)
    finally:
        dialog.Destroy()

    return _answer((), tuple(discarded), None, restored_nothing=True)


def _after_discard(dropped: int, remaining: int) -> str:
    """The line the list header becomes after a discard. Counts, then what is left."""
    noun = "document" if dropped == 1 else "documents"
    if remaining <= 0:
        return f"Discarded {dropped} {noun}. Nothing is left to offer."
    left = "1 document" if remaining == 1 else f"{remaining} documents"
    return f"Discarded {dropped} {noun}. {left} still listed."


def _confirm_discard_all(parent: wx.Window, count: int) -> bool:
    """Ask once before deleting every copy. The one confirmation in this window."""
    noun = "document" if count == 1 else "documents"
    answer = show_message_box(
        f"Delete the saved-aside copy of all {count} {noun}?\n\n"
        "This is the only copy of that work. Files you have saved are not "
        "touched.",
        "Unsaved Work from Last Time",
        # NO_DEFAULT, so Enter answers No. This is the one button in the window
        # that destroys anything, and somebody pressing Enter reflexively on a
        # dialog they have not yet heard must not lose a month of unsaved work.
        wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        parent,
    )
    return answer == wx.YES


def _answer(
    restore: tuple[Recoverable, ...],
    discard: tuple[Recoverable, ...],
    offer_untitled: bool | None,
    *,
    restored_nothing: bool = False,
) -> RecoveryAnswer:
    """Assemble the answer, including the sentence to say afterwards."""
    parts: list[str] = []
    if discard:
        noun = "document" if len(discard) == 1 else "documents"
        parts.append(f"Discarded unsaved work from {len(discard)} {noun}.")
    if restored_nothing and not restore:
        parts.append("Nothing restored. The rest is offered again next time.")
    if offer_untitled is False:
        parts.append(
            "Untitled unsaved work will not be offered again. The setting is "
            "Offer untitled unsaved work."
        )
    return RecoveryAnswer(
        restore=restore,
        discard=discard,
        offer_untitled=offer_untitled,
        spoken=" ".join(parts).strip(),
    )
