"""QUILL Lite's door to Scribe for Documents (PRD 8.2).

An adapter with no commands of its own: each ``cmd_scribe_*`` below hands
straight to the shared :class:`~quill.ui.scribe_entry.ScribeEntryPoints`, the
same code QUILL's :mod:`quill.ui.main_frame_scribe` reaches, and every Scribe
window is the shared one (Convert, Scribe Conversions, My Scribe Documents,
Options, Sign In). The rows are :mod:`quill.core.lite.commands_scribe`'s.

**One controller for the app**, not one per window: QUILL Lite has a window
per document, and the family queue wants one runner per app
(:class:`LiteScribeHost` is keyed on the app). It speaks through the window in
front, so speech and braille follow the person.

**The ``scribe`` feature area** (off by default) takes the whole submenu
away, keys and Command Palette rows included. It is offered on first need:
when an imported PDF has little or no text, the question includes "Turn on
Scribe for Documents and convert", straight after the person's own command.

**Where results open** (section 9, as QUILL Lite can): Word, HTML and a BRF
in a new QUILL Lite window; MP3 and DAISY in Quill Media Player; the rest
are saved and the result sentence says where. Lite has no braille view, no
read aloud and no chained AI (8.2: "Not in Lite"), so its Next Steps are
Send to Media Player and Open in QUILL Lite.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.scribe import PRODUCT_NAME
from quill.ui.scribe_entry import ScribeEntryPoints

__all__ = ["DocumentScribeMixin", "LiteScribeHost"]

AREA = "scribe"
#: What a Lite window opens itself, of Scribe's formats.
_OPENS_HERE = ("docx", "html", "brf")


class LiteScribeHost:
    """QUILL Lite's side of :class:`quill.ui.scribe_controller.ScribeHost`."""

    app_name = "QUILL Lite"

    def __init__(self, app: Any) -> None:
        self._app = app

    def _window(self) -> Any:
        frame = getattr(self._app, "active_frame", None)
        frames = getattr(self._app, "frames", [])
        if frame in frames:
            return frame
        return frames[-1] if frames else None

    def scribe_parent(self) -> Any:
        import wx

        return wx.GetActiveWindow() or self._window() or getattr(self._app, "shell", None)

    def scribe_announce(self, text: str) -> None:
        window = self._window()
        if window is not None:
            window._announce(text)
            return
        voice = getattr(self._app, "voice", None)
        if voice is not None:
            voice.speak(text)

    def scribe_in_front(self) -> bool:
        import wx

        return wx.GetActiveWindow() is not None

    def scribe_ai_off(self) -> bool:
        """AI help switched off: Describe the pictures starts unchecked (10.1.4)."""
        enabled = getattr(self._app, "feature_enabled", None)
        return bool(callable(enabled) and not enabled("hosted_ai"))

    def scribe_open_result(self, job: Any, format_id: str, path: Path) -> str:
        from quill.core.scribe.results import opened_phrase
        from quill.ui.scribe_entry import send_to_player as _send_to_player

        if format_id in _OPENS_HERE:
            self._app.open_path(path)
            return opened_phrase(format_id, "QUILL Lite")
        if format_id in ("mp3", "daisy") and _send_to_player(format_id, path):
            return opened_phrase(format_id, "Media Player")
        return ""

    def scribe_next_steps(self, job: Any, ready: dict[str, Path]) -> list[tuple[str, Any]]:
        """Send to Media Player first, then Open in QUILL Lite (8.1.7, 8.2)."""
        from quill.core.scribe.model import format_label
        from quill.ui.scribe_entry import send_to_player as _send_to_player

        steps: list[tuple[str, Any]] = []
        for format_id in ("mp3", "daisy"):
            if format_id in ready:
                steps.append((
                    f"Send to Media Player ({format_label(format_id)})",
                    lambda f=format_id: _send_to_player(f, ready[f]),
                ))
        for format_id in _OPENS_HERE:
            if format_id in ready:
                steps.append((
                    f"Open in QUILL Lite ({format_label(format_id)})",
                    lambda f=format_id: self._app.open_path(ready[f]),
                ))
        return steps


