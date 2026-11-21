"""Scribe for Documents in QUILL (PRD 8.1), a MainFrame mixin.

Everything shared lives in :class:`quill.ui.scribe_controller.ScribeController`;
this mixin is QUILL's host adapter and its entry points:

* **Tools > Scribe for Documents**: Convert a File..., Convert This
  Document..., Convert from a Link..., My Scribe Documents, Conversions,
  Scribe Status, Repeat Last Scribe Message, Sign In..., Sign Out, Open My
  Scribe Account in Browser, Options..., About Scribe for Documents.
* **File > My Scribe Documents**, **File > Import > Convert with Scribe for
  Documents...** (the Scribe tier of Import / Convert: Word by default, opened
  as a new unsaved tab "<stem> (Scribe)"), **File > Export > With Scribe for
  Documents...** (tagged PDF, MOBI, DAISY with audio, large print: what QUILL's
  own export cannot make; its own EPUB, Word, BRF and text-only DAISY stay).
* **Tools > Braille > Translate with Scribe for Documents...** (BRF with
  Scribe's table and page settings, opened in QUILL's braille view).
* **Window > Scribe Conversions**.
* The scanned-PDF and Import questions offer Scribe when "Offer Scribe when
  a PDF has little or no text" is on and Scribe is available.

The rows are placed by :meth:`_place_scribe_rows`, one call at the end of the
menu build, so the at-budget menu modules gain one line. Commands register
themselves (``self.commands.try_register``) as the Forms rows do. Keys are
deliberately none: every command is a once-in-a-while command reached from
its menu and the Command Palette (rule 9); Scribe Status and Repeat Last
Scribe Message are the two the PRD wants keyed, left for Jeff to choose.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from quill.core.scribe import PRODUCT_NAME
from quill.core.scribe import queue as q
from quill.core.scribe.inputs import ACCEPTED_EXTENSIONS

#: (command id, title, handler, place). Places: tools (the submenu), file,
#: import, export, braille, window.
ROWS: tuple[tuple[str, str, str, str], ...] = (
    ("scribe.convert_file", "Convert a &File...", "scribe_convert_file", "tools"),
    ("scribe.convert_this", "Convert &This Document...", "scribe_convert_this", "tools"),
    ("scribe.convert_link", "Convert from a &Link...", "scribe_convert_link", "tools"),
    ("scribe.my_documents", "&My Scribe Documents", "scribe_my_documents", "tools"),
    ("scribe.conversions", "&Conversions", "scribe_conversions", "tools"),
    ("scribe.status", "Scribe &Status", "scribe_status", "tools"),
    ("scribe.repeat", "&Repeat Last Scribe Message", "scribe_repeat", "tools"),
    ("scribe.sign_in", "Sign &In...", "scribe_sign_in", "tools"),
    ("scribe.sign_out", "Sign &Out", "scribe_sign_out", "tools"),
    ("scribe.account", "Open My Scribe &Account in Browser", "scribe_account", "tools"),
    ("scribe.options", "O&ptions...", "scribe_options", "tools"),
    ("scribe.about", "A&bout Scribe for Documents", "scribe_about", "tools"),
    ("scribe.file_documents", "My Scribe Doc&uments", "scribe_my_documents", "file"),
    ("scribe.import", "Convert with &Scribe for Documents...", "scribe_import_file", "import"),
    ("scribe.export", "With &Scribe for Documents...", "scribe_export", "export"),
    ("scribe.braille", "Translate with &Scribe for Documents...", "scribe_braille", "braille"),
    ("scribe.window", "Scribe &Conversions", "scribe_conversions", "window"),
)

#: Files Scribe takes as they are: the 23 types Pneuma confirmed (3.1). Anything
#: else -- Markdown, and HTML, which Scribe refuses -- QUILL saves as DOCX first.
SENDABLE = ACCEPTED_EXTENSIONS


def _submenu_named(menu: Any, name: str) -> Any:
    for item in menu.GetMenuItems():
        sub = item.GetSubMenu()
        if sub is not None and item.GetItemLabelText().replace("&", "") == name:
            return sub
    return None


def _before_exit(menu: Any) -> int | None:
    """File: above the separator before Exit, which stays last."""
    import wx

    if menu is None:
        return None
    items = list(menu.GetMenuItems())
    at = next((i for i, it in enumerate(items) if it.GetId() == wx.ID_EXIT), len(items))
    if at > 0 and items[at - 1].IsSeparator():
        at -= 1
    return at


def _before_documents(menu: Any) -> int | None:
    """Window: before the last separator, after which open documents are listed."""
    if menu is None:
        return None
    items = list(menu.GetMenuItems())
    separators = [i for i, it in enumerate(items) if it.IsSeparator()]
    return separators[-1] if separators else len(items)


class QuillScribeHost:
    """QUILL's side of :class:`quill.ui.scribe_controller.ScribeHost`."""

    app_name = "QUILL"

    def __init__(self, frame_owner: Any) -> None:
        self._mf = frame_owner

    def scribe_parent(self) -> Any:
        """The active window (Conversions, My Scribe Documents...) so a nested
        dialog returns focus to it, else the main window."""
        import wx

        return wx.GetActiveWindow() or self._mf.frame

    def scribe_announce(self, text: str) -> None:
        self._mf._announce(text)

    def scribe_in_front(self) -> bool:
        import wx

        return wx.GetActiveWindow() is not None

    def scribe_ai_off(self) -> bool:
        choice = str(getattr(self._mf.settings, "ai_connection", "") or "").lower()
        return choice in {"off", "none"}

    def scribe_open_result(self, job: q.Job, format_id: str, path: Path) -> str:
        """Section 9: open the output in the tool where it is used."""
        from quill.core.scribe.results import daisy_entry, default_action, opened_phrase

        action = default_action(format_id)
        if job.open_as == "import" and format_id in {"docx", "html", "epub"}:
            self._mf._scribe_open_as_import(job, path)
            return opened_phrase(format_id, "a new tab")
        if action in {"editor", "braille"}:
            self._mf.open_file(path)
            return opened_phrase(format_id, "QUILL")
        if action == "player":
            from quill.core.app_launcher import launch_app

            target = daisy_entry(path) if format_id == "daisy" else path
            if target is not None and launch_app("player", extra_args=(str(target),)):
                return opened_phrase(format_id, "Media Player")
        return ""


