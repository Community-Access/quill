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

**Where results open** (section 9, as QUILL Lite can):

* Word, a BRF and the tagged PDF in a new QUILL Lite window, as Lite opens
  any such file.
* The accessible HTML **as a readable document** in a new window -- headings,
  lists, tables and links, converted as Import / Convert converts any HTML --
  never as its markup, and named "<stem> (Scribe)", unsaved.
* EPUB in QUILL when QUILL is installed (Lite does not read EPUB). Without
  QUILL it is only saved, and the result sentence says so once.
* MP3 and DAISY in Quill Media Player. The rest are saved, and the result
  sentence says where.

**After the sentence, never under it** (:mod:`quill.ui.scribe_after_sentence`):
every one of those is a window coming to the front, so it opens once the
sentence that names it has been said.

Lite has no braille view, no read aloud and no chained AI (8.2: "Not in
Lite"), so its Next Steps are Send to Media Player and Open in QUILL Lite.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.scribe import PRODUCT_NAME
from quill.ui.scribe_after_sentence import AfterSentence
from quill.ui.scribe_after_sentence import wait_for_sentence as wait_for_sentence
from quill.ui.scribe_entry import ScribeEntryPoints
from quill.ui.scribe_entry import send_to_player as _send_to_player


def _player_target(format_id: str, path: Path) -> Path | None:
    """What Media Player would open for this result, or ``None``."""
    from quill.ui.scribe_entry import player_target

    return player_target(format_id, path)


__all__ = ["DocumentScribeMixin", "LiteScribeHost"]

AREA = "scribe"
#: What a Lite window opens itself, of Scribe's formats.
_OPENS_HERE = ("docx", "html", "pdf", "brf", "mobi")
#: What QUILL Lite cannot read, and QUILL can (handed to QUILL when it is there).
_QUILL_ONLY = ("epub",)
#: Said once in the result sentence when an EPUB was made and QUILL is not here.
NO_EPUB_READER = "QUILL Lite does not open EPUB books. QUILL does."


#: Said once when the converted HTML is asked for again while its window is open.
ALREADY_OPEN_SENTENCE = "The accessible HTML is already open"


def _readable_name(job: Any, path: Path) -> str:
    """ "Notes (Scribe)": the converted window's name, as Import names one."""
    from quill.core.import_convert import scribe_name

    return scribe_name(Path(getattr(job, "file_name", "") or path.name).stem or path.stem)


def _quill_installed() -> bool:
    from quill.core.app_launcher import build_launch_argv

    return build_launch_argv("quill") is not None


class LiteScribeHost:
    """QUILL Lite's side of :class:`quill.ui.scribe_controller.ScribeHost`."""

    app_name = "QUILL Lite"

    def __init__(self, app: Any) -> None:
        self._app = app
        #: The result window, held until its sentence has been said.
        self._after = AfterSentence(still_here=lambda: self.scribe_in_front())
        #: The accessible HTML's converted windows, by file: reused while open.
        self._readable_windows: dict[str, Any] = {}

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
        else:
            voice = getattr(self._app, "voice", None)
            if voice is not None:
                voice.speak(text)
        self._after.said(text)

    def _hold(self, opening: Callable[[], None], phrase: str) -> None:
        self._after.hold(opening, phrase)

    def scribe_hold(self, opening: Callable[[], None], phrase: str) -> None:
        """Open after the sentence carrying *phrase* (the browser, for the controller)."""
        self._after.hold(opening, phrase)

    def scribe_in_front(self) -> bool:
        import wx

        return wx.GetActiveWindow() is not None

    def scribe_ai_off(self) -> bool:
        """AI help switched off: Describe the pictures starts unchecked (10.1.4)."""
        enabled = getattr(self._app, "feature_enabled", None)
        return bool(callable(enabled) and not enabled("hosted_ai"))

    def scribe_open_result(self, job: Any, format_id: str, path: Path) -> str:
        from quill.core.scribe.results import opened_phrase

        if format_id == "html":
            shown = self._readable_window(path)
            if shown is not None:  # still open: brought forward, never a second copy
                phrase = ALREADY_OPEN_SENTENCE  # the reader says the window's name
                self._hold(lambda: self._app.focus_frame(shown), phrase)
                return phrase
            text = self._readable(path)  # converted now, so a failure is never "open"
            if text is None:
                return ""
            phrase = opened_phrase(format_id, "QUILL Lite")
            self._hold(lambda: self._show_readable(job, path, text), phrase)
            return phrase
        if format_id in _OPENS_HERE:
            phrase = opened_phrase(format_id, "QUILL Lite")
            self._hold(lambda: self._app.open_path(path), phrase)
            return phrase
        if format_id in _QUILL_ONLY and _quill_installed():
            phrase = opened_phrase(format_id, "QUILL")
            self._hold(lambda: self._to_quill(path), phrase)
            return phrase
        if format_id in ("mp3", "daisy") and _player_target(format_id, path) is not None:
            phrase = opened_phrase(format_id, "Media Player")
            self._hold(lambda: self._to_player(job, format_id, path), phrase)
            return phrase
        return ""

    def scribe_result_note(self, job: Any) -> str:
        """Said once, at the end of the result sentence: an EPUB nothing here reads."""
        made = getattr(job, "outputs", {}) or {}
        return NO_EPUB_READER if "epub" in made and not _quill_installed() else ""

    def _open_here(self, job: Any, format_id: str, path: Path) -> None:
        """A Lite window: the accessible HTML readable, the rest as Lite opens them."""
        if format_id == "html":
            self._open_readable(job, path)
        else:
            self._app.open_path(path)

    def _readable_window(self, path: Path) -> Any:
        """The window already showing *path* converted, if it is still open."""
        window = self._readable_windows.get(str(path))
        if window is not None and window in getattr(self._app, "frames", []):
            return window
        self._readable_windows.pop(str(path), None)
        return None

    def _open_readable(self, job: Any, path: Path) -> None:
        """A Next Step: the accessible HTML, readable, at once (a step speaks for
        itself). Already open, its window comes forward after one sentence."""
        shown = self._readable_window(path)
        if shown is not None:
            sentence = f"{ALREADY_OPEN_SENTENCE}."  # the reader says the window's name
            self._hold(lambda: self._app.focus_frame(shown), sentence)
            self.scribe_announce(sentence)
            return
        text = self._readable(path)
        if text is None:
            self.scribe_announce(
                f"QUILL Lite could not read {path.name}. It is saved in its folder."
            )
            return
        self._show_readable(job, path, text)

    @staticmethod
    def _readable(path: Path) -> str | None:
        """The accessible HTML converted as Import / Convert converts any HTML
        (headings, lists, tables, links), never its markup; ``None`` if it cannot be."""
        from quill.io.docconvert import convert_document

        try:
            return str(convert_document(path).text)
        except Exception:  # noqa: BLE001 - the caller says it, never raised into the queue
            return None

    def _show_readable(self, job: Any, path: Path, text: str) -> None:
        """A new unsaved window named "<stem> (Scribe)", as Import names one."""
        from quill.core.lite.open_prepare import PLAIN, PreparedDocument

        window = self._app.new_window(PLAIN)
        if window is None:
            return
        window._commit_download(PreparedDocument(mode=PLAIN, text=text), _readable_name(job, path))
        self._readable_windows[str(path)] = window

    def _to_quill(self, path: Path) -> None:
        from quill.core.app_launcher import launch_app

        if not launch_app("quill", extra_args=(str(path),)):
            self.scribe_announce(f"QUILL could not be opened. {path.name} is saved in its folder.")

    def scribe_next_steps(self, job: Any, ready: dict[str, Path]) -> list[tuple[str, Any]]:
        """Send to Media Player first, then Open in QUILL Lite (8.1.7, 8.2)."""
        from quill.core.scribe.model import format_label
        from quill.core.scribe.results import open_step

        steps: list[tuple[str, Any]] = []
        for format_id in ("mp3", "daisy"):
            if format_id in ready:
                steps.append((
                    f"Send to Media Player ({format_label(format_id)})",
                    lambda f=format_id: self._to_player(job, f, ready[f]),
                ))
        for format_id in _OPENS_HERE:
            if format_id in ready:
                steps.append((
                    open_step("QUILL Lite", format_id),
                    lambda f=format_id: self._open_here(job, f, ready[f]),
                ))
        if "epub" in ready and _quill_installed():
            steps.append((
                f"Open in QUILL ({format_label('epub')})",
                lambda: self._to_quill(ready["epub"]),
            ))
        from quill.ui.scribe_entry import browser_steps

        return steps + browser_steps(ready, self.scribe_announce)  # pictures and all (F2)

    def _to_player(self, job: Any, format_id: str, path: Path) -> None:
        if not _send_to_player(format_id, path):
            self.scribe_announce(
                f"Media Player could not be opened. {job.display_name} is saved in its folder."
            )


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
        jobs = self._scribe().convert_files([source], app_formats=["docx"], open_as="import")
        if self._scribe_turned_on and jobs:  # said only when something was sent
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
