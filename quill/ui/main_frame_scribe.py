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

* **Tools > Scribe for Documents > Replace with Finished Document**, in the streaming tab
  (:mod:`quill.ui.main_frame_scribe_stream`, 8.1.3).
* **Next Steps** in Scribe Conversions (8.1.7): Read Aloud with QUILL's
  voices, the GLOW accessibility check, the braille view, Summarize with the
  person's own AI, and the Media Player -- each a separate, chosen command.

The commands themselves are shared with QUILL Lite
(:class:`quill.ui.scribe_entry.ScribeEntryPoints`); this module is only where
they sit in QUILL and how QUILL opens a result.

The rows are placed by :meth:`_place_scribe_rows`, one call at the end of the
menu build, so the at-budget menu modules gain one line. Commands register
themselves (``self.commands.try_register``) with whatever the person bound in
the Keymap Editor (``_binding_for``), so every row is assignable and in the
Command Palette. No row has a default key: each is a once-in-a-while command
reached from its menu and the palette (rule 9), and the written reasons for
Scribe Status, Repeat Last Scribe Message and Replace with Finished Document
are in the family gate's ``UNBOUND_WITH_REASON``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.scribe import PRODUCT_NAME
from quill.core.scribe import queue as q
from quill.ui.main_frame_scribe_stream import ScribeStreamMixin
from quill.ui.scribe_entry import SENDABLE, ScribeEntryPoints, player_target
from quill.ui.scribe_entry import send_to_player as _send_to_player