class ScribeMixin:
    """QUILL's Scribe for Documents entry points."""

    def _scribe(self) -> Any:
        from quill.ui.scribe_controller import controller_for

        host = getattr(self, "_scribe_host", None)
        if host is None:
            host = QuillScribeHost(self)
            self._scribe_host = host
        return controller_for(host)

    def _scribe_open_as_import(self, job: q.Job, path: Path) -> None:
        """Import / Convert's Scribe tier: a new unsaved tab "<stem> (Scribe)"."""
        from quill.core.document import Document
        from quill.core.import_convert import opened_sentence, scribe_name
        from quill.io.docconvert import TIER_SCRIBE, convert_document

        try:
            outcome = convert_document(path)
        except Exception as error:  # noqa: BLE001 - said, never raised into the queue
            self._announce(f"{PRODUCT_NAME} made {path.name}, but QUILL could not read it: {error}")  # type: ignore[attr-defined]
            return
        outcome.tier = TIER_SCRIBE
        index = self._create_document_tab(  # type: ignore[attr-defined]
            Document(text=outcome.text, path=None, modified=True), select=True
        )
        stem = Path(job.file_name).stem or path.stem
        self._set_tab_page_text(index, scribe_name(stem))  # type: ignore[attr-defined]
        self._set_status(opened_sentence(job.file_name or path.name, outcome))  # type: ignore[attr-defined]

    # ------------------------------------------------------------- the menus

    def _place_scribe_rows(self, menu_bar: Any) -> None:
        """Put every Scribe row in its place (one call from the menu build)."""
        import wx

        ids = getattr(self, "_scribe_ids", None)
        if ids is None:
            ids = {command_id: wx.NewIdRef() for command_id, *_rest in ROWS}
            self._scribe_ids = ids
            # Once, after startup's own messages: pick up jobs left running (7.4).
            wx.CallLater(5000, self._scribe_start)

        def menu(title: str) -> Any:
            index = menu_bar.FindMenu(title)
            return menu_bar.GetMenu(index) if index != wx.NOT_FOUND else None

        file_menu, tools_menu, window_menu = menu("File"), menu("Tools"), menu("Window")
        places: dict[str, Any] = {
            "file": file_menu,
            "import": _submenu_named(file_menu, "Import") if file_menu else None,
            "export": _submenu_named(file_menu, "Export") if file_menu else None,
            "braille": _submenu_named(tools_menu, "Braille") if tools_menu else None,
            "window": window_menu,
            "tools": None,
        }
        if tools_menu is not None:
            places["tools"] = wx.Menu()
            tools_menu.AppendSubMenu(places["tools"], f"&{PRODUCT_NAME}")
        for place in ("export", "braille"):
            if places[place] is not None:
                places[place].AppendSeparator()
        positions = {"file": _before_exit(file_menu), "window": _before_documents(window_menu)}
        for command_id, title, handler, place in ROWS:
            target = places.get(place)
            if target is None:
                continue
            self.commands.try_register(  # type: ignore[attr-defined]
                command_id,
                f"{PRODUCT_NAME}: {title.replace('&', '').removesuffix('...')}",
                (lambda h=handler: getattr(self, h)()),
                None,
            )
            label = self._menu_label(title, command_id)  # type: ignore[attr-defined]
            at = positions.get(place)
            if at is None:
                target.Append(ids[command_id], label)
            else:
                target.Insert(at, ids[command_id], label)
                positions[place] = at + 1
            self.frame.Bind(  # type: ignore[attr-defined]
                wx.EVT_MENU, lambda _e, h=handler: getattr(self, h)(), id=ids[command_id]
            )

    def _command_to_menu_id_map(self) -> dict[str, int]:
        mapping: dict[str, int] = super()._command_to_menu_id_map()  # type: ignore[misc]
        if getattr(self, "_scribe_ids", None):
            mapping.update(self._scribe_ids)
        return mapping

    # -------------------------------------------------------------- commands

    def scribe_convert_file(self) -> None:
        self._scribe_pick_and_convert(multiple=True, app_formats=None, open_as="")

    def scribe_import_file(self, path: Path | None = None) -> None:
        """Import / Convert's Scribe tier: Word, opened as a new tab (8.1.1)."""
        if path is None:
            self._scribe_pick_and_convert(multiple=False, app_formats=["docx"], open_as="import")
            return
        self._scribe().convert_files([path], app_formats=["docx"], open_as="import")

    def _scribe_pick_and_convert(self, *, multiple: bool, app_formats: Any, open_as: str) -> None:
        import wx

        from quill.core.scribe.inputs import input_wildcard

        controller = self._scribe()
        if not controller.check_available():
            return
        style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | (wx.FD_MULTIPLE if multiple else 0)
        dialog = wx.FileDialog(
            self.frame,  # type: ignore[attr-defined]
            f"Convert with {PRODUCT_NAME}",
            wildcard=input_wildcard(),  # only what Scribe takes (3.1)
            style=style,
        )
        try:
            if self._show_modal_dialog(dialog, f"Convert with {PRODUCT_NAME}") != wx.ID_OK:  # type: ignore[attr-defined]
                return
            paths = [Path(p) for p in dialog.GetPaths()] if multiple else [Path(dialog.GetPath())]
        finally:
            dialog.Destroy()
        controller.convert_files(paths, app_formats=app_formats, open_as=open_as)

    def _scribe_current_file(self) -> Path | None:
        """The current document as a file Scribe takes: saved first (8.1.4)."""
        document = getattr(self, "document", None)
        if document is None:
            self._announce("Open or create a document first.")  # type: ignore[attr-defined]
            return None
        if getattr(document, "modified", False) or document.path is None:
            self.save_file()  # type: ignore[attr-defined]
            if document.path is None or document.modified:
                self._announce("Nothing was sent: the document needs saving first.")  # type: ignore[attr-defined]
                return None
        path = Path(document.path)
        if path.suffix.lower() in SENDABLE:
            return path
        return self._scribe_as_docx(path)

    def _scribe_as_docx(self, path: Path) -> Path | None:
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
        target.write_text(self.document.text, encoding="utf-8")  # type: ignore[attr-defined]
        return target

    def scribe_convert_this(self) -> None:
        self._scribe_send_current(app_formats=None, open_as="")

    def scribe_export(self) -> None:
        """File > Export > With Scribe for Documents...: every Scribe format."""
        self._scribe_send_current(app_formats=["pdf"], open_as="")

    def scribe_braille(self) -> None:
        """Braille > Translate with Scribe for Documents...: BRF, in the braille view."""
        self._scribe_send_current(app_formats=["brf"], open_as="braille")

    def _scribe_send_current(self, *, app_formats: Any, open_as: str) -> None:
        controller = self._scribe()
        if not controller.check_available():
            return
        path = self._scribe_current_file()
        if path is None:
            return
        title = Path(self.document.path).stem if self.document.path else path.stem  # type: ignore[attr-defined]
        controller.convert_files([path], app_formats=app_formats, open_as=open_as, title=title)

    def scribe_convert_link(self) -> None:
        import wx

        controller = self._scribe()
        if not controller.check_available():
            return
        dialog = wx.TextEntryDialog(
            self.frame,  # type: ignore[attr-defined]
            "The address of a file (a PDF or a document, not a web page or a page behind a "
            "sign-in):",
            "Convert from a Link",
        )
        try:
            if self._show_modal_dialog(dialog, "Convert from a Link") != wx.ID_OK:  # type: ignore[attr-defined]
                return
            url = dialog.GetValue().strip()
        finally:
            dialog.Destroy()
        if not url.lower().startswith(("https://", "http://")):
            self._announce("That is not a web address. Nothing was sent.")  # type: ignore[attr-defined]
            return
        controller.convert_url(url)

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
            self._announce(f"You are already signed in to {PRODUCT_NAME}.")  # type: ignore[attr-defined]
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
        self._html_info(f"About {PRODUCT_NAME}", self._scribe().about())  # type: ignore[attr-defined]

    # ---------------------------------------------------- the scanned offer

    def _scribe_scanned_choice(self, path: Path, page_count: int) -> str | None:
        """The scanned-PDF question with Scribe in it (8.1.2), or ``None`` when
        Scribe is not offered and the plain OCR question should be asked.

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
        choices = [
            "Run free OCR on this computer (nothing is uploaded)",
            f"Convert with {PRODUCT_NAME} (rebuilds headings, tables and picture "
            f"descriptions; uses {pages} of your Scribe credit)",
            "Open the text there is",
        ]
        dialog = wx.SingleChoiceDialog(
            self.frame,  # type: ignore[attr-defined]
            f"{path.name} has little or no readable text. It looks scanned. What should QUILL do?",
            "Scanned Document",
            choices,
        )
        try:
            if self._show_modal_dialog(dialog, "Scanned Document") != wx.ID_OK:  # type: ignore[attr-defined]
                return "cancel"
            return ("ocr", "scribe", "open")[max(0, dialog.GetSelection())]
        finally:
            dialog.Destroy()

    def _scribe_start(self) -> None:
        """At startup: pick up Scribe jobs another app or an earlier run left."""
        self._scribe().start_if_jobs_waiting()


__all__ = ["ROWS", "ScribeMixin"]
