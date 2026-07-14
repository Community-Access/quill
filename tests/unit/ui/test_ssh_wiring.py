"""Source-contract wiring for edit-over-SSH UI (issue #139).

wxPython is headless-unfriendly, so this pins the integration points: the mixin
is mixed in, save uploads back to the remote, and the File menu + command
palette expose Quick Connect and the Site Manager.
"""

from __future__ import annotations

from pathlib import Path


def _read(rel: str) -> str:
    return Path(rel).read_text(encoding="utf-8")


def test_main_frame_mixes_in_ssh_editing() -> None:
    source = _read("quill/ui/main_frame.py")
    assert "from quill.ui.main_frame_ssh import SshEditingMixin" in source
    assert "    SshEditingMixin,\n" in source


def test_save_uploads_back_over_ssh() -> None:
    source = _read("quill/ui/main_frame.py")
    start = source.index("def save_file")
    # Read the whole function body so we can match regardless of how the
    # earlier guards grow; the contract is that save_file triggers the
    # SSH upload helper from SshEditingMixin.
    body = source[start : source.index("\n    def ", start + 1)]
    assert "self.maybe_upload_remote_on_save()" in body


def test_commands_registered_for_palette() -> None:
    source = _read("quill/ui/main_frame.py")
    assert '"file.ssh_quick_connect"' in source
    assert '"file.ssh_site_manager"' in source


def test_file_menu_has_ssh_items_and_bindings() -> None:
    menu = _read("quill/ui/main_frame_menu.py")
    assert "Open over SS&H" in menu
    assert "self._bind_ssh_file_menu()" in menu
    ssh = _read("quill/ui/main_frame_ssh.py")
    assert "self.open_ssh_quick_connect()" in ssh
    assert "self.open_ssh_site_manager()" in ssh


def test_ssh_dialogs_are_native_and_dismissable() -> None:
    dialogs = _read("quill/ui/ssh_dialogs.py")
    # Native wx, never a WebView; every dialog can be cancelled with Escape.
    assert "html2" not in dialogs
    assert "show_web_form" not in dialogs
    assert dialogs.count("wx.ID_CANCEL") >= 4
