"""Edit-over-SSH orchestration for ``MainFrame`` (issue #139).

Wires the SSH dialogs to the core SFTP service: connect (off the UI thread so the
screen reader stays responsive), browse, download a remote file to a local temp
copy, open it normally, and on save upload it back with a tilde backup in the
file's original newline style.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.ssh.client import SftpConnection, SshDependencyError, connect
from quill.core.ssh.sites import AUTH_PASSWORD, SiteConfig
from quill.core.ssh.transfer import editor_to_remote, remote_to_editor
from quill.ui.ssh_dialogs import (
    ConnectionRequest,
    QuickConnectDialog,
    RemoteBrowserDialog,
    SiteManagerDialog,
)


@dataclass(slots=True)
class _RemoteBinding:
    connection: SftpConnection
    remote_path: str
    newline: str


class SshEditingMixin:
    def _ssh_state(self) -> tuple[list[SftpConnection], dict[str, _RemoteBinding]]:
        if not hasattr(self, "_ssh_connections"):
            self._ssh_connections: list[SftpConnection] = []
            self._ssh_remote_files: dict[str, _RemoteBinding] = {}
        return self._ssh_connections, self._ssh_remote_files

    def _bind_ssh_file_menu(self) -> None:
        """Bind the File > Open over SSH submenu items (kept off main_frame_menu)."""
        wx = self._wx
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_ssh_quick_connect(), id=self._id_ssh_quick_connect
        )
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self.open_ssh_site_manager(), id=self._id_ssh_site_manager
        )

    # ------------------------------------------------------------- entry points
    def open_ssh_quick_connect(self) -> None:
        request = QuickConnectDialog(self.frame).show()
        if request is not None:
            self._ssh_connect_and_browse(request)

    def open_ssh_site_manager(self) -> None:
        site = SiteManagerDialog(self.frame).show()
        if site is None:
            return
        request = self._request_for_site(site)
        if request is not None:
            self._ssh_connect_and_browse(request)

    def _request_for_site(self, site: SiteConfig) -> ConnectionRequest | None:
        password = ""
        if site.auth == AUTH_PASSWORD:
            wx = self._wx
            with wx.PasswordEntryDialog(
                self.frame, f"Password for {site.username or ''}@{site.host}", "SSH Password"
            ) as dialog:
                if self._show_modal_dialog(dialog, "SSH Password") != wx.ID_OK:
                    return None
                password = dialog.GetValue()
        return ConnectionRequest(
            host=site.host,
            port=site.port,
            username=site.username,
            auth=site.auth,
            password=password,
            key_path=site.key_path,
            default_dir=site.default_dir or "/",
        )

    # ------------------------------------------------------------- connect flow
    def _ssh_connect_and_browse(self, request: ConnectionRequest) -> None:
        self._set_status(f"Connecting to {request.host}...")
        self._announce(f"Connecting to {request.host}")

        def worker() -> None:
            try:
                connection = connect(
                    request.host,
                    port=request.port,
                    username=request.username,
                    password=request.password,
                    auth=request.auth,
                    key_path=request.key_path,
                    # For key auth the password field doubles as the key passphrase
                    # (used to decrypt an encrypted OpenSSH or .ppk key).
                    key_passphrase=request.password or None,
                )
            except SshDependencyError as error:
                self._wx.CallAfter(self._ssh_error, str(error))
            except Exception as error:  # noqa: BLE001 - report any connect failure plainly
                self._wx.CallAfter(self._ssh_error, f"Could not connect to {request.host}: {error}")
            else:
                self._wx.CallAfter(self._on_ssh_connected, connection, request)

        threading.Thread(  # GATE-40-OK: SSH connect worker.
            target=worker, daemon=True
        ).start()

    def _ssh_error(self, message: str) -> None:
        self._set_status(message)
        self._announce(message)
        self._show_message_box(message, "SSH", self._wx.ICON_ERROR | self._wx.OK)

    def _on_ssh_connected(self, connection: SftpConnection, request: ConnectionRequest) -> None:
        connections, _bindings = self._ssh_state()
        connections.append(connection)
        self._set_status(f"Connected to {request.host}")
        remote_path = RemoteBrowserDialog(
            self.frame,
            list_dir=connection.service.list_dir,
            start_dir=request.default_dir,
            announce_cb=self._announce,
        ).show()
        if remote_path is None:
            connection.close()
            connections.remove(connection)
            self._set_status("SSH browse cancelled")
            return
        self._ssh_open_remote_file(connection, remote_path)

    # ------------------------------------------------------------- open / save
    def _ssh_open_remote_file(self, connection: SftpConnection, remote_path: str) -> None:
        try:
            data = connection.service.read_file(remote_path)
        except Exception as error:  # noqa: BLE001
            self._ssh_error(f"Could not read {remote_path}: {error}")
            return
        text, newline = remote_to_editor(data)
        temp_dir = app_data_dir() / "ssh-temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        local_path = temp_dir / Path(remote_path).name
        local_path.write_text(text, encoding="utf-8", newline="")
        _connections, bindings = self._ssh_state()
        bindings[str(local_path)] = _RemoteBinding(connection, remote_path, newline)
        self.open_file(local_path)
        self._set_status(f"Editing {remote_path} (saves upload back over SSH)")
        self._announce(f"Opened remote file {Path(remote_path).name}")

    def maybe_upload_remote_on_save(self) -> None:
        """After a local save, upload the file back to its remote origin (#139)."""
        path = getattr(self.document, "path", None)
        if path is None:
            return
        _connections, bindings = self._ssh_state()
        binding = bindings.get(str(path))
        if binding is None:
            return
        try:
            data = editor_to_remote(self.document.text, binding.newline)
            backup = binding.connection.service.write_file(
                binding.remote_path, data, make_backup=True
            )
        except Exception as error:  # noqa: BLE001
            self._ssh_error(f"Saved locally but could not upload to {binding.remote_path}: {error}")
            return
        if backup:
            message = f"Uploaded to {binding.remote_path} (backup {Path(backup).name})"
        else:
            message = f"Uploaded to {binding.remote_path}"
        self._set_status(message)
        self._announce(message)

    def close_ssh_connections(self) -> None:
        """Close any open SSH connections (best effort, e.g. on app shutdown)."""
        connections, bindings = self._ssh_state()
        for connection in connections:
            connection.close()
        connections.clear()
        bindings.clear()