#: What :meth:`ScribeMixin._scribe_open_as_import` returns when the converted
#: tab was still open and was brought forward rather than made again.
ALREADY_OPEN = "already open"

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
    # Not in File: with WordPress and Forms on, File has no letter left (all 36
    # are taken), and a row with no Alt letter has no route (menu accelerators gate).
    (
        "scribe.replace_finished",
        "Replace &with Finished Document",
        "scribe_replace_finished",
        "tools",
    ),
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
        from quill.ui.scribe_after_sentence import AfterSentence

        self._mf = frame_owner
        #: Media Player coming to the front waits for the result sentence.
        self._after = AfterSentence(still_here=lambda: self.scribe_in_front())

    def scribe_parent(self) -> Any:
        """The active window (Conversions, My Scribe Documents...) so a nested
        dialog returns focus to it, else the main window."""
        import wx

        return wx.GetActiveWindow() or self._mf.frame

    def scribe_announce(self, text: str) -> None:
        self._mf._announce(text)
        self._after.said(text)

    def scribe_status_text(self, text: str) -> None:
        """The latest Scribe sentence in the status bar, not spoken."""
        self._mf._set_status_quiet(text)

    def scribe_hold(self, opening: Any, phrase: str) -> None:
        """Open after the sentence carrying *phrase* (the browser, Media Player)."""
        self._after.hold(opening, phrase)

    def scribe_in_front(self) -> bool:
        import wx

        return wx.GetActiveWindow() is not None

    def scribe_ai_off(self) -> bool:
        choice = str(getattr(self._mf.settings, "ai_connection", "") or "").lower()
        return choice in {"off", "none"}

    def scribe_open_result(self, job: q.Job, format_id: str, path: Path) -> str:
        """Section 9: open the output in the tool where it is used."""
        from quill.core.scribe.results import OPENED_NAME, default_action, opened_phrase

        action = default_action(format_id)
        # The accessible HTML is read as a document (headings, lists, tables,
        # links), converted as Import does, never shown as its markup.
        if format_id == "html" or (job.open_as == "import" and format_id in {"docx", "epub"}):
            if self._mf._scribe_open_as_import(job, path) == ALREADY_OPEN:
                # The reader says the tab's name as it is selected: not repeated here.
                return f"{OPENED_NAME.get(format_id, 'The result')} is already open"
            return opened_phrase(format_id, "a new tab")
        if action in {"editor", "braille"}:
            self._mf.open_file(path)
            return opened_phrase(format_id, "QUILL")
        if action == "player" and player_target(format_id, path) is not None:
            # Media Player comes to the front: after the sentence, not under it.
            phrase = opened_phrase(format_id, "Media Player")
            self._after.hold(lambda: self._to_player(job, format_id, path), phrase)
            return phrase
        return ""

    # -- the streaming tab (main_frame_scribe_stream, 8.1.3) -----------------

    def scribe_stream_started(self, job: q.Job) -> None:
        self._mf._scribe_open_stream_tab(job)

    def scribe_stream_finished(self, job: q.Job) -> str:
        return str(self._mf._scribe_stream_finished_phrase(job))

    # -- Next Steps (8.1.7): each a separate command the person chooses ------

    def scribe_next_steps(self, job: q.Job, ready: dict[str, Path]) -> list[tuple[str, Any]]:
        """QUILL's own commands on what was made, named by format when there
        are several (accessibility review, 2026-11-21)."""
        from quill.core.scribe.model import format_label

        editable = [f for f in ("docx", "html", "epub") if f in ready]
        steps: list[tuple[str, Any]] = []

        def named(label: str, format_id: str) -> str:
            return f"{label} ({format_label(format_id)})" if len(editable) > 1 else label

        for format_id in editable:
            path = ready[format_id]
            commands = [
                # read_all, not the Start/Pause toggle: from the top, never a pause.
                ("Read Aloud with QUILL's Voices", "read_all"),
                ("Check Accessibility (GLOW Audit)", "glow_audit_document"),
            ]
            if not self.scribe_ai_off():  # a command that would only refuse is not offered
                commands.append(("Summarize with Your AI...", "open_ai_summarize_selection"))
            for label, command in commands:
                steps.append((named(label, format_id), self._then(path, command, job)))
        steps += self._beacon_steps(job, ready, named)
        if "pdf" in ready:
            steps.append((f"Open in QUILL ({format_label('pdf')})", self._then(ready["pdf"], "")))
        if "brf" in ready:
            steps.append(("Open in the Braille View", self._then(ready["brf"], "")))
        if "mobi" in ready:
            steps.append(("Open the Kindle Book (MOBI)", self._then(ready["mobi"], "")))
        for format_id in ("mp3", "daisy"):
            if format_id in ready:
                label = f"Send to Media Player ({format_label(format_id)})"
                steps.append((label, lambda f=format_id: self._to_player(job, f, ready[f])))
        from quill.ui.scribe_entry import browser_steps

        return steps + browser_steps(ready, self.scribe_announce)  # pictures and all (F2)

    def _beacon_steps(self, job: q.Job, ready: dict[str, Path], named: Any) -> list[Any]:
        """Save a Beacon Place, for Word and HTML, where Beacon is (8.1.7, 8.7)."""
        from quill.ui.scribe_beacon_place import beacon_available, save_beacon_place

        places = [f for f in ("docx", "html") if f in ready]
        if not places or not job.document_id or not beacon_available():
            return []

        def save(format_id: str) -> None:
            save_beacon_place(
                job,
                format_id,
                ready[format_id],
                parent=self.scribe_parent(),
                say=self.scribe_announce,
                modal=self._mf._show_modal_dialog,
            )

        return [(named("Save a Beacon Place", f) + "...", lambda f=f: save(f)) for f in places]

    def _to_player(self, job: q.Job, format_id: str, path: Path) -> None:
        """Send to Media Player, saying so when it could not be opened."""
        if not _send_to_player(format_id, path):
            self.scribe_announce(
                f"Media Player could not be opened. {job.display_name} is saved in its folder."
            )

    def _then(self, path: Path, command: str, job: q.Job | None = None) -> Any:
        """Open *path* in QUILL (or go to its tab), then run QUILL's *command*.
        The accessible HTML opens as a readable document, never its markup.
        Nothing is said about the opening: the reader says the tab, and the
        command speaks for itself (review 2026-11-21)."""

        def run() -> None:
            import wx

            if path.suffix.lower() in {".html", ".htm"} and job is not None:
                self._mf._scribe_open_as_import(job, path)
            else:
                self._mf.open_file(path)
            if command:
                wx.CallAfter(getattr(self._mf, command))

        return run


