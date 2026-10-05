"""Opening from a link, the clipboard or a drop; reopening; and the save check.

QUILL Lite's half of the 2026-10-04 PlanCake design note (PlanCake is Andre's,
of Oire Software). QUILL has the same five things, from the same shared
modules, in ``quill/ui/main_frame_open_sources.py`` -- QUILL Lite may never be
ahead of QUILL, and here it is not even allowed to be different:

* **Open from URL** -- the shared flow in ``quill/ui/open_from_url.py``: it
  asks before downloading, naming the host and the size; downloads on the
  app's task manager with a progress window; and says one sentence when it
  fails. The downloaded text opens as an untitled document named after the
  file, and the temp file is removed as soon as it is read.
* **Open from Clipboard** (Ctrl+Alt+Shift+Enter) -- files copied in File
  Explorer, a path copied as text, or a link.
* **Drag and drop** -- files dropped on the window or the editor open; text
  dropped on the editor is still inserted where it lands.
* **Reopen with Encoding** -- from the File Encoding window: the same bytes,
  read again strictly as the code page chosen.
* **Never overwrite an unseen change** -- Save re-checks the file on disk and
  asks before writing over a change another program made.

Composed onto ``DocumentFrame``, which supplies ``app``, ``control``,
``editor``, ``path``, ``encoding``, ``newline`` and the announcement hooks.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import wx

__all__ = ["DocumentSourcesMixin"]


class DocumentSourcesMixin:
    """Open from URL and the clipboard, drops, Reopen with Encoding, save check."""

    # ------------------------------------------------------------------ #
    # Open from URL
    # ------------------------------------------------------------------ #

    def cmd_open_from_url(self) -> None:
        """Ask for a web address and open the document at it, after asking."""
        from quill.ui.open_from_url import ask_for_url

        address = ask_for_url(self)
        if not address:
            return
        self._open_link(address)

    def _open_link(self, address: str) -> bool:
        from quill.apps.lite_window_open import app_task_manager
        from quill.ui.open_from_url import UrlOpenFlow

        flow = UrlOpenFlow(
            self,
            task_manager=app_task_manager(self.app),
            announce=self._announce,
            on_downloaded=self._open_downloaded,
        )
        self._url_flow = flow
        return flow.start(address)

    def _open_downloaded(self, download: Any) -> None:
        """Read the download into a window, then remove the temp file."""
        from quill.core.lite.filetypes import is_rich_path
        from quill.core.lite.open_prepare import PLAIN, RICH
        from quill.core.lite.open_prepare import prepare as prepare_document
        from quill.io.http_transport import discard_download

        filename = str(getattr(download, "filename", "") or "download")
        mode = RICH if is_rich_path(filename) else PLAIN
        try:
            prepared = prepare_document(Path(download.local_path), mode)
        except OSError:
            self._announce(f"{filename} downloaded, but could not be read.")
            return
        finally:
            discard_download(download.local_path)
        target = self if self._is_blank() else self.app.new_window(mode)
        target._commit_download(prepared, filename)

    def _commit_download(self, prepared: Any, filename: str) -> None:
        """An untitled document named after the download, unsaved until saved."""
        self._loading = True
        try:
            if prepared.mode == "rich":
                self._commit_rich(prepared)
            else:
                self._commit_plain(prepared)
        except Exception:  # noqa: BLE001 - one sentence, the window stays as it was
            self._announce(f"{filename} downloaded, but could not be shown.")
            return
        finally:
            self._loading = False
            self.doc_text.invalidate()
        self.path = None
        self.download_name = filename
        self._set_modified(True)
        self.control.SetInsertionPoint(0)
        self._update_title()
        self._sync_menu_rows()
        self._touch_status()
        try:
            self.control.SetFocus()
        except RuntimeError:
            pass

    # ------------------------------------------------------------------ #
    # Open from Clipboard and drag and drop
    # ------------------------------------------------------------------ #

    def cmd_open_from_clipboard(self) -> None:
        """Open what the clipboard holds: files, a path, or a link."""
        from quill.core.open_sources import FILES, NOTHING_TO_OPEN, URL, clipboard_sentence
        from quill.ui.open_sources_ui import read_clipboard

        found = read_clipboard()
        if found.kind == FILES:
            self._open_paths(found.paths)
            sentence = clipboard_sentence(len(found.paths), found.skipped)
            if sentence:
                self._announce(sentence)
        elif found.kind == URL:
            self._open_link(found.url)
        else:
            self._announce(NOTHING_TO_OPEN)

    def _open_paths(self, paths: Sequence[Path]) -> None:
        for index, path in enumerate(paths):
            # As Open does: only the first file may claim this window, and only
            # if it is empty.
            reuse = self if index == 0 and self._is_blank() else None
            self.app.open_path(path, reuse=reuse)

    def _open_dropped_files(self, names: Sequence[str]) -> None:
        from quill.core.open_sources import dropped_sentence

        paths = [Path(name) for name in names]
        files = [path for path in paths if path.is_file()]
        self._open_paths(files)
        self._announce(dropped_sentence(len(files), len(paths) - len(files)))

    def _install_file_drop(self) -> None:
        from quill.ui.open_sources_ui import install_file_drop

        install_file_drop(self, self.control, self._open_dropped_files)

    # ------------------------------------------------------------------ #
    # Reopen with Encoding
    # ------------------------------------------------------------------ #

    def _can_reopen_with_encoding(self) -> bool:
        return self.path is not None and Path(self.path).is_file()

    def reopen_with_encoding(self, codec: str) -> None:
        """Read the open file again from disk as *codec*, strictly."""
        from quill.core.text_decoding import decode_as, reopen_mismatch_sentence, reopened_sentence
        from quill.ui.dialog_contract import show_message_box

        if not codec or self.path is None:
            return
        if self.modified:
            answer = show_message_box(
                "Reopening discards your unsaved changes to this document. Reopen anyway?",
                "Reopen with Encoding",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
                self,
            )
            if answer != wx.YES:
                self._announce("Reopen cancelled")
                return
        try:
            decoded = decode_as(Path(self.path).read_bytes(), codec)
        except UnicodeDecodeError:
            self._announce(reopen_mismatch_sentence(codec))
            return
        except (OSError, LookupError):
            self._announce(f"Could not read {Path(self.path).name} again.")
            return
        # The newline rule is the reader's own, so a reopen and an open agree.
        raw_text = decoded.text
        newline = "\r\n" if "\r\n" in raw_text else ("\r" if "\r" in raw_text else "\n")
        text = decoded.text.replace("\r\n", "\n").replace("\r", "\n")
        caret = self.control.GetInsertionPoint()
        self._loading = True
        try:
            self.control.ChangeValue(text)
        finally:
            self._loading = False
            self.doc_text.invalidate()
        self.encoding, self.newline = decoded.encoding, newline
        self.control.SetInsertionPoint(max(0, min(caret, len(text))))
        self._set_modified(False)
        self._remember_disk_baseline()
        self._update_title()
        self._touch_status()
        self._announce(reopened_sentence(decoded.encoding))

    # ------------------------------------------------------------------ #
    # Never overwrite an unseen change
    # ------------------------------------------------------------------ #

    def _remember_disk_baseline(self) -> None:
        """Note the file on disk as this window last saw it (open, save, reopen)."""
        from quill.core.external_change import FileSnapshot

        self._disk_baseline = FileSnapshot.of(self.path) if self.path is not None else None

    def _confirm_unseen_disk_change(self, destination: Path) -> bool:
        """True when Save may write *destination*; asks if it changed on disk."""
        from quill.core.external_change import changed_since
        from quill.core.lite import APP_NAME
        from quill.ui.save_conflict_dialog import OVERWRITE, RELOAD, SAVE_AS, ask_save_conflict

        if self.path is None or Path(destination) != Path(self.path):
            return True
        if changed_since(getattr(self, "_disk_baseline", None), destination) is None:
            return True
        answer = ask_save_conflict(self, Path(destination).name, app_name=APP_NAME)
        if answer == OVERWRITE:
            return True
        if answer == RELOAD:
            path = Path(self.path)
            if self.load(path):
                self._announce(f"Reloaded {path.name} from disk.")
        elif answer == SAVE_AS:
            self.cmd_save_as()
        else:
            self._announce("Save cancelled")
        return False
