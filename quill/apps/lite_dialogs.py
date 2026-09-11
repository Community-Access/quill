"""QuillLite's small windows: go to line, headings, bookmarks, file format, about.

Six surfaces, each one screen, each built to QUILL's own dialog contract rather
than to a private convention:

* every modal goes through :func:`quill.ui.dialog_contract.show_modal_dialog`,
  which installs F1 context help and infers the accessible names macOS
  VoiceOver needs -- but **without** its optional announce hook: the screen
  reader announces a dialog opening and closing by itself, and a spoken
  "Entered/Exited <name> dialog" on top of that is the over-announcing GATE-13
  exists to catch (reported: leaving Preferences talked twice);
* :func:`~quill.ui.dialog_contract.apply_modal_ids` gives Enter and Escape their
  jobs, and :func:`~quill.ui.dialog_contract.bind_close_button` makes a Close
  button actually close -- a ``wx.Dialog`` answers ``ID_CANCEL`` for free but a
  ``wx.Frame`` does not, and a button that looks like the way out and is not is
  worse than no button;
* every field is preceded, immediately, by a ``wx.StaticText`` carrying its
  ``&`` mnemonic, which is where NVDA and JAWS take the field's name from;
* **OK, Cancel and Close carry no mnemonic at all.** Enter and Escape already
  serve them, and every letter they give up resolves a collision elsewhere in
  the window (GATE-14);
* every helpable control carries its own ``SetHelpText`` at the construction
  site, which is what the F1 audit can verify (GATE-LITE-HELP).

Nothing here knows anything about documents. Each surface takes what it needs
and hands back a value or calls a callback, so the window owns the decisions and
these own the screen.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.lite.textfile import ENCODING_CHOICES, NEWLINE_CHOICES
from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    bind_close_button,
    set_accessible_name,
    show_modal_dialog,
)

__all__ = [
    "ask_line_number",
    "choose_bookmark",
    "choose_from_rows",
    "choose_heading",
    "edit_file_format",
    "show_text_window",
]

#: Uniform padding. One number, so nothing drifts by two pixels per dialog.
_PAD = 8


def _plain_label(label: str) -> str:
    """A label as an accessible name: no mnemonic ampersand, no trailing colon.

    ``&&`` is a literal ampersand rather than a mnemonic, so it collapses to one
    rather than disappearing -- a field labelled "R&&D" is called "R&D", not "RD".
    """
    out: list[str] = []
    index = 0
    while index < len(label):
        if label[index] == "&":
            if label[index + 1 : index + 2] == "&":
                out.append("&")
                index += 2
                continue
            index += 1
            continue
        out.append(label[index])
        index += 1
    return "".join(out).rstrip(": ")


def _labelled_text(
    parent: wx.Window,
    sizer: wx.Sizer,
    label: str,
    value: str = "",
    *,
    help_text: str = "",
    multiline: bool = False,
) -> wx.TextCtrl:
    """A ``StaticText`` immediately followed by the field it names.

    Immediately is the operative word: Windows screen readers take a field's
    accessible name from the static text created directly before it, so the two
    constructions have to stay adjacent even when a sizer would read more
    naturally the other way round.
    """
    static = wx.StaticText(parent, label=label)
    style = wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 if multiline else 0
    field = wx.TextCtrl(parent, value=value, style=style)
    # Named here rather than left to the modal show path's runtime walker: two
    # of this helper's callers (Find and Replace) are *modeless*, so they never
    # go through that path at all, and a field named only by adjacency is a
    # field macOS VoiceOver announces as "edit" with no name.
    set_accessible_name(field, _plain_label(label))
    if help_text:
        field.SetHelpText(help_text)
    sizer.Add(static, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
    sizer.Add(field, 1 if multiline else 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)
    return field


def ask_line_number(parent: wx.Window, current: int, maximum: int) -> int | None:
    """Ask for a line number. Returns the clamped line, or ``None`` if cancelled.

    Clamped rather than refused: somebody who asks for line 900 of an 800-line
    file wants the end of the file, and an error dialog would be a second thing
    to dismiss on the way there.
    """
    dialog = wx.Dialog(parent, title="Go to line")
    root = wx.BoxSizer(wx.VERTICAL)
    field = _labelled_text(
        dialog,
        root,
        f"&Line number (1 to {maximum}):",
        str(current),
        help_text="Type a line number and press Enter. Past the end takes you to the last line.",
    )
    buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
    root.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, _PAD)
    dialog.SetSizerAndFit(root)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
    field.SetFocus()
    field.SelectAll()
    try:
        if show_modal_dialog(dialog, "Go to line") != wx.ID_OK:
            return None
        try:
            return max(1, min(maximum, int(field.GetValue().strip())))
        except ValueError:
            return None
    finally:
        dialog.Destroy()


def _stack(sizer: wx.Sizer, label: wx.StaticText, control: wx.Window) -> None:
    """Add a label and the control it names, in that order.

    The ordering rule is not cosmetic and it is not about the sizer. Windows
    screen readers infer a control's accessible name from the ``wx.StaticText``
    **constructed immediately before it**, so the label has to be built first as
    well as placed first. Getting that backwards is silent: the control still
    appears, still takes focus, and is announced as "combo box" or "spin button"
    with no name at all.
    """
    sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
    sizer.Add(control, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)


def choose_from_rows(
    parent: wx.Window,
    *,
    title: str,
    label: str,
    help_text: str,
    rows: list[tuple[object, str]],
    extra_button: str = "",
    size: tuple[int, int] = (560, 400),
    on_highlight: Callable[[object], None] | None = None,
) -> tuple[object, str] | object | None:
    """One list, one choice. Returns the chosen row's key, or ``None``.

    A list rather than a tree, everywhere it is used -- headings, bookmarks,
    copy-tray slots, kept clips. A flat list in a meaningful order is what a
    listener can arrow through at speed, and the structure is already in each
    row's own text ("Heading 2: Installing", "Slot 3: ...").

    With *extra_button*, the answer is ``(key, "choose" | "<button>")`` so a
    caller can offer a second verb -- Remove, on the bookmark list -- without a
    second dialog. Without it, the answer is just the key.

    *on_highlight* is called with a row's key each time the selection moves,
    including the initial one. It exists for the spelling suggestions list,
    where the row's *text* is not enough: choosing between "receive" and
    "recieve" by ear is exactly as impossible in a list as it was in the
    document, so the caller spells out whichever one you land on. Anything it
    raises is swallowed -- a decoration on a list must never take the list down
    -- and a caller that passes nothing gets a plain list, unchanged.
    """
    dialog = wx.Dialog(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    root = wx.BoxSizer(wx.VERTICAL)
    static = wx.StaticText(dialog, label=label)
    listbox = wx.ListBox(dialog, choices=[text for _key, text in rows])
    set_accessible_name(listbox, _plain_label(label))
    listbox.SetHelpText(help_text)
    root.Add(static, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
    root.Add(listbox, 1, wx.EXPAND | wx.ALL, _PAD)

    extra: wx.Button | None = None
    if extra_button:
        extra = wx.Button(dialog, label=extra_button)
        extra.SetHelpText(f"{extra_button.replace('&', '')} the row you are on.")
        root.Add(extra, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT, _PAD)
    buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
    root.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, _PAD)
    dialog.SetSizerAndFit(root)
    dialog.SetSize(size)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
    # Enter and double-click both accept: a wx.ListBox raises no activated event
    # of its own, so without this the list is choose-with-the-mouse only.
    apply_listbox_activation(listbox, lambda _event: dialog.EndModal(wx.ID_OK))
    verb = {"value": "choose"}
    if extra is not None:

        def _extra(_event: wx.CommandEvent) -> None:
            verb["value"] = "extra"
            dialog.EndModal(wx.ID_OK)

        extra.Bind(wx.EVT_BUTTON, _extra)
    if on_highlight is not None:

        def _highlighted(_event: wx.CommandEvent) -> None:
            index = listbox.GetSelection()
            if index == wx.NOT_FOUND:
                return
            try:
                on_highlight(rows[int(index)][0])
            except Exception:  # noqa: BLE001 - a decoration must not break the list
                return

        listbox.Bind(wx.EVT_LISTBOX, _highlighted)
    if rows:
        listbox.SetSelection(0)
        if on_highlight is not None:
            # The first row too: it is selected without an event, and a listener
            # who opens the list and waits should hear about the row they are on
            # rather than only about the ones they arrow to.
            try:
                on_highlight(rows[0][0])
            except Exception:  # noqa: BLE001 - see above
                pass
    listbox.SetFocus()
    try:
        if show_modal_dialog(dialog, title) != wx.ID_OK:
            return None
        index = listbox.GetSelection()
        if index == wx.NOT_FOUND:
            return None
        key = rows[int(index)][0]
        return (key, verb["value"]) if extra is not None else key
    finally:
        dialog.Destroy()


def choose_heading(parent: wx.Window, headings: list[tuple[int, int, str]]) -> int | None:
    """Pick a heading from the document. Returns its start offset, or ``None``."""
    chosen = choose_from_rows(
        parent,
        title="Headings",
        label="&Headings in this document:",
        help_text="Choose a heading and press Enter to put the cursor at the start of it.",
        rows=[(offset, f"Heading {level}: {text}") for offset, level, text in headings],
    )
    return None if chosen is None else int(chosen)  # type: ignore[arg-type]


def choose_bookmark(parent: wx.Window, marks: list[Any]) -> tuple[str, int] | None:
    """Pick a bookmark. Returns ``("go" | "remove", number)``, or ``None``.

    Two verbs in one window, because the second thing anyone does with a
    bookmark list is tidy it, and sending them to a separate Remove dialog for
    that is a window and a decision too many.
    """
    chosen = choose_from_rows(
        parent,
        title="Bookmarks",
        label="&Bookmarks in this document, in order:",
        help_text=(
            "Choose a bookmark and press Enter to go there. Remove takes the one "
            "you are on out of the list; the document is not changed."
        ),
        rows=[(mark.number, f"{mark.number}: {mark.label}") for mark in marks],
        extra_button="&Remove",
        size=(560, 360),
    )
    if chosen is None:
        return None
    number, verb = chosen  # type: ignore[misc]
    return ("remove" if verb == "extra" else "go", int(number))


def edit_file_format(parent: wx.Window, *, encoding: str, newline: str) -> tuple[str, str] | None:
    """Choose the encoding and line endings this document saves with.

    Nothing is written here. The choice takes effect at the next save, which is
    the moment it means anything -- and which is why the dialog says so rather
    than implying the file has already changed.
    """
    dialog = wx.Dialog(parent, title="File format", style=wx.DEFAULT_DIALOG_STYLE)
    root = wx.BoxSizer(wx.VERTICAL)
    root.Add(
        wx.StaticText(
            dialog,
            label="These take effect the next time you save this document.",
        ),
        0,
        wx.ALL,
        _PAD,
    )

    encoding_label = wx.StaticText(dialog, label="&Encoding:")
    encoding_choice = wx.Choice(dialog, choices=[name for _codec, name in ENCODING_CHOICES])
    set_accessible_name(encoding_choice, "Encoding")
    encoding_choice.SetHelpText(
        "How characters are stored. UTF-8 is the right answer for anything new. "
        "UTF-8 with BOM is what Windows tools often expect. Windows-1252 is the "
        "old Western European encoding a lot of existing .txt files are in."
    )
    encoding_choice.SetSelection(_index_of(ENCODING_CHOICES, encoding))
    _stack(root, encoding_label, encoding_choice)

    newline_label = wx.StaticText(dialog, label="&Line endings:")
    newline_choice = wx.Choice(dialog, choices=[name for _value, name in NEWLINE_CHOICES])
    set_accessible_name(newline_choice, "Line endings")
    newline_choice.SetHelpText(
        "CRLF is what Windows programs write. LF is what Unix, macOS and most "
        "build tools expect. QuillLite writes back whichever the file arrived "
        "with unless you change it here."
    )
    newline_choice.SetSelection(_index_of(NEWLINE_CHOICES, newline))
    _stack(root, newline_label, newline_choice)

    buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
    root.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, _PAD)
    dialog.SetSizerAndFit(root)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
    encoding_choice.SetFocus()
    try:
        if show_modal_dialog(dialog, "File format") != wx.ID_OK:
            return None
        return (
            ENCODING_CHOICES[max(0, encoding_choice.GetSelection())][0],
            NEWLINE_CHOICES[max(0, newline_choice.GetSelection())][0],
        )
    finally:
        dialog.Destroy()


def _index_of(choices: tuple[tuple[str, str], ...], value: str) -> int:
    """Where *value* sits in *choices*, or 0 for something unrecognised."""
    for index, (candidate, _name) in enumerate(choices):
        if candidate == value:
            return index
    return 0


def show_text_window(parent: wx.Window, title: str, body: str) -> None:
    """A read-only text window (the key list, the About box).

    The body sits in a ``TE_RICH2`` read-only field rather than in a static
    label, because a screen reader can only *read through* text it can put a
    cursor in -- a long label is announced once, in one breath, and cannot be
    reviewed line by line afterwards.
    """
    dialog = wx.Dialog(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    root = wx.BoxSizer(wx.VERTICAL)
    field = _labelled_text(
        dialog,
        root,
        "&Text:",
        body,
        help_text="Read with the arrow keys. Escape closes this window.",
        multiline=True,
    )
    close_btn = wx.Button(dialog, wx.ID_CANCEL, "Close")
    close_btn.SetHelpText("Close this window and go back to your document.")
    root.Add(close_btn, 0, wx.ALIGN_RIGHT | wx.ALL, _PAD)
    dialog.SetSizerAndFit(root)
    dialog.SetSize((640, 480))
    apply_modal_ids(dialog, cancel_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)
    bind_close_button(dialog, close_btn, modeless=False)
    field.SetFocus()
    field.SetInsertionPoint(0)
    try:
        show_modal_dialog(dialog, title)
    finally:
        dialog.Destroy()
