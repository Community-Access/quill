"""QuillLite's Keyboard Manager: change a key, and be told what it costs.

QUILL has had a searchable, conflict-aware keymap editor for a long time
(``quill/ui/keymap_editor.py``). QuillLite could not have one, because it had no
keymap to edit -- its keys were string literals in a table. Now it has one
(:mod:`quill.core.lite.keymap`), and this is the editor on top.

Not a port of QUILL's mixin. That one reaches ``self.keymap``, ``self.commands``,
``self._binding_for`` and ``self._show_modal_dialog`` -- a command *registry* and
a chord grammar QuillLite does not have and does not want. What is worth copying
is the behaviour, and this has all of it:

* **One box, two questions.** Type part of a command's name and the list
  narrows. Press **Record a Key** and press a chord instead, and the same box
  answers the other question a person actually has -- *what is this key already
  doing?* -- because "is Ctrl+Shift+K free" is not answerable by reading a list
  of two hundred rows.
* **Honest conflicts.** Assigning a key somebody else owns names the owner and
  offers to move it, rather than silently refusing or silently stealing. A key
  claimed twice is the failure this whole area exists to prevent: one of the
  pair never fires and nothing announces the loss.
* **Refusals that say why.** Insert is never bindable -- it is NVDA's and JAWS's
  own modifier -- and a bare letter would type itself. Both are refused with the
  sentence, not with a beep.
* **An audit.** One button reports every duplicate, every binding for a command
  that no longer exists, every binding QuillLite cannot read, and every binding
  wx will accept and then never fire. The last of those is the one that looks
  like success from everywhere else: ``wx.AcceleratorEntry`` silently drops what
  it cannot parse, leaving a menu advertising a key that does nothing.

The list is a plain ``wx.ListBox`` of "Command -- Key" rows with buttons beside
it, which is the house pattern: no checkboxes inside a list control, and Enter on
a row does the obvious thing.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.lite import keymap as keymap_mod
from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    set_accessible_name,
    show_message_box,
    show_modal_dialog,
)
from quill.ui.hotkey_conflict import claim_sentence

__all__ = ["DocumentKeymapMixin", "KeymapEditorDialog", "row_text", "sort_key"]

#: Uniform padding, the same number the other QuillLite dialogs use.
_PAD = 8

#: How wide and tall the manager opens. Big enough that the list is worth
#: arrowing and the buttons are not below the fold.
_SIZE = (720, 520)

#: What the key column says for a command whose key has been cleared. Written
#: out rather than left blank, because an empty cell read aloud is a pause the
#: listener has to interpret.
_UNBOUND = "no key"


def row_text(title: str, key: str) -> str:
    """One list row: the command, then the key it answers to.

    Command first, because that is what somebody is scanning for -- the key is
    the answer to the row, not its name.
    """
    return f"{title} -- {key or _UNBOUND}"


def sort_key(title: str) -> tuple[str, ...]:
    """Menu path order, so a list of two hundred reads like the menu bar."""
    return tuple(part.strip().lower() for part in title.split(">"))


def _describe_modifiers(event: wx.KeyEvent) -> list[str]:
    modifiers = []
    if event.ControlDown():
        modifiers.append("Ctrl")
    if event.ShiftDown():
        modifiers.append("Shift")
    if event.AltDown():
        modifiers.append("Alt")
    return modifiers


#: wx key codes that are only ever a modifier, so a recorder must ignore them
#: rather than reporting "Ctrl" as a chord the moment Ctrl goes down.
_MODIFIER_CODES = frozenset({wx.WXK_CONTROL, wx.WXK_SHIFT, wx.WXK_ALT, wx.WXK_WINDOWS_LEFT})

#: Key codes whose name is not what ``chr()`` would give.
_SPECIAL_CODES: dict[int, str] = {
    wx.WXK_UP: "Up",
    wx.WXK_DOWN: "Down",
    wx.WXK_LEFT: "Left",
    wx.WXK_RIGHT: "Right",
    wx.WXK_HOME: "Home",
    wx.WXK_END: "End",
    wx.WXK_PAGEUP: "PageUp",
    wx.WXK_PAGEDOWN: "PageDown",
    wx.WXK_INSERT: "Insert",
    wx.WXK_DELETE: "Delete",
    wx.WXK_BACK: "Back",
    wx.WXK_TAB: "Tab",
    wx.WXK_RETURN: "Return",
    wx.WXK_NUMPAD_ENTER: "Return",
    wx.WXK_ESCAPE: "Escape",
    wx.WXK_SPACE: "Space",
}
_SPECIAL_CODES.update({getattr(wx, f"WXK_F{index}"): f"F{index}" for index in range(1, 25)})


def chord_from_event(event: wx.KeyEvent) -> str:
    """The chord a key event names, or "" while only modifiers are down.

    Reading the event rather than asking the user to type "ctrl plus shift plus
    k" is the whole point of Record: the chord you get is the chord the keyboard
    actually sends, including whichever of the two Alt keys and whatever the
    layout does with punctuation.
    """
    code = event.GetKeyCode()
    if code in _MODIFIER_CODES:
        return ""
    name = _SPECIAL_CODES.get(code)
    if name is None:
        if code < 32 or code > 0x10FFFF:
            return ""
        name = chr(code).upper()
    return "+".join([*_describe_modifiers(event), name])


class KeymapEditorDialog:
    """The Keyboard Manager window.

    Holds a *copy* of the keymap and hands it back only if the user saves, so
    Escape out of a session of experimenting leaves the keys exactly as they
    were. The app's live keymap is never edited in place.
    """

    def __init__(
        self,
        parent: wx.Window,
        *,
        keymap: dict[str, str],
        announce_cb: Any = None,
    ) -> None:
        self._keymap = dict(keymap)
        self._titles = keymap_mod.command_titles()
        self._announce = announce_cb or (lambda _m: None)
        self._handlers: list[str] = sorted(self._titles, key=lambda h: sort_key(self._titles[h]))
        self._shown: list[str] = list(self._handlers)
        self._recording = False
        self._saved = False

        self.dialog = wx.Dialog(
            parent,
            title="Keyboard Manager",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label=(
                    "Type part of a command's name to find it, or press Record a Key "
                    "and press a key combination to find out what it already does."
                ),
            ),
            0,
            wx.ALL,
            _PAD,
        )
        root.Add(self._build_search_row(), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, _PAD)

        self.status = wx.StaticText(self.dialog, label="")
        set_accessible_name(self.status, "Result")
        root.Add(self.status, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)

        self.listbox = wx.ListBox(self.dialog, choices=[])
        set_accessible_name(self.listbox, "Commands and their keys")
        self.listbox.SetHelpText(
            "Every command QuillLite has, with the key it answers to. Press Enter "
            "on one to give it a different key."
        )
        apply_listbox_activation(self.listbox, lambda _event: self._assign_selected())
        root.Add(self.listbox, 1, wx.EXPAND | wx.ALL, _PAD)
        root.Add(self._build_button_row(), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, _PAD)

        closing = self.dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        root.Add(closing, 0, wx.ALIGN_RIGHT | wx.ALL, _PAD)
        self.dialog.SetSizerAndFit(root)
        self.dialog.SetSize(_SIZE)
        self._refresh_list("")

    # -- construction -------------------------------------------------------- #

    def _build_search_row(self) -> wx.Sizer:
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(
            wx.StaticText(self.dialog, label="&Find a command:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            _PAD // 2,
        )
        self.search = wx.TextCtrl(self.dialog)
        set_accessible_name(self.search, "Find a command")
        self.search.SetHelpText(
            "Type part of a command's name, or of the menu it is in. Press Down to "
            "move into the list."
        )
        self.search.Bind(wx.EVT_TEXT, lambda _e: self._on_search())
        self.search.Bind(wx.EVT_KEY_DOWN, self._on_search_key)
        row.Add(self.search, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, _PAD // 2)

        self.record = wx.ToggleButton(self.dialog, label="&Record a Key")
        self.record.SetHelpText(
            "Turn this on and press a key combination. QuillLite says what that key "
            "does today, so you can find a free one without reading the whole list."
        )
        self.record.Bind(wx.EVT_TOGGLEBUTTON, lambda _e: self._on_record_toggled())
        row.Add(self.record, 0, wx.ALIGN_CENTER_VERTICAL)
        return row

    def _build_button_row(self) -> wx.Sizer:
        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, help_text, method in (
            (
                "&Assign Key...",
                "Give the command you are on a different key.",
                self._assign_selected,
            ),
            (
                "Reset to &Default",
                "Put the command you are on back to the key QuillLite ships with.",
                self._reset_selected,
            ),
            (
                "Reset &Everything...",
                "Put every key back to the one QuillLite ships with.",
                self._reset_all,
            ),
            (
                "Chec&k for Problems",
                "Report duplicate keys, keys QuillLite cannot read, and keys that "
                "are assigned but can never fire.",
                self._audit,
            ),
        ):
            button = wx.Button(self.dialog, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, run=method: run())
            row.Add(button, 0, wx.RIGHT, _PAD // 2)
        return row

    # -- the list ------------------------------------------------------------ #

    def _refresh_list(self, query: str, *, keep: str = "") -> None:
        """Show the handlers matching *query*, keeping the caret on *keep*."""
        words = query.lower().split()
        self._shown = [
            handler
            for handler in self._handlers
            if all(word in self._titles[handler].lower() for word in words)
        ]
        self.listbox.Set([row_text(self._titles[h], self._keymap.get(h, "")) for h in self._shown])
        if not self._shown:
            return
        index = self._shown.index(keep) if keep in self._shown else 0
        self.listbox.SetSelection(index)

    def _selected_handler(self) -> str:
        index = self.listbox.GetSelection()
        if index == wx.NOT_FOUND or index >= len(self._shown):
            return ""
        return self._shown[index]

    def _say(self, message: str) -> None:
        """Put a result in the status line and speak it.

        A label change on an unfocused control is exactly what a screen reader
        does not say by itself, and every message here is the outcome of
        something the user just did -- which is the one thing the reader cannot
        know (GATE-12, GATE-13).
        """
        self.status.SetLabel(message)
        self._announce(message)

    # -- searching, and the other question -------------------------------- #

    def _on_search(self) -> None:
        if self._recording:
            return  # the box is holding a recorded chord, not a search
        query = self.search.GetValue()
        self._refresh_list(query)
        if not query:
            self._say(f"{len(self._handlers)} commands.")
        elif self._shown:
            self._say(f"{len(self._shown)} of {len(self._handlers)} commands shown.")
        else:
            self._say("No commands match. Clear the box to see them all.")

    def _on_search_key(self, event: wx.KeyEvent) -> None:
        if self._recording:
            self._record_chord(event)
            return
        if event.GetKeyCode() == wx.WXK_DOWN and self._shown:
            self.listbox.SetFocus()
            return
        event.Skip()

    def _on_record_toggled(self) -> None:
        self._recording = bool(self.record.GetValue())
        if self._recording:
            self.search.SetValue("")
            self.search.SetFocus()
            self._say("Recording. Press the key combination you want to ask about.")
        else:
            self._say("Recording off. Typing searches command names again.")

    def _record_chord(self, event: wx.KeyEvent) -> None:
        """Answer "what is this key already doing?" for the chord just pressed."""
        chord = chord_from_event(event)
        if not chord:
            return  # only modifiers so far; wait for the key itself
        self.search.ChangeValue(keymap_mod.normalise_chord(chord) or chord)
        owners = keymap_mod.conflicting_handlers(self._keymap, "", chord)
        if owners:
            self._refresh_list("", keep=owners[0])
            names = ", ".join(self._titles.get(owner, owner) for owner in owners)
            self._say(f"{chord} is {names}.")
            return
        problem = keymap_mod.describe_binding_problem(chord)
        if problem:
            self._say(problem)
            return
        # "Free" used to mean "free inside QuillLite", which is the wrong half
        # of the question: another application holding a chord system-wide gets
        # the key before this window sees it, so the chord is not free at all
        # and pressing it does nothing. Reported as "Ctrl+Alt+G interferes with
        # Google Drive".
        self._say(claim_sentence(chord, wx) or f"{chord} is free.")

    # -- changing a key ------------------------------------------------------ #

    def _assign_selected(self) -> None:
        handler = self._selected_handler()
        if not handler:
            self._say("Move to a command in the list first.")
            return
        title = self._titles[handler]
        chord = ask_for_chord(self.dialog, title, self._keymap.get(handler, ""))
        if chord is None:
            return
        problem = keymap_mod.describe_binding_problem(chord)
        if problem:
            self._say(problem)
            show_message_box(problem, "Cannot use that key", wx.OK | wx.ICON_WARNING, self.dialog)
            return
        chord = keymap_mod.normalise_chord(chord)
        # And wx's own answer, at assign time. The check above is
        # :mod:`quill.core.lite.keymap` asking whether the chord is *sane*; this
        # is wx asking whether it can actually fire one, and they are not the
        # same question -- ``wx.AcceleratorEntry`` silently drops what it cannot
        # parse, so a chord that normalises cleanly and that wx refuses is
        # assigned and inert. The menu then advertises a key that does nothing
        # and nothing says so, which is the one failure that looks like success.
        # It ran only from the Audit button, which is to say after the damage
        # (bad.md H2); QUILL's keymap editor has checked at assign time all
        # along.
        if not binding_is_dispatchable(chord):
            refusal = (
                f"{chord} is a key Windows will not send to QuillLite, so nothing "
                "would happen when you pressed it. Try another."
            )
            self._say(refusal)
            show_message_box(refusal, "Cannot use that key", wx.OK | wx.ICON_WARNING, self.dialog)
            return
        claimed = claim_sentence(chord, wx)
        if claimed:
            # Warned rather than refused: the chord may be free again tomorrow
            # when that application is not running, and it is not this editor's
            # place to forbid a key somebody has chosen deliberately.
            self._say(claimed)
            show_message_box(claimed, "Key already in use", wx.OK | wx.ICON_WARNING, self.dialog)
        owners = keymap_mod.conflicting_handlers(self._keymap, handler, chord)
        if owners and not self._confirm_move(chord, owners):
            self._say(f"{title} still answers to {self._keymap.get(handler, '') or _UNBOUND}.")
            return
        for owner in owners:
            self._keymap[owner] = ""
        self._keymap[handler] = chord
        self._refresh_list(self.search.GetValue() if not self._recording else "", keep=handler)
        freed = (
            " " + ", ".join(self._titles.get(o, o) for o in owners) + " now has no key."
            if owners
            else ""
        )
        self._say(f"{title} is now {chord}.{freed}")

    def _confirm_move(self, chord: str, owners: list[str]) -> bool:
        """Name the command that owns *chord* and ask before taking it.

        Named, not counted: "that key is taken" leaves the user to go and find
        what took it, which on a two-hundred-row list is the work the editor was
        supposed to do.
        """
        names = ", ".join(self._titles.get(owner, owner) for owner in owners)
        answer = show_message_box(
            f"{chord} is currently {names}.\n\n"
            f"Move it? {names} will be left with no key until you give it one.",
            "That key is taken",
            # NO_DEFAULT on both confirmations here: a listener pressing Enter
            # reflexively must not silently strip a key off a command they were
            # not thinking about.
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self.dialog,
        )
        return bool(answer == wx.YES)

    def _reset_selected(self) -> None:
        handler = self._selected_handler()
        if not handler:
            self._say("Move to a command in the list first.")
            return
        default = keymap_mod.default_keymap().get(handler, "")
        title = self._titles[handler]
        if keymap_mod.chord_identity(self._keymap.get(handler, "")) == keymap_mod.chord_identity(
            default
        ):
            self._say(f"{title} is already on its default key, {default}.")
            return
        self._keymap[handler] = default
        self._refresh_list(self.search.GetValue() if not self._recording else "", keep=handler)
        self._say(f"{title} is back to {default}.")

    def _reset_all(self) -> None:
        changed = sum(
            1
            for handler, default in keymap_mod.default_keymap().items()
            if keymap_mod.chord_identity(self._keymap.get(handler, ""))
            != keymap_mod.chord_identity(default)
        )
        if not changed:
            self._say("Nothing to reset. Every key is already the one QuillLite ships with.")
            return
        answer = show_message_box(
            f"Put all {changed} changed keys back to the ones QuillLite ships with?",
            "Reset every key",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self.dialog,
        )
        if answer != wx.YES:
            return
        self._keymap = keymap_mod.default_keymap()
        self._refresh_list("")
        self._say(f"{changed} keys reset. Nothing is saved until you press Save.")

    # -- diagnosis ----------------------------------------------------------- #

    def _audit(self) -> None:
        """Report every way this keymap can be wrong, including the invisible one."""
        audit = keymap_mod.audit_keymap(self._keymap)
        inert = [
            handler
            for handler, key in sorted(self._keymap.items())
            if key and not binding_is_dispatchable(key)
        ]
        lines = [audit.summary()]
        for chord, owners in sorted(audit.duplicates.items()):
            names = ", ".join(self._titles.get(owner, owner) for owner in owners)
            lines.append(f"  {chord}: claimed by {names} -- only one of them fires.")
        for handler in audit.unparseable:
            lines.append(f"  {self._titles.get(handler, handler)}: QuillLite cannot read its key.")
        for handler in audit.reserved:
            lines.append(f"  {self._titles.get(handler, handler)}: on a key QuillLite reserves.")
        for handler in inert:
            lines.append(
                f"  {self._titles.get(handler, handler)}: {self._keymap[handler]} is a key "
                "Windows will not send to a menu, so it can never fire."
            )
        if len(lines) == 1 and not inert:
            self._say(audit.summary())
        else:
            self._say(f"{audit.summary()} See the list.")
        show_message_box(
            "\n".join(lines), "Keyboard check", wx.OK | wx.ICON_INFORMATION, self.dialog
        )

    # -- showing ------------------------------------------------------------- #

    def show(self) -> dict[str, str] | None:
        """Modal. Returns the new keymap if the user saved, else ``None``."""
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Save",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Cancel",
        )
        self.search.SetFocus()
        try:
            if show_modal_dialog(self.dialog, "Keyboard Manager") != wx.ID_OK:
                return None
            self._saved = True
            return dict(self._keymap)
        finally:
            self.dialog.Destroy()


def binding_is_dispatchable(binding: str) -> bool:
    """True when wx can actually fire *binding* from a menu accelerator.

    The check that cannot live in :mod:`quill.core.lite.keymap`, because it is
    wx asking wx. ``wx.AcceleratorEntry`` silently drops what it cannot parse,
    so a binding that reads fine and that wx refuses is assigned and inert --
    the menu advertises a key that does nothing, and nothing says so.
    """
    text = str(binding or "").strip()
    if not text:
        return False
    entry = wx.AcceleratorEntry()
    try:
        return bool(entry.FromString(text))
    except (TypeError, ValueError):
        return False


def ask_for_chord(parent: wx.Window, title: str, current: str) -> str | None:
    """Ask for one key combination by *pressing* it. Returns it, or ``None``.

    A capture box rather than a text field, because spelling a chord out is the
    step where a user and the app disagree about what "Ctrl plus comma" is. The
    field is read-only to typing and filled from the key event, so what is
    assigned is what the keyboard actually sends.
    """
    dialog = wx.Dialog(parent, title=f"Key for {title}", style=wx.DEFAULT_DIALOG_STYLE)
    root = wx.BoxSizer(wx.VERTICAL)
    root.Add(
        wx.StaticText(
            dialog,
            label=(
                f"Press the key combination for {title}.\n"
                f"It is {current or _UNBOUND} today. Press Escape to leave it alone."
            ),
        ),
        0,
        wx.ALL,
        _PAD,
    )
    field = wx.TextCtrl(dialog, value=current, style=wx.TE_READONLY)
    set_accessible_name(field, "Key combination")
    field.SetHelpText("The key combination you last pressed. Press another to change it.")
    root.Add(field, 0, wx.EXPAND | wx.ALL, _PAD)
    root.Add(dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_RIGHT | wx.ALL, _PAD)
    dialog.SetSizerAndFit(root)

    captured = {"chord": current}

    def _on_key(event: wx.KeyEvent) -> None:
        # Escape and Tab stay the dialog's, or the box becomes a trap that
        # cannot be left without a mouse.
        if event.GetKeyCode() in {wx.WXK_ESCAPE, wx.WXK_TAB}:
            event.Skip()
            return
        chord = chord_from_event(event)
        if not chord:
            return
        captured["chord"] = keymap_mod.normalise_chord(chord) or chord
        field.ChangeValue(captured["chord"])

    field.Bind(wx.EVT_KEY_DOWN, _on_key)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
    field.SetFocus()
    try:
        if show_modal_dialog(dialog, f"Key for {title}") != wx.ID_OK:
            return None
        return captured["chord"]
    finally:
        dialog.Destroy()


class DocumentKeymapMixin:
    """The Tools menu item that opens the manager."""

    def cmd_keyboard_manager(self) -> None:
        """Change what any key does, and be told what it was doing first.

        Every window is rebuilt on save, not just this one: a menu bar showing
        one key while its neighbour shows another is a worse bug than the stale
        key it would be replacing.
        """
        dialog = KeymapEditorDialog(self, keymap=self.app.keymap, announce_cb=self._announce)
        changed = dialog.show()
        self.control.SetFocus()
        if changed is None:
            return
        self.app.keymap = changed
        self.app.save_keymap()
        self._announce("Keys saved. Every window's menus have been rebuilt.")
