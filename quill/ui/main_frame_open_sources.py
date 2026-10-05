"""Opening from a link, the clipboard or a drop; reopening; and the save check.

Five things from the 2026-10-04 PlanCake design note (PlanCake is Andre's, of
Oire Software), on ``MainFrame``. QUILL Lite has the same five through the same
shared modules (``quill/apps/lite_window_sources.py``), because QUILL Lite may
never be ahead of QUILL:

* **Open from URL** (moved here from ``main_frame.py``): asks before
  downloading, naming the host and the size; runs on the task manager with a
  progress window; says one plain sentence when it fails; and removes its temp
  file when the tab closes. The flow is ``quill/ui/open_from_url.py``.
* **Open from Clipboard** (Ctrl+Alt+Shift+Enter): files copied in File
  Explorer, a path copied as text, or a link, which goes through Open from URL.
* **Drag and drop**: files dropped on the window or the editor open; text
  dropped on the editor is still inserted.
* **Reopen with Encoding**, from the File Format window: the same bytes read
  again as the code page the person chooses.
* **Never overwrite an unseen change**: Save re-checks the file on disk and
  asks before writing over somebody else's change.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

__all__ = ["OpenSourcesMixin"]


class OpenSourcesMixin:
    """Mixed into ``MainFrame``; uses its usual helpers."""

    # Provided by MainFrame and its other mixins.
    _wx: Any
    frame: Any
    document: Any
    editor: Any
    settings: Any
    _document_tabs: list[Any]
    _task_manager: Any
    _external_change_watcher: Any

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #

    def _register_open_sources_commands(self) -> None:
        """Open from URL (no key: Open from Clipboard opens a copied link) and
        Open from Clipboard, on Ctrl+Alt+Shift+Enter in both editors."""
        commands = self.commands  # type: ignore[attr-defined]
        commands.register("file.open_url", "Open from URL...", self.open_url, None)
        commands.register(
            "file.open_from_clipboard",
            "Open from Clipboard",
            self.open_from_clipboard,
            self._binding_for("file.open_from_clipboard"),  # type: ignore[attr-defined]
        )

    def _command_to_menu_id_map(self) -> dict[str, int]:
        mapping: dict[str, int] = super()._command_to_menu_id_map()  # type: ignore[misc]
        mapping["file.open_from_clipboard"] = self._id_open_from_clipboard  # type: ignore[attr-defined]
        return mapping

    # ------------------------------------------------------------------ #
    # Open from URL
    # ------------------------------------------------------------------ #

    def open_url(self) -> None:
        from quill.ui.open_from_url import ask_for_url

        address = ask_for_url(self.frame)
        if not address:
            self._set_status("Open from URL cancelled")  # type: ignore[attr-defined]
            return
        self._open_link(address)

    def _open_link(self, address: str) -> bool:
        from quill.ui.open_from_url import UrlOpenFlow

        flow = UrlOpenFlow(
            self.frame,
            task_manager=self._task_manager,
            announce=self._announce,  # type: ignore[attr-defined]
            on_downloaded=self._open_downloaded,
            ask_yes_no=self._ask_url_question,
        )
        # Held so the flow lives as long as its download does.
        self._url_flow = flow
        return flow.start(address)

    def _ask_url_question(self, question: str, title: str) -> bool:
        wx = self._wx
        answer = self._show_message_box(  # type: ignore[attr-defined]
            question, title, wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION
        )
        return bool(answer == wx.YES)

    def _open_downloaded(self, download: Any) -> None:
        """Read a finished download into a new, read-only remote tab."""
        from quill.io.detect import STRUCTURED_EXTENSIONS
        from quill.io.http_transport import discard_download
        from quill.io.open_read import OFFICE_STREAM_SUFFIXES, read_open_document

        suffix = Path(download.filename).suffix.lower()
        selected_path = Path(download.local_path)
        try:
            if suffix in OFFICE_STREAM_SUFFIXES and (
                suffix in STRUCTURED_EXTENSIONS or suffix in {".odt", ".rtf", ".pages"}
            ):
                # Heavy formats parse on a worker so the window keeps answering.
                word_mode = (
                    self._resolve_word_open_mode(selected_path)  # type: ignore[attr-defined]
                    if suffix in {".doc", ".docx"}
                    else None
                )
                docx_engine = self._docx_read_engine()  # type: ignore[attr-defined]

                def _worker(_progress: object) -> tuple[object, object]:
                    return read_open_document(
                        selected_path, suffix, word_mode=word_mode, docx_engine=docx_engine
                    )

                self._run_background_task(  # type: ignore[attr-defined]
                    f"Opening {download.filename}",
                    _worker,
                    lambda result: self._install_remote_document(  # type: ignore[attr-defined]
                        result, suffix, download
                    ),
                )
                return
            result = read_open_document(selected_path, suffix or ".txt")
        except Exception:  # noqa: BLE001 - format dispatch can fail; one sentence
            discard_download(selected_path)
            self._announce(  # type: ignore[attr-defined]
                f"{download.filename} downloaded, but QUILL could not read it as a document."
            )
            return
        self._install_remote_document(result, suffix, download)  # type: ignore[attr-defined]

    def _discard_remote_download(self, tab: Any) -> None:
        """Remove the tab's Open from URL temp file, if it has one."""
        temp_path = str(getattr(tab, "remote_temp_path", "") or "")
        if temp_path:
            from quill.io.http_transport import discard_download

            discard_download(temp_path)
            tab.remote_temp_path = ""

    # ------------------------------------------------------------------ #
    # Open from Clipboard and drag and drop
    # ------------------------------------------------------------------ #

    def open_from_clipboard(self) -> None:
        """Open what the clipboard holds: files, a path, or a link."""
        from quill.core.open_sources import FILES, NOTHING_TO_OPEN, URL, clipboard_sentence
        from quill.ui.open_sources_ui import read_clipboard

        found = read_clipboard()
        if found.kind == FILES:
            for path in found.paths:
                self.open_file(path)  # type: ignore[attr-defined]
            sentence = clipboard_sentence(len(found.paths), found.skipped)
            if sentence:
                self._announce(sentence)  # type: ignore[attr-defined]
        elif found.kind == URL:
            self._open_link(found.url)
        else:
            self._announce(NOTHING_TO_OPEN)  # type: ignore[attr-defined]

    def _open_dropped_files(self, names: Sequence[str]) -> None:
        from quill.core.open_sources import dropped_sentence

        paths = [Path(name) for name in names]
        files = [path for path in paths if path.is_file()]
        for path in files:
            self.open_file(path)  # type: ignore[attr-defined]
        self._announce(dropped_sentence(len(files), len(paths) - len(files)))  # type: ignore[attr-defined]

    def _prepare_tab_sources(self, tab: Any) -> None:
        """Per new tab: its disk baseline, and drops on its editor and the frame."""
        self._remember_disk_baseline(tab)
        from quill.ui.open_sources_ui import install_file_drop

        frame = self.frame if not getattr(self, "_frame_drop_installed", False) else None
        install_file_drop(frame, tab.editor, self._open_dropped_files)
        self._frame_drop_installed = True

    # ------------------------------------------------------------------ #
    # Reopen with Encoding
    # ------------------------------------------------------------------ #

    def _can_reopen_with_encoding(self) -> bool:
        document = self.document
        path = getattr(document, "path", None)
        if path is None or not Path(path).is_file():
            return False
        tab = self._active_tab()  # type: ignore[attr-defined]
        if getattr(tab, "read_only_remote", False):
            return False
        return document.source_metadata.get("source_kind") == "text"

    def reopen_with_encoding(self, codec: str) -> None:
        """Read the open file again from disk as *codec*, strictly."""
        from quill.core.external_change import FileSnapshot
        from quill.core.text_decoding import decode_as, reopen_mismatch_sentence, reopened_sentence

        path = self.document.path
        if not codec or path is None:
            return
        if self.document.modified and not self._confirm_discard_changes():  # type: ignore[attr-defined]
            self._set_status("Reopen cancelled")  # type: ignore[attr-defined]
            return
        try:
            decoded = decode_as(Path(path).read_bytes(), codec)
        except UnicodeDecodeError:
            self._announce(reopen_mismatch_sentence(codec))  # type: ignore[attr-defined]
            return
        except (OSError, LookupError):
            self._announce(f"Could not read {Path(path).name} again.")  # type: ignore[attr-defined]
            return
        text = decoded.text
        line_ending = "\r\n" if "\r\n" in text else "\n"
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        caret = self.editor.GetInsertionPoint()
        self.document.set_text(text)
        self.document.encoding = decoded.encoding
        self.document.line_ending = line_ending
        self.document.modified = False
        self.editor.SetValue(text)
        self.document.modified = False
        capped = max(0, min(caret, len(text)))
        self.editor.SetInsertionPoint(capped)
        if self._external_change_watcher is not None:
            self._external_change_watcher.prime(FileSnapshot.of(path))
        self._remember_disk_baseline(self._active_tab())  # type: ignore[attr-defined]
        self._refresh_title()  # type: ignore[attr-defined]
        self._refresh_statusbar()  # type: ignore[attr-defined]
        self._announce(reopened_sentence(decoded.encoding))  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ #
    # Never overwrite an unseen change
    # ------------------------------------------------------------------ #

    def _remember_disk_baseline(self, tab: Any) -> None:
        """Note the file on disk as this tab sees it now (open, save, reload)."""
        if tab is None:
            return
        from quill.core.external_change import FileSnapshot

        path = getattr(getattr(tab, "document", None), "path", None)
        try:
            tab.disk_baseline = FileSnapshot.of(path) if path is not None else None
        except AttributeError:
            pass

    def _remember_disk_baseline_for(self, document: Any) -> None:
        """After a write: the tab holding *document* now knows the new file."""
        for tab in getattr(self, "_document_tabs", []):
            if getattr(tab, "document", None) is document:
                self._remember_disk_baseline(tab)
                return

    def _confirm_unseen_disk_change(self) -> bool:
        """True when Save may write; asks first if the file changed on disk."""
        from quill.core.external_change import changed_since
        from quill.ui.save_conflict_dialog import OVERWRITE, RELOAD, SAVE_AS, ask_save_conflict

        tab = self._active_tab()  # type: ignore[attr-defined]
        path = self.document.path
        if tab is None or path is None:
            return True
        if changed_since(getattr(tab, "disk_baseline", None), path) is None:
            return True
        answer = ask_save_conflict(self.frame, Path(path).name)
        if answer == OVERWRITE:
            return True
        if answer == RELOAD:
            self.document.modified = False
            self.open_file(path, record_recent=False, refresh_existing=True)  # type: ignore[attr-defined]
            self._remember_disk_baseline(self._active_tab())  # type: ignore[attr-defined]
            self._announce(f"Reloaded {Path(path).name} from disk.")  # type: ignore[attr-defined]
        elif answer == SAVE_AS:
            self.save_file_as()  # type: ignore[attr-defined]
        else:
            self._set_status("Save cancelled")  # type: ignore[attr-defined]
        return False
