"""File > Show and Hide Key...: choose the key that shows and hides an app from anywhere.

Quill Weather, Converter, Media Player and Inkwell have no show/hide key until
the listener chooses one (core/family_chords.py says why). This is where they
choose it, the same way in all four: type the key, or leave the box empty for
none. A key the family already uses -- another app's show/hide key, or any
app's shortcut -- is refused in one sentence that says whose it is, and the box
comes back with what was typed so it can be corrected rather than retyped.

Typed rather than pressed on purpose: a key some other program has registered
system-wide never reaches a "press the key now" box at all, so the person
pressing it would be told nothing.

Inkwell's two other system-wide keys, Quick Insert and Expand Word, are chosen
through the same loop and refused by the same rules
(:func:`run_system_key_command`), so there is one picker, not three.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "ShowHideKeyMixin",
    "choose_show_hide_key",
    "run_show_hide_key_command",
    "run_system_key_command",
]

_CAPTION = "Show and Hide Key"


def _prompt(app_id: str, current: str, purpose: str = "", own: dict[str, str] | None = None) -> str:
    from quill.core.app_launcher import app_name
    from quill.core.family_chords import suggest_show_hide_key

    does = purpose or f"shows and hides {app_name(app_id)}"
    now = f"It is {current} now." if current else "It has no key now."
    example = suggest_show_hide_key(app_id, own=own)
    hint = f", for example {example}" if example else ""
    return f"Type the key that {does} from any program{hint}. Leave the box empty for no key. {now}"


def _spelled(chord: str) -> str:
    """*chord* with its modifiers in the order the family writes them everywhere,
    Ctrl+Alt+Shift, so what is said back is what the guides say."""
    *mods, key = chord.split("+")
    order = [name for name in ("Ctrl", "Alt", "Shift") if name in mods]
    return "+".join([*order, key])


def choose_show_hide_key(
    host: Any,
    wx: Any,
    *,
    app_id: str,
    current: str,
    taken: dict[str, str] | None = None,
    caption: str = _CAPTION,
    purpose: str = "",
    own: dict[str, str] | None = None,
) -> str | None:
    """Ask until the answer is usable. The key (``""`` for none), or None if cancelled.

    *purpose* is what the key does ("opens Quick Insert"), when it is not the
    app's show/hide key; *own* is the app's other system-wide keys, which this
    one may not equal either.
    """
    from quill.core.family_chords import show_hide_key_problem
    from quill.core.lite.keymap import normalise_chord

    value = current
    prompt = _prompt(app_id, current, purpose, own)
    while True:
        dialog = wx.TextEntryDialog(host.frame, prompt, caption, value)
        try:
            answer = host._show_modal_dialog(dialog, caption)
            typed = str(dialog.GetValue()).strip()
        finally:
            dialog.Destroy()
        if answer != wx.ID_OK:
            return None
        problem = show_hide_key_problem(typed, app_id=app_id, taken=taken, own=own)
        if not problem:
            return _spelled(normalise_chord(typed)) if typed else ""
        host._show_message_box(problem, caption, wx.OK | wx.ICON_WARNING)
        value = typed


def _family_choices() -> dict[str, str]:
    """``{app id: show/hide key}`` other family apps' listeners have chosen."""
    try:
        from quill.core.paths import app_data_dir
        from quill.core.show_hide_keys import saved_keys

        return saved_keys(app_data_dir())
    except Exception:  # noqa: BLE001 - other apps' choices are a courtesy check
        return {}


def run_system_key_command(
    host: Any,
    wx: Any,
    *,
    app_id: str,
    current: str,
    caption: str,
    purpose: str,
    name: str,
    replace: Any,
    save: Any,
    own: dict[str, str] | None = None,
) -> None:
    """Choose one of an app's system-wide keys other than show/hide: ask,
    swap the registration (``replace(key) -> bool``), keep (``save(key)``),
    and say so. *name* is what the key is called when it is said back
    ("Quick Insert has no key.")."""
    chosen = choose_show_hide_key(
        host,
        wx,
        app_id=app_id,
        current=current,
        taken=_family_choices(),
        caption=caption,
        purpose=purpose,
        own=own,
    )
    if chosen is None or chosen == current:
        return
    if not replace(chosen):
        host._announce(f"Another program already uses {chosen}, so {name} kept its old key.")
        return
    save(chosen)
    host._announce(f"{chosen} now {purpose}." if chosen else f"{name} has no key.")


