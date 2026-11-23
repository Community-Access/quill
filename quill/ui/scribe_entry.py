"""The Scribe for Documents commands both editors have, written once (PRD 8.1, 8.2).

QUILL (:mod:`quill.ui.main_frame_scribe`) and QUILL Lite
(:mod:`quill.apps.lite_window_scribe`) each mix this in and answer six small
hooks; neither has a second implementation of any command here. That is the
family rule CLAUDE.md states for the hosted AI: QUILL Lite may never be ahead
of QUILL, and a duplicate is how that rule gets broken quietly.

The hooks:

* ``_scribe()`` -- the app's :class:`~quill.ui.scribe_controller.ScribeController`;
* ``_scribe_frame()`` -- the window a picker or question belongs to;
* ``_scribe_modal(dialog, title)`` -- the app's modal contract;
* ``_scribe_say(text)`` -- the announcement service;
* ``_scribe_document()`` -- ``(path, modified, text)`` of the document in
  front, or ``None`` when there is none;
* ``_scribe_save_document()`` -- the app's own Save (which asks for a name).

The rest is shared: the file picker that offers only the 23 types Scribe
takes, the current document as a file Scribe takes (saved first, Markdown and
HTML sent as Word), the link prompt, the scanned-PDF question with Scribe in
it, and every Tools > Scribe for Documents command.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.scribe import PRODUCT_NAME
from quill.core.scribe.inputs import ACCEPTED_EXTENSIONS

#: Files Scribe takes as they are: the 23 types Pneuma confirmed (3.1). Anything
#: else -- Markdown, and HTML, which Scribe refuses -- is saved as DOCX first.
SENDABLE = ACCEPTED_EXTENSIONS


class ScribeEntryPoints:
    """The commands, on an editor window (QUILL's MainFrame or a Lite window)."""

    # -- hooks (each app answers these) ------------------------------------

    def _scribe(self) -> Any:  # pragma: no cover - always overridden
        raise NotImplementedError

    def _scribe_frame(self) -> Any:  # pragma: no cover - always overridden
        raise NotImplementedError

    def _scribe_modal(self, dialog: Any, title: str) -> int:
        from quill.ui.dialog_contract import show_modal_dialog

        return int(show_modal_dialog(dialog, title))

    def _scribe_say(self, text: str) -> None:  # pragma: no cover - always overridden
        raise NotImplementedError

    def _scribe_document(self) -> tuple[Path | None, bool, str] | None:  # pragma: no cover
        raise NotImplementedError

    def _scribe_save_document(self) -> None:  # pragma: no cover - always overridden
        raise NotImplementedError

    def _scribe_show_about(self, title: str, text: str) -> None:
        import wx

        from quill.ui.dialog_contract import show_message_box

        show_message_box(text, title, wx.OK | wx.ICON_INFORMATION, self._scribe_frame())

    # -- convert a file ----------------------------------------------------

    def scribe_convert_file(self) -> None:
        self._scribe_pick_and_convert(multiple=True, app_formats=None, open_as="")

    def scribe_import_file(self, path: Path | None = None) -> None:
        """Import / Convert's Scribe tier: Word, opened as new text (8.1.1, 8.2)."""
        if path is None:
            self._scribe_pick_and_convert(multiple=False, app_formats=["docx"], open_as="import")
            return
        self._scribe().convert_files([path], app_formats=["docx"], open_as="import")

    def _scribe_pick_and_convert(
        self, *, multiple: bool, app_formats: Any, open_as: str, folder: str = ""
    ) -> None:
        import wx

        from quill.core.scribe.inputs import input_wildcard

        controller = self._scribe()
        if not controller.check_available():
            return
        style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | (wx.FD_MULTIPLE if multiple else 0)
        dialog = wx.FileDialog(
            self._scribe_frame(),
            f"Convert with {PRODUCT_NAME}",
            wildcard=input_wildcard(),  # only what Scribe takes (3.1)
            style=style,
        )
        try:
            if self._scribe_modal(dialog, f"Convert with {PRODUCT_NAME}") != wx.ID_OK:
                return
            paths = [Path(p) for p in dialog.GetPaths()] if multiple else [Path(dialog.GetPath())]
        finally:
            dialog.Destroy()
        controller.convert_files(paths, app_formats=app_formats, open_as=open_as, folder=folder)

    # -- convert the document in front ------------------------------------

    def _scribe_current_file(self) -> Path | None:
        """The current document as a file Scribe takes: saved first (8.1.4)."""
        state = self._scribe_document()
        if state is None:
            self._scribe_say("Open or create a document first.")
            return None
        path, modified, _text = state
        if modified or path is None:
            self._scribe_save_document()
            state = self._scribe_document()
            if state is None or state[0] is None or state[1]:
                self._scribe_say("Nothing was sent: the document needs saving first.")
                return None
            path = state[0]
        path = Path(path)
        if path.suffix.lower() in SENDABLE:
            return path
        return self._scribe_as_docx(path, state[2])

    def _scribe_as_docx(self, path: Path, text: str) -> Path | None:
        """A Markdown or other text document, as DOCX through Pandoc when it is
        installed, otherwise as plain text, which Scribe certainly takes."""
        folder = Path(tempfile.mkdtemp(prefix="quill-scribe-"))
        try:
            from quill.core.external_tools import get_external_tool_status
            from quill.io.pandoc import convert_file_with_pandoc

            if get_external_tool_status("pandoc").installed:
                target = folder / f"{path.stem}.docx"
                # Scribe refuses web pages (3.1), so an HTML document goes as Word.
                web = path.suffix.lower() in {".html", ".htm", ".xhtml"}
                source_format = "html" if web else "gfm+hard_line_breaks"
                convert_file_with_pandoc(path, target, from_format=source_format, to_format="docx")
                return target
        except Exception:  # noqa: BLE001 - fall back to the text
            pass
        target = folder / f"{path.stem}.txt"
        target.write_text(text, encoding="utf-8")
        return target

    def scribe_convert_this(self) -> None:
        self._scribe_send_current(app_formats=None, open_as="")

    def scribe_export(self) -> None:
        """Export with Scribe for Documents...: every Scribe format, tagged PDF first."""
        self._scribe_send_current(app_formats=["pdf"], open_as="")

    def scribe_braille(self) -> None:
        """Translate with Scribe for Documents...: BRF, in the braille view."""
        self._scribe_send_current(app_formats=["brf"], open_as="braille")

    def _scribe_send_current(self, *, app_formats: Any, open_as: str) -> None:
        controller = self._scribe()
        if not controller.check_available():
            return
        path = self._scribe_current_file()
        if path is None:
            return
        state = self._scribe_document()
        source = state[0] if state is not None else None
        title = Path(source).stem if source else path.stem
        controller.convert_files([path], app_formats=app_formats, open_as=open_as, title=title)

    def scribe_convert_link(self) -> None:
        import wx

        controller = self._scribe()
        if not controller.check_available():
            return
        dialog = wx.TextEntryDialog(
            self._scribe_frame(),
            "The address of a file (a PDF or a document, not a web page or a page behind a "
            "sign-in):",
            "Convert from a Link",
        )
        try:
            if self._scribe_modal(dialog, "Convert from a Link") != wx.ID_OK:
                return
            url = dialog.GetValue().strip()
        finally:
            dialog.Destroy()
        if not url.lower().startswith(("https://", "http://")):
            self._scribe_say("That is not a web address. Nothing was sent.")
            return
        controller.convert_url(url)

    # -- the rest of the submenu ------------------------------------------

    def scribe_my_documents(self) -> None:
        self._scribe().my_documents()

    def scribe_conversions(self) -> None:
        self._scribe().open_conversions()

    def scribe_status(self) -> None:
        self._scribe().status()

    def scribe_repeat(self) -> None:
        self._scribe().repeat_last()

    def scribe_sign_in(self) -> None:
        controller = self._scribe()
        if not controller.unavailable() and controller.session.is_signed_in():
            self._scribe_say(f"You are already signed in to {PRODUCT_NAME}.")
            return
        controller.sign_in()

    def scribe_sign_out(self) -> None:
        controller = self._scribe()
        if controller.check_available():
            controller.sign_out()

    def scribe_account(self) -> None:
        self._scribe().open_account_in_browser()

    def scribe_options(self) -> None:
        self._scribe().show_options()

    def scribe_about(self) -> None:
        self._scribe_show_about(f"About {PRODUCT_NAME}", self._scribe().about())

    # -- the scanned offer ------------------------------------------------

    def _scribe_scanned_choice(
        self, path: Path, page_count: int, *, turn_on: bool = False
    ) -> str | None:
        """The scanned-PDF question with Scribe in it (8.1.2, 8.2), or ``None``
        when Scribe is not offered and the plain OCR question should be asked.

        *turn_on* words the Scribe choice for an app where Scribe is switched
        off ("Turn on Scribe for Documents and convert"): it is offered on first
        need, straight after the person's own command (8.2).

        Returns ``"ocr"``, ``"scribe"``, ``"open"`` or ``"cancel"``.
        """
        import wx

        from quill.core.scribe.inputs import is_accepted

        if not is_accepted(path):  # Scribe is offered only for what it takes (3.1)
            return None
        controller = self._scribe()
        if controller.unavailable() or not controller.options().offer_low_text_pdf:
            return None
        pages = f"about {page_count} pages" if page_count else "pages"
        verb = f"Turn on {PRODUCT_NAME} and convert" if turn_on else f"Convert with {PRODUCT_NAME}"
        choices = [
            "Run free OCR on this computer (nothing is uploaded)",
            f"{verb} (rebuilds headings, tables and picture "
            f"descriptions; uses {pages} of your Scribe pages)",
            "Open the text there is",
        ]
        app = controller.app_name
        dialog = wx.SingleChoiceDialog(
            self._scribe_frame(),
            f"{path.name} has little or no readable text. It looks scanned. What should {app} do?",
            "Scanned Document",
            choices,
        )
        try:
            if self._scribe_modal(dialog, "Scanned Document") != wx.ID_OK:
                return "cancel"
            return ("ocr", "scribe", "open")[max(0, dialog.GetSelection())]
        finally:
            dialog.Destroy()


def player_target(format_id: str, path: Path) -> Path | None:
    """What Media Player opens for a result: the MP3, or a DAISY 3 book's
    ``.ncx`` (the zip unpacked beside itself). ``None`` if nothing: the Player
    reads DAISY 3 only, so a DAISY 2.02 ``ncc.html`` is never handed over and
    reported as open (Open Result goes on to the MP3)."""
    from quill.core.scribe.results import daisy_entry

    if format_id == "daisy":
        entry = daisy_entry(path)
        return entry if entry is not None and entry.suffix.lower() == ".ncx" else None
    return path if format_id == "mp3" else None


def send_to_player(format_id: str, path: Path) -> bool:
    """Open an MP3 or a DAISY book (its navigation file) in Quill Media Player."""
    from quill.core.app_launcher import launch_app

    target = player_target(format_id, path)
    return bool(target is not None and launch_app("player", extra_args=(str(target),)))


def open_in_browser(path: Path) -> bool:
    """Show a saved web page in the person's own browser (a local file: no egress)."""
    import wx

    return bool(wx.LaunchDefaultBrowser(path.resolve().as_uri()))


def browser_steps(
    ready: dict[str, Path], announce: Callable[[str], None]
) -> list[tuple[str, Callable[[], None]]]:
    """Next Steps' "Open in Your Browser (Web page for offline reading)": the
    offline web page, pictures and all, when it is one HTML file (F2)."""
    from quill.core.scribe.results import BROWSER_STEP

    page = ready.get("offline_html")
    if page is None or page.suffix.lower() != ".html":
        return []

    def show() -> None:
        if not open_in_browser(page):
            announce(f"Your browser could not be opened. {page.name} is saved in its folder.")

    return [(BROWSER_STEP, show)]


__all__ = [
    "SENDABLE",
    "ScribeEntryPoints",
    "browser_steps",
    "open_in_browser",
    "player_target",
    "send_to_player",
]
