"""QUILL's door to the shared WordPress commands: File > WordPress (wordpress.md 12).

An adapter with no commands of its own, the same shape as
``main_frame_hosted_ai.py``: :class:`QuillWordPressHost` turns the main frame
into a :class:`~quill.ui.wordpress_host.WordPressHost`, and
:class:`WordPressMenuMixin` builds the submenu, registers each row as a
palette command and binds it. Every ``cmd_*`` that runs is in
:mod:`quill.ui.wordpress_commands`, which QUILL Lite reaches too -- a test
asserts this module defines none, because a second implementation is how the
two editors drift.
"""

from __future__ import annotations

import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.wordpress.menu import DOCUMENT_ONLY, PLACES, Submenu, all_rows

#: wx's code for Escape, which is 27 on every platform wx runs on here.
_WXK_ESCAPE = 27


class QuillWordPressHost:
    """The main frame, as the shared WordPress commands see it."""

    def __init__(self, frame: Any) -> None:
        self._mf = frame

    @property
    def parent(self) -> Any:
        return self._mf.frame

    def show_modal(self, dialog: Any, label: str) -> int:
        return int(self._mf._show_modal_dialog(dialog, label))

    def announce(self, text: str) -> None:
        self._mf._announce(text)

    def run_task(
        self,
        name: str,
        func: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_failure: Callable[[BaseException], None],
    ) -> None:
        self._mf._task_manager.submit(
            name,
            lambda **_kw: func(),
            on_success=lambda _op, result: on_success(result),
            on_failure=lambda _op, exc: on_failure(exc),
        )

    def current_path(self) -> Path | None:
        path = getattr(self._mf.document, "path", None)
        return Path(path) if path else None

    def current_text(self) -> str:
        return str(self._mf.editor.GetValue())

    def replace_text(self, text: str) -> None:
        editor = self._mf.editor
        editor.SetSelection(0, editor.GetLastPosition())
        editor.WriteText(text)

    def insert_text(self, text: str) -> None:
        self._mf.editor.WriteText(text)

    def selected_text(self) -> str:
        return str(self._mf.editor.GetStringSelection())

    def caret_offset(self) -> int:
        return int(self._mf.editor.GetInsertionPoint())

    def go_to_offset(self, offset: int) -> None:
        editor = self._mf.editor
        editor.SetInsertionPoint(offset)
        editor.ShowPosition(offset)
        editor.SetFocus()

    def open_path(self, path: Path) -> None:
        self._mf.open_file(path)

    def save_current(self) -> bool:
        self._mf.save_file()
        return not bool(getattr(self._mf.document, "modified", False))

    def clipboard_text(self) -> str:
        return read_clipboard_text()

    def set_clipboard_text(self, text: str) -> None:
        write_clipboard_text(text)

    def open_in_browser(self, url: str) -> None:
        webbrowser.open(url)

    def clipboard_image_png(self) -> bytes | None:
        from quill.ui.wordpress_media_host import read_clipboard_png

        return read_clipboard_png()

    def ai_describe_image(
        self,
        path: Path,
        question: str,
        on_done: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> bool:
        from quill.ui.wordpress_media_host import ask_editor_ai

        return ask_editor_ai(self._mf, path, question, on_done, on_error)

    def ai_editor(self) -> Any:
        return self._mf

    def start_repeating(self, seconds: float, callback: Callable[[], None]) -> Callable[[], None]:
        return start_wx_repeating(self._mf.frame, seconds, callback)


class WordPressMenuMixin:
    def _wordpress(self) -> Any:
        commands = getattr(self, "_wordpress_commands", None)
        if commands is None:
            from quill.ui.wordpress_commands import WordPressCommands

            commands = WordPressCommands(QuillWordPressHost(self))
            self._wordpress_commands = commands
        return commands

    def _wordpress_menu_ids(self) -> dict[str, int]:
        ids = getattr(self, "_wordpress_ids", None)
        if ids is None:
            import wx

            # Keep the refs: wx releases an id when its WindowIDRef is collected,
            # and Append then refuses it ("id should first be reserved").
            refs = {row[0]: wx.NewIdRef() for _sub, row in all_rows()}
            self._wordpress_id_refs = refs
            ids = {command_id: int(ref) for command_id, ref in refs.items()}
            self._wordpress_ids = ids
        return ids

    def _append_wordpress_file_menu(self, file_menu: Any) -> None:
        """File > WordPress, when the WordPress feature is on (wordpress.md 12)."""
        if self._feature_enabled("core.wordpress"):  # type: ignore[attr-defined]
            self._fill_wordpress_menu(file_menu, PLACES["file"][1])

    def _place_wordpress_rows(self, menus: dict[str, Any]) -> None:
        """The rows that live in Edit, View, Insert, Format and Tools (wordpress.md 12).

        *menus* maps a place in :data:`PLACES` to the built ``wx.Menu``; each
        place's rows go at its foot, after a separator.
        """
        if not self._feature_enabled("core.wordpress"):  # type: ignore[attr-defined]
            return
        for place, menu in menus.items():
            if place != "file" and menu is not None:
                self._fill_wordpress_menu(menu, PLACES[place][1])

    def _refresh_wordpress_menu_items(self, menu_bar: Any) -> None:
        """Enable the page commands only while a WordPress document is in front.

        Elsewhere they are dimmed; reached another way (the Command Palette),
        the command itself says why.
        """
        ids = getattr(self, "_wordpress_ids", None)
        if not ids or menu_bar is None:
            return
        host = QuillWordPressHost(self)
        try:
            is_wordpress = self._wordpress().local.copy_for_path(host.current_path()) is not None
        except Exception:  # noqa: BLE001 - a menu refresh must never raise
            is_wordpress = False
        for _path, (command_id, _title, handler) in all_rows():
            if handler in DOCUMENT_ONLY and command_id in ids:
                item = menu_bar.FindItemById(ids[command_id])
                if item is not None:
                    item.Enable(is_wordpress)

    def _fill_wordpress_menu(self, menu: Any, rows: tuple[Any, ...]) -> Any:
        """Put *rows* in *menu*, nesting each :class:`Submenu` as it comes."""
        import wx

        ids = self._wordpress_menu_ids()
        for row in rows:
            if row is None:
                menu.AppendSeparator()
                continue
            if isinstance(row, Submenu):
                menu.AppendSubMenu(self._fill_wordpress_menu(wx.Menu(), row.rows), row.title)
                continue
            command_id, title, handler = row
            self.commands.try_register(  # type: ignore[attr-defined]
                command_id,
                title.replace("&", "").removesuffix("..."),
                (lambda h=handler: getattr(self._wordpress(), h)()),
                self._binding_for(command_id),  # type: ignore[attr-defined]
            )
            menu.Append(ids[command_id], self._menu_label(title, command_id))  # type: ignore[attr-defined]
            self.frame.Bind(  # type: ignore[attr-defined]
                wx.EVT_MENU,
                lambda _e, h=handler: getattr(self._wordpress(), h)(),
                id=ids[command_id],
            )
        return menu

    def _wordpress_key_event(self, event: Any) -> bool:
        """The WordPress keys: Ctrl+Alt+Shift+Grave, then a letter (wordpress.md 19).

        Called from the char hook ahead of the QUILL key. True when the key was
        the layer's; the shared :class:`~quill.core.wordpress.keys.WordPressKeyLayer`
        decides what it means, and the letters come from the live keymap, so a
        key moved in the Keyboard Manager moves here too.
        """
        from quill.core.wordpress import keys

        layer = getattr(self, "_wordpress_key_layer", None)
        if layer is None:
            layer = self._wordpress_key_layer = keys.WordPressKeyLayer()
        if layer.active:
            code = int(event.GetKeyCode())
            if self._is_bare_modifier_key(code):  # type: ignore[attr-defined]
                return True  # Shift going down on the way to Shift+S
            key = keys.event_key(
                code,
                ctrl=bool(event.ControlDown()),
                alt=bool(event.AltDown()),
                shift=bool(event.ShiftDown()),
                escape_code=_WXK_ESCAPE,
            )
            if not key:
                layer.cancel()
                return False
            keymap = getattr(self, "keymap", None) or {}
            outcome = layer.press(key, keys.layer_from_bindings(keymap))
            if outcome.command:
                self._run_command(outcome.command)  # type: ignore[attr-defined]
            elif outcome.message:
                self._announce(outcome.message)  # type: ignore[attr-defined]
            return outcome.consumed
        if not self._wordpress_prefix_matches(event):
            return False
        self._announce(layer.start())  # type: ignore[attr-defined]
        return True

    def _wordpress_prefix_matches(self, event: Any) -> bool:
        """Ctrl+Alt+Shift+Grave, while WordPress is on and the QUILL key is not on it."""
        from quill.core.lite.keymap import chord_identity
        from quill.core.wordpress.keys import LAYER_PREFIX

        if not (event.ControlDown() and event.AltDown() and event.ShiftDown()):
            return False
        if not self._feature_enabled("core.wordpress"):  # type: ignore[attr-defined]
            return False
        settings = getattr(self, "settings", None)
        quill_key = str(getattr(settings, "quill_key_binding", "") or "")
        if quill_key and chord_identity(quill_key) == chord_identity(LAYER_PREFIX):
            return False  # the user put the QUILL key here; it wins
        return bool(self._event_matches_grave_key(event))  # type: ignore[attr-defined]

    def _command_to_menu_id_map(self) -> dict[str, int]:
        mapping: dict[str, int] = super()._command_to_menu_id_map()  # type: ignore[misc]
        if getattr(self, "_wordpress_ids", None):
            mapping.update(self._wordpress_ids)
        return mapping


def read_clipboard_text() -> str:
    import wx

    text = ""
    if wx.TheClipboard.Open():
        try:
            data = wx.TextDataObject()
            if wx.TheClipboard.GetData(data):
                text = data.GetText()
        finally:
            wx.TheClipboard.Close()
    return text


def write_clipboard_text(text: str) -> None:
    import wx

    if wx.TheClipboard.Open():
        try:
            wx.TheClipboard.SetData(wx.TextDataObject(text))
        finally:
            wx.TheClipboard.Close()


def start_wx_repeating(
    owner: Any, seconds: float, callback: Callable[[], None]
) -> Callable[[], None]:
    """A ``wx.Timer`` owned by *owner*, so it dies with the window; returns its stop."""
    import wx

    timer = wx.Timer(owner)

    def on_timer(_event: Any) -> None:
        callback()

    def on_destroy(event: Any) -> None:
        # wx does not stop a timer when its owner goes; one left running fires
        # into freed memory (tests/conftest.py tells that story).
        if event.GetEventObject() is owner and timer.IsRunning():
            timer.Stop()
        event.Skip()

    owner.Bind(wx.EVT_TIMER, on_timer, timer)
    owner.Bind(wx.EVT_WINDOW_DESTROY, on_destroy)
    timer.Start(max(1, int(seconds * 1000)))

    def stop() -> None:
        if timer.IsRunning():
            timer.Stop()
        if owner:  # still alive: drop the binding too
            owner.Unbind(wx.EVT_TIMER, handler=on_timer, source=timer)

    return stop