class DocumentScribeMixin(ScribeEntryPoints):
    """File > Scribe for Documents in a QUILL Lite window."""

    # -- the shared commands' hooks --------------------------------------

    def _scribe(self) -> Any:
        from quill.ui.scribe_controller import controller_for

        app = self.app  # type: ignore[attr-defined]
        host = getattr(app, "_scribe_host", None)
        if host is None:
            host = LiteScribeHost(app)
            app._scribe_host = host
        return controller_for(host)

    def _scribe_frame(self) -> Any:
        return self

    def _scribe_say(self, text: str) -> None:
        self._announce(text)  # type: ignore[attr-defined]

    def _scribe_document(self) -> tuple[Path | None, bool, str] | None:
        path = getattr(self, "path", None)
        text = str(self.control.GetValue())  # type: ignore[attr-defined]
        return (Path(path) if path else None, bool(getattr(self, "modified", False)), text)

    def _scribe_save_document(self) -> None:
        self.cmd_save()  # type: ignore[attr-defined]

    # -- the area --------------------------------------------------------

    def _scribe_on(self) -> bool:
        """The area is on. Off, a command reached anyway says how to turn it on."""
        if self.app.feature_enabled(AREA):  # type: ignore[attr-defined]
            return True
        self._announce(  # type: ignore[attr-defined]
            f"{PRODUCT_NAME} is off. Turn it on in Tools, Customize Features."
        )
        return False

    def _scribe_turn_on(self) -> None:
        """First need (8.2): the person chose to turn it on, from the import question."""
        app = self.app  # type: ignore[attr-defined]
        features = getattr(app, "features", None)
        if features is None or app.feature_enabled(AREA):
            return
        features.set_enabled(AREA, True)
        app.save_features()
        app.refresh_all_menus()
        self._scribe_turned_on = True

    def _scribe_import_offer(self, source: Path, pages: int) -> str | None:
        """The scanned-import question with Scribe in it, on or off (8.2)."""
        on = bool(self.app.feature_enabled(AREA))  # type: ignore[attr-defined]
        return self._scribe_scanned_choice(source, pages, turn_on=not on)

    def _scribe_import_with(self, source: Path) -> None:
        """Convert *source* with Scribe from the import question; turning the area
        on first when the person chose that, and saying so once afterwards."""
        self._scribe_turned_on = False
        self._scribe_turn_on()
        self.scribe_import_file(source)
        if self._scribe_turned_on:
            self._announce(f"{PRODUCT_NAME} is on. It is in the File menu.")  # type: ignore[attr-defined]

    # -- the rows (commands_scribe.py) -----------------------------------

    def cmd_scribe_convert_file(self) -> None:
        if self._scribe_on():
            self.scribe_convert_file()

    def cmd_scribe_convert_this(self) -> None:
        if self._scribe_on():
            self.scribe_convert_this()

    def cmd_scribe_export(self) -> None:
        if self._scribe_on():
            self.scribe_export()

    def cmd_scribe_convert_link(self) -> None:
        if self._scribe_on():
            self.scribe_convert_link()

    def cmd_scribe_my_documents(self) -> None:
        if self._scribe_on():
            self.scribe_my_documents()

    def cmd_scribe_conversions(self) -> None:
        if self._scribe_on():
            self.scribe_conversions()

    def cmd_scribe_window(self) -> None:
        """Window > Scribe Conversions."""
        self.cmd_scribe_conversions()

    def cmd_scribe_status(self) -> None:
        if self._scribe_on():
            self.scribe_status()

    def cmd_scribe_repeat(self) -> None:
        if self._scribe_on():
            self.scribe_repeat()

    def cmd_scribe_sign_in(self) -> None:
        if self._scribe_on():
            self.scribe_sign_in()

    def cmd_scribe_sign_out(self) -> None:
        if self._scribe_on():
            self.scribe_sign_out()

    def cmd_scribe_account(self) -> None:
        if self._scribe_on():
            self.scribe_account()

    def cmd_scribe_options(self) -> None:
        if self._scribe_on():
            self.scribe_options()

    def cmd_scribe_about(self) -> None:
        self.scribe_about()