def run_show_hide_key_command(
    host: Any, wx: Any, *, app_id: str, save: Any, own: dict[str, str] | None = None
) -> None:
    """The whole File-menu command: ask, swap the registration, keep, and say so.

    *save* keeps the chosen key (``save(key)``); the host's ``_show_hide_key``
    holds the current one. A key Windows will not give (another program holds
    it) is said and not kept, and the old key stays in place. *own* is the
    app's other system-wide keys (Inkwell's two).
    """
    from quill.core.app_launcher import app_name

    current = str(getattr(host, "_show_hide_key", "") or "")
    chosen = choose_show_hide_key(
        host, wx, app_id=app_id, current=current, taken=_family_choices(), own=own
    )
    if chosen is None or chosen == current:
        return
    title = app_name(app_id)
    if not host._replace_tray_hotkey(chosen):
        host._announce(f"Another program already uses {chosen}, so {title} kept its old key.")
        return
    save(chosen)
    host._announce(
        f"{chosen} now shows and hides {title}." if chosen else f"{title} has no show and hide key."
    )


class ShowHideKeyMixin:
    """On ``AppShellFrame``: the chosen show/hide key's whole lifecycle.

    Quill Weather, Converter and Media Player call :meth:`_start_show_hide_key`
    once at launch; Quill Inkwell, which keeps its key in its own settings,
    calls :meth:`_begin_show_hide_key` with what it read. All four put
    :meth:`_append_show_hide_key_item` in their File menu, beside Minimize to
    Tray.
    """

    _show_hide_key: str = ""

    def _start_show_hide_key(self, app_id: str, *evidence: Any) -> None:
        """Read (and on the first launch, decide) the key, register it, and say
        the once-only sentence if this launch moved somebody off the old one.

        *evidence* is files whose existence proves the app has run here before.
        """
        from quill.core import show_hide_keys
        from quill.core.paths import app_data_dir

        try:
            data = app_data_dir()
            existing = show_hide_keys.has_run_before(data, app_id, *evidence)
            chord, notice = show_hide_keys.load_show_hide_key(data, app_id, existing_user=existing)
        except Exception:  # noqa: BLE001 - a key must never stop the app opening
            chord, notice = "", ""
        self._begin_show_hide_key(chord, notice)

    def _begin_show_hide_key(self, chord: str, notice: str = "") -> None:
        import wx

        self._show_hide_key = chord
        self._register_tray_hotkey(chord)  # type: ignore[attr-defined]
        if notice:
            # After the window is up and the screen reader has read its title.
            wx.CallLater(1500, self._say_show_hide_notice, notice)

    def _say_show_hide_notice(self, sentence: str) -> None:
        self._set_status(sentence)  # type: ignore[attr-defined]
        self._announce(sentence)  # type: ignore[attr-defined]

    def _replace_tray_hotkey(self, chord: str) -> bool:
        """Swap the registered key for *chord* ("" for none). False, with the
        old key back in place, when Windows will not give *chord*."""
        old = self._show_hide_key
        self._release_tray_hotkey()  # type: ignore[attr-defined]
        if not chord or self._register_tray_hotkey(chord):  # type: ignore[attr-defined]
            self._show_hide_key = chord
            return True
        self._register_tray_hotkey(old)  # type: ignore[attr-defined]
        return False

    def _append_show_hide_key_item(
        self, menu: Any, app_id: str, save: Any = None, own: Any = None
    ) -> None:
        """File > Show and Hide Key..., bound to the picker. *save* keeps the key
        (default: the shared ``show_hide_keys.json``); *own* answers the app's
        other system-wide keys at the moment the picker opens."""
        import wx

        if save is None:

            def save(chord: str) -> None:
                from quill.core.paths import app_data_dir
                from quill.core.show_hide_keys import save_show_hide_key

                save_show_hide_key(app_data_dir(), app_id, chord)

        item_id = wx.NewIdRef()
        menu.Append(item_id, "Show and &Hide Key...\tCtrl+Alt+Shift+H")
        self.frame.Bind(  # type: ignore[attr-defined]
            wx.EVT_MENU,
            lambda _e: run_show_hide_key_command(
                self, wx, app_id=app_id, save=save, own=own() if own else None
            ),
            id=item_id,
        )
        self._keep_menu_ids(item_id)  # type: ignore[attr-defined]