class ScribeMixin(ScribeStreamMixin, ScribeEntryPoints):
    """QUILL's Scribe for Documents entry points."""

    def _scribe(self) -> Any:
        from quill.ui.scribe_controller import controller_for

        host = getattr(self, "_scribe_host", None)
        if host is None:
            host = QuillScribeHost(self)
            self._scribe_host = host
        return controller_for(host)

    def _scribe_open_as_import(self, job: q.Job, path: Path) -> str:
        """Import / Convert's Scribe tier: a new unsaved tab "<stem> (Scribe)".

        The same file converted again while its tab is still open goes to that
        tab instead of making a second copy: returns :data:`ALREADY_OPEN`, and
        the caller says so once. ``"opened"``, or ``""`` when it could not be read.
        """
        from quill.core.document import Document
        from quill.core.import_convert import opened_sentence, scribe_name
        from quill.io.docconvert import TIER_SCRIBE, convert_document

        shown: dict[str, Any] = self.__dict__.setdefault("_scribe_readable", {})
        earlier = shown.get(str(path))
        tabs = list(getattr(self, "_document_tabs", []))
        for index, tab in enumerate(tabs):
            if earlier is not None and getattr(tab, "document", None) is earlier:
                self._select_tab(index)  # type: ignore[attr-defined]
                return ALREADY_OPEN
        shown.pop(str(path), None)
        try:
            outcome = convert_document(path)
        except Exception as error:  # noqa: BLE001 - said, never raised into the queue
            self._announce(f"{PRODUCT_NAME} made {path.name}, but QUILL could not read it: {error}")  # type: ignore[attr-defined]
            return ""
        outcome.tier = TIER_SCRIBE
        document = Document(text=outcome.text, path=None, modified=True)
        index = self._create_document_tab(document, select=True)  # type: ignore[attr-defined]
        shown[str(path)] = document
        stem = Path(job.file_name).stem or path.stem
        self._set_tab_page_text(index, scribe_name(stem))  # type: ignore[attr-defined]
        self._set_status(opened_sentence(job.file_name or path.name, outcome))  # type: ignore[attr-defined]
        return "opened"

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
            self._scribe_wire_watch()

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
            binding = getattr(self, "_binding_for", lambda _c: None)(command_id)
            self.commands.try_register(  # type: ignore[attr-defined]
                command_id,
                f"{PRODUCT_NAME}: {title.replace('&', '').removesuffix('...')}",
                (lambda h=handler: getattr(self, h)()),
                binding,  # a key the person gave it in the Keymap Editor
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

    # ------------------------------------------- the shared commands' hooks

    def _scribe_frame(self) -> Any:
        return self.frame  # type: ignore[attr-defined]

    def _scribe_modal(self, dialog: Any, title: str) -> int:
        return int(self._show_modal_dialog(dialog, title))  # type: ignore[attr-defined]

    def _scribe_say(self, text: str) -> None:
        self._announce(text)  # type: ignore[attr-defined]

    def _scribe_document(self) -> tuple[Path | None, bool, str] | None:
        document = getattr(self, "document", None)
        if document is None:
            return None
        path = Path(document.path) if document.path else None
        return path, bool(getattr(document, "modified", False)), str(document.text)

    def _scribe_save_document(self) -> None:
        self.save_file()  # type: ignore[attr-defined]

    def _scribe_show_about(self, title: str, text: str) -> None:
        self._html_info(title, text)  # type: ignore[attr-defined]

    def _scribe_wire_watch(self) -> None:
        """Give the watch folder's Scribe action this app's runner (8.1.6): it
        wakes the family queue and asks whether the person is signed in."""
        import wx

        service = getattr(self, "_watch_service", None)
        registry = getattr(service, "registry", None)
        action = registry.get("scribe_convert") if registry is not None else None
        if action is None:
            return
        controller = self._scribe()  # made here, on the UI thread
        action.app_name = controller.app_name
        action.on_wake = lambda: wx.CallAfter(controller.wake)
        action.signed_in = lambda: bool(controller.session.is_signed_in())

    # -- Explorer's Send To (8.10) ---------------------------------------------

    def _scribe_shell_request(self, path: Path) -> None:
        """Send To > Convert with Scribe for Documents: one Convert dialog for
        every file sent together (each arrives as its own request)."""
        import wx

        pending: list[Path] = self.__dict__.setdefault("_scribe_send_to", [])
        if not pending:
            wx.CallLater(400, self._scribe_send_to_flush)
        if Path(path) not in pending:
            pending.append(Path(path))

    def _scribe_send_to_flush(self) -> None:
        """Bring QUILL forward, then open the dialog; never over another dialog."""
        import wx

        frame = self.frame  # type: ignore[attr-defined]
        if not self.__dict__.get("_scribe_send_to_raised"):  # once, never on a retry
            self.__dict__["_scribe_send_to_raised"] = True
            if frame.IsIconized():
                frame.Iconize(False)
            frame.Show()
            frame.Raise()
        active = wx.GetActiveWindow()
        # A native modal (a file picker, a message box) is invisible to
        # GetActiveWindow, but every modal disables the window that owns it.
        busy = not frame.IsEnabled() or (isinstance(active, wx.Dialog) and active.IsModal())
        if busy:
            if not self.__dict__.get("_scribe_send_to_said"):
                self.__dict__["_scribe_send_to_said"] = True
                title = active.GetTitle() if isinstance(active, wx.Dialog) else ""
                self._announce(  # type: ignore[attr-defined]
                    f"Convert with {PRODUCT_NAME} is waiting until you close "
                    f"{title or 'the window that is open'}."
                )
            wx.CallLater(1000, self._scribe_send_to_flush)
            return
        paths = list(self.__dict__.pop("_scribe_send_to", []))
        self.__dict__.pop("_scribe_send_to_said", None)
        self.__dict__.pop("_scribe_send_to_raised", None)
        if paths:
            self._scribe().convert_files(paths)

    def _scribe_start(self) -> None:
        """At startup: pick up Scribe jobs another app or an earlier run left."""
        self._scribe().start_if_jobs_waiting()


__all__ = ["ALREADY_OPEN", "ROWS", "SENDABLE", "QuillScribeHost", "ScribeMixin"]
