"""Editing over SSH and remote sites on QUILL's main window: open, save, save a
copy, manage sites, and the download and upload behind them.

Moved whole out of ``MainFrame`` under qc.md F-08 (2026-10-03); the host
contract is unchanged: these methods use the same ``self`` attributes they did.
"""

from __future__ import annotations

import os
from pathlib import Path

from quill.core.document import Document
from quill.core.error_codes import user_facing_message
from quill.core.locations import LocationRing
from quill.core.url_ops import format_content_length
from quill.io.open_read import read_open_document


class RemoteFilesMixin:
    """Open from and save to remote sites; mixed into ``MainFrame``."""

    def _install_remote_document(
        self,
        result: object,
        suffix: str,
        download: object,
    ) -> None:
        """Open a downloaded URL document and tag the tab as a remote view."""

        assert isinstance(result, tuple)
        loaded, epub_book = result
        self._epub_book = epub_book if suffix == ".epub" else None
        self._create_document_tab(loaded, select=True)
        # Tag the tab as remote-sourced; saves go to "Save Copy to Local File..."
        # rather than the original URL.
        try:
            current_tab = self._document_tabs[-1]
            current_tab.source_label = f"from {getattr(download, 'final_url', '')}"
            current_tab.read_only_remote = True
        except (IndexError, AttributeError):
            pass
        self._location_ring = LocationRing()
        self._location_ring.record(0)
        self._refresh_title()
        size_text = format_content_length(getattr(download, "size", 0))
        self._set_status(
            f"Opened {getattr(download, 'filename', 'remote document')} "
            f"({size_text}) from {getattr(download, 'final_url', '')}"
        )
        # #187: the "Open from URL" dialog's own close-out queues a CallAfter
        # that restores focus to the *previous* tab's editor (captured before
        # this new tab existed). Queue a second, correctly-bound CallAfter so
        # it runs after that stale one and wins, landing focus on the new
        # editor -- otherwise it never receives its first SetFocus and its
        # content stays visually blank until the user manually tabs into it.
        call_after = getattr(self._wx, "CallAfter", None)
        if callable(call_after) and hasattr(self, "editor"):
            call_after(self.editor.SetFocus)

    # --- Remote Sites (issues #154, #155, #156, #157) -----------------------

    def open_from_remote(self) -> None:
        from quill.ui.remote_sites_dialog import DialogMode, RemoteSitesDialog

        with RemoteSitesDialog(
            self.frame, mode=DialogMode.OPEN, title="Open from Remote"
        ) as dialog:
            if self._show_modal_dialog(dialog, "Open from Remote") != self._wx.ID_OK:
                self._set_status("Open from Remote cancelled")
                return
            result = dialog.result
        if result is None:
            return
        self._download_remote_into_new_tab(result.site, result.path)

    def save_to_remote(self) -> None:
        from quill.ui.remote_sites_dialog import DialogMode, RemoteSitesDialog

        if self._active_tab().read_only_remote:
            # The active tab was opened from a URL; nothing to write back.
            self._show_message_box(
                "This document was opened from a URL and cannot be saved back to it. "
                "Use Save Copy to Remote... to write a local copy to a remote site.",
                "Save to Remote",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )
            return
        with RemoteSitesDialog(self.frame, mode=DialogMode.SAVE, title="Save to Remote") as dialog:
            if self._show_modal_dialog(dialog, "Save to Remote") != self._wx.ID_OK:
                self._set_status("Save to Remote cancelled")
                return
            result = dialog.result
        if result is None:
            return
        self._upload_active_document(result.site, result.path)

    def save_copy_to_remote(self) -> None:
        from quill.ui.remote_sites_dialog import DialogMode, RemoteSitesDialog

        with RemoteSitesDialog(
            self.frame, mode=DialogMode.SAVE, title="Save Copy to Remote"
        ) as dialog:
            if self._show_modal_dialog(dialog, "Save Copy to Remote") != self._wx.ID_OK:
                self._set_status("Save Copy to Remote cancelled")
                return
            result = dialog.result
        if result is None:
            return
        self._upload_active_document(result.site, result.path)

    def save_copy_remote(self) -> None:
        """Local-folder analogue of Save Copy to Remote; used by remote tabs."""

        self.save_copy_to_remote()

    def manage_remote_sites(self) -> None:
        from quill.ui.remote_sites_dialog import DialogMode, RemoteSitesDialog

        with RemoteSitesDialog(
            self.frame,
            mode=DialogMode.OPEN,
            title="Manage Remote Sites",
        ) as dialog:
            self._show_modal_dialog(dialog, "Manage Remote Sites")

    def _download_remote_into_new_tab(self, site, remote_path: str) -> None:

        self._set_status(f"Downloading {remote_path} from {site.name}...")
        local_path = self._alloc_remote_temp_path(remote_path)
        try:
            self._run_remote_download(site, remote_path, local_path)
        except Exception as exc:  # noqa: BLE001 - transport errors are surfaced
            self._show_message_box(
                f"Could not download from {site.name}: {user_facing_message(exc)}",
                "Open from Remote",
                self._wx.ICON_ERROR | self._wx.OK,
            )
            return
        suffix = Path(remote_path).suffix.lower() or Path(local_path).suffix.lower()
        self._create_document_tab(
            Document(text="", path=Path(local_path), modified=False), select=True
        )
        existing_index = len(self._document_tabs) - 1
        from quill.io.open_read import OFFICE_STREAM_SUFFIXES

        if suffix in OFFICE_STREAM_SUFFIXES:
            docx_engine = self._docx_read_engine()
            self._run_background_task(
                f"Opening {Path(remote_path).name}",
                lambda _p: read_open_document(Path(local_path), suffix, docx_engine=docx_engine),
                lambda result: self._finish_remote_download(
                    result, suffix, site, remote_path, existing_index
                ),
            )
            return
        result = read_open_document(Path(local_path), suffix)
        self._finish_remote_download(result, suffix, site, remote_path, existing_index)

    def _finish_remote_download(
        self,
        result: object,
        suffix: str,
        site,
        remote_path: str,
        existing_index: int,
    ) -> None:
        assert isinstance(result, tuple)
        loaded, epub_book = result
        if 0 <= existing_index < len(self._document_tabs):
            tab = self._document_tabs[existing_index]
            tab.document = loaded
            tab.editor.ChangeValue(loaded.text)
            tab.source_label = f"from {site.name}:{remote_path}"
            tab.read_only_remote = False
        self._epub_book = epub_book if suffix == ".epub" else None
        self._select_tab(existing_index)
        self._refresh_title()
        self._set_status(f"Downloaded {remote_path} from {site.name}")
        # #187: the "Open from Remote" dialog's own close-out queues a
        # CallAfter that restores focus to the *previous* tab's editor
        # (captured before this new tab existed). Queue a second,
        # correctly-bound CallAfter so it runs after that stale one and
        # wins, landing focus on the new editor -- otherwise it never
        # receives its first SetFocus and its content stays visually blank
        # until the user manually tabs into it.
        call_after = getattr(self._wx, "CallAfter", None)
        if callable(call_after) and hasattr(self, "editor"):
            call_after(self.editor.SetFocus)

    def _upload_active_document(self, site, remote_path: str) -> None:

        from quill.core.remote_sites import load_password

        local_path = self._alloc_remote_temp_path(remote_path)
        # Atomic, and in the document's own encoding and line endings (bad.md
        # F4). This was the one writer left that opened the target and wrote
        # straight into it as UTF-8 with Python's newline translation on, so a
        # file edited over SFTP came back re-encoded and re-lined -- and an
        # interrupted write left a truncated temp file to upload.
        from quill.core.storage import write_text_atomic
        from quill.io.text import _normalize_line_endings

        text = _normalize_line_endings(
            self.editor.GetValue(), str(getattr(self.document, "line_ending", "") or "\r\n")
        )
        encoding = str(getattr(self.document, "encoding", "") or "utf-8")
        try:
            text.encode(encoding)
        except (UnicodeEncodeError, LookupError):
            encoding = "utf-8"
        write_text_atomic(Path(local_path), text, encoding=encoding, newline="")
        password = load_password(site.id)
        try:
            self._run_remote_upload(site, local_path, remote_path, password)
        except Exception as exc:  # noqa: BLE001
            self._show_message_box(
                f"Could not save to {site.name}: {user_facing_message(exc)}",
                "Save to Remote",
                self._wx.ICON_ERROR | self._wx.OK,
            )
            return
        self._set_status(f"Saved {remote_path} to {site.name}")

    def _alloc_remote_temp_path(self, remote_path: str) -> str:
        import tempfile

        base = os.path.basename(remote_path.rstrip("/")) or "remote"
        suffix = os.path.splitext(base)[1]
        fd, path = tempfile.mkstemp(prefix="quill-remote-", suffix=suffix)
        os.close(fd)
        return path

    def _run_remote_download(self, site, remote_path: str, local_path: str) -> None:
        """Synchronous download on the calling thread.

        The dialog UI is modal and short-lived; threading is intentionally
        minimal. The transport still raises :class:`RemoteTransportError` on
        failure so the caller can present a single error message.
        """

        from quill.core.remote_sites import load_password
        from quill.io.ftp_transport import FtpTransport
        from quill.io.remote_transport import RemoteTransport
        from quill.io.s3_transport import S3Transport
        from quill.io.sftp_transport import SftpTransport
        from quill.io.webdav_transport import WebDavTransport

        password = load_password(site.id)
        protocol = site.protocol
        transport: RemoteTransport
        if protocol == "ftp":
            transport = FtpTransport(site, password=password)
        elif protocol == "sftp":
            transport = SftpTransport(site, password=password)
        elif protocol == "webdav":
            transport = WebDavTransport(site, password=password)
        elif protocol == "s3":
            transport = S3Transport(site, password=password)
        else:
            raise RuntimeError(f"Unsupported protocol: {protocol}")
        try:
            transport.download(remote_path, local_path)
        finally:
            transport.close()

    def _run_remote_upload(self, site, local_path: str, remote_path: str, password: str) -> None:
        from quill.io.ftp_transport import FtpTransport
        from quill.io.remote_transport import RemoteTransport
        from quill.io.s3_transport import S3Transport
        from quill.io.sftp_transport import SftpTransport
        from quill.io.webdav_transport import WebDavTransport

        protocol = site.protocol
        transport: RemoteTransport
        if protocol == "ftp":
            transport = FtpTransport(site, password=password)
        elif protocol == "sftp":
            transport = SftpTransport(site, password=password)
        elif protocol == "webdav":
            transport = WebDavTransport(site, password=password)
        elif protocol == "s3":
            transport = S3Transport(site, password=password)
        else:
            raise RuntimeError(f"Unsupported protocol: {protocol}")
        try:
            transport.upload(local_path, remote_path)
        finally:
            transport.close()
