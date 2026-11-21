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

* **File > Replace with Finished Document**, in the streaming tab
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
from quill.ui.scribe_entry import SENDABLE, ScribeEntryPoints
from quill.ui.scribe_entry import send_to_player as _send_to_player

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
    (
        "scribe.replace_finished",
        "Replace with Finished Doc&ument",
        "scribe_replace_finished",
        "file",
    ),
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
        from quill.core.scribe.results import default_action, opened_phrase

        action = default_action(format_id)
        if job.open_as == "import" and format_id in {"docx", "html", "epub"}:
            self._mf._scribe_open_as_import(job, path)
            return opened_phrase(format_id, "a new tab")
        if action in {"editor", "braille"}:
            self._mf.open_file(path)
            return opened_phrase(format_id, "QUILL")
        if action == "player" and _send_to_player(format_id, path):
            return opened_phrase(format_id, "Media Player")
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
            for label, command in (
                ("Read Aloud with QUILL's Voices", "toggle_read_aloud"),
                ("Check Accessibility (GLOW Audit)", "glow_audit_document"),
                ("Summarize with Your AI...", "open_ai_summarize_selection"),
            ):
                steps.append((named(label, format_id), self._then(path, command)))
        if "brf" in ready:
            steps.append(("Open in the Braille View", self._then(ready["brf"], "")))
        for format_id in ("mp3", "daisy"):
            if format_id in ready:
                label = f"Send to Media Player ({format_label(format_id)})"
                steps.append((label, lambda f=format_id: _send_to_player(f, ready[f])))
        return steps

    def _then(self, path: Path, command: str) -> Any:
        """Open *path* in QUILL (or go to its tab), then run QUILL's *command*.
        Nothing is said about the opening: the reader says the tab, and the
        command speaks for itself (review 2026-11-21)."""

        def run() -> None:
            import wx

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

    def _scribe_start(self) -> None:
        """At startup: pick up Scribe jobs another app or an earlier run left."""
        self._scribe().start_if_jobs_waiting()


__all__ = ["ROWS", "SENDABLE", "QuillScribeHost", "ScribeMixin"]
