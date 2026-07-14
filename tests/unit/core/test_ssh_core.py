"""Core edit-over-SSH logic (issue #139): newline transfer, sites, SFTP service.

These cover the pure/injectable pieces and need no network or paramiko.
"""

from __future__ import annotations

import io

import pytest

from quill.core.ssh import sites as sites_mod
from quill.core.ssh.client import RemoteEntry, SftpFileService
from quill.core.ssh.sites import SiteConfig
from quill.core.ssh.transfer import (
    backup_name,
    detect_newline,
    editor_to_remote,
    remote_to_editor,
)

# --- transfer: newline translation round-trips --------------------------------


def test_detect_newline_prefers_crlf_over_cr() -> None:
    assert detect_newline(b"a\r\nb") == "crlf"
    assert detect_newline(b"a\rb") == "cr"
    assert detect_newline(b"a\nb") == "lf"
    assert detect_newline(b"no newline") == "lf"


def test_lf_file_round_trips_without_rewriting_line_endings() -> None:
    # A Linux config file (LF) edited and saved back stays LF, not CRLF.
    text, newline = remote_to_editor(b"line1\nline2\n")
    assert newline == "lf"
    assert text == "line1\nline2\n"
    assert editor_to_remote(text, newline) == b"line1\nline2\n"


def test_crlf_file_is_restored_on_save() -> None:
    text, newline = remote_to_editor(b"line1\r\nline2\r\n")
    assert newline == "crlf"
    assert text == "line1\nline2\n"  # editor sees normalised LF
    assert editor_to_remote(text, newline) == b"line1\r\nline2\r\n"


def test_editor_crlf_input_does_not_double_up_for_lf_target() -> None:
    # Editor buffer arrives with CRLF but the remote file is LF: write LF only.
    assert editor_to_remote("a\r\nb", "lf") == b"a\nb"


def test_non_utf8_bytes_round_trip_losslessly() -> None:
    raw = b"caf\xe9\n"  # latin-1 e-acute, not valid UTF-8
    text, newline = remote_to_editor(raw)
    assert editor_to_remote(text, newline) == raw


def test_backup_name_adds_tilde() -> None:
    assert backup_name("/etc/test.txt") == "/etc/test.txt~"


# --- sites: persistence, no plaintext passwords -------------------------------


@pytest.fixture
def temp_app_data(tmp_path, monkeypatch):
    monkeypatch.setattr(sites_mod, "app_data_dir", lambda: tmp_path)
    return tmp_path


def test_sites_round_trip_and_sorted(temp_app_data) -> None:
    sites_mod.upsert_site(SiteConfig(name="Zeta", host="z.example", username="root"))
    sites_mod.upsert_site(SiteConfig(name="alpha", host="a.example", port=2222))
    loaded = sites_mod.load_sites()
    assert [site.name for site in loaded] == ["alpha", "Zeta"]
    assert loaded[0].port == 2222


def test_upsert_replaces_same_name_case_insensitively(temp_app_data) -> None:
    sites_mod.upsert_site(SiteConfig(name="Box", host="old.example"))
    sites_mod.upsert_site(SiteConfig(name="box", host="new.example"))
    loaded = sites_mod.load_sites()
    assert len(loaded) == 1
    assert loaded[0].host == "new.example"


def test_delete_site(temp_app_data) -> None:
    sites_mod.upsert_site(SiteConfig(name="Keep", host="k.example"))
    sites_mod.upsert_site(SiteConfig(name="Drop", host="d.example"))
    sites_mod.delete_site("Drop")
    assert [site.name for site in sites_mod.load_sites()] == ["Keep"]


def test_persisted_site_never_contains_a_password(temp_app_data) -> None:
    import json

    sites_mod.upsert_site(SiteConfig(name="Server", host="s.example", username="admin"))
    stored = json.loads((temp_app_data / "ssh_sites.json").read_text(encoding="utf-8"))
    # Versioned envelope: {"schema_version", "sites": [...]}.
    assert stored["schema_version"] == 1
    records = stored["sites"]
    # The site stores the auth *method* ("password") but no secret value: there is
    # no "password" key holding a credential.
    assert all("password" not in record for record in records)
    assert records[0]["auth"] == "password"


def test_normalised_fixes_bad_port_and_auth() -> None:
    site = SiteConfig(name="x", host="h", port=0, auth="bogus").normalised()
    assert site.port == 22
    assert site.auth == "password"


# --- SFTP service: browse + write-with-backup via a fake sftp -----------------


class _FakeAttr:
    def __init__(self, filename: str, mode: int, size: int = 0, mtime: float = 0.0) -> None:
        self.filename = filename
        self.st_mode = mode
        self.st_size = size
        self.st_mtime = mtime


class _FakeSftp:
    """Minimal in-memory SFTP stand-in for SftpFileService."""

    DIR_MODE = 0o040000
    FILE_MODE = 0o100000

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.dirs: dict[str, list[_FakeAttr]] = {}

    def listdir_attr(self, path: str) -> list[_FakeAttr]:
        return self.dirs[path]

    def stat(self, path: str):
        if path not in self.files:
            raise OSError("no such file")
        return _FakeAttr(path, self.FILE_MODE, len(self.files[path]))

    def open(self, path: str, mode: str):
        sftp = self

        class _Handle(io.BytesIO):
            def __enter__(self_inner):
                if "r" in mode:
                    self_inner.write(sftp.files[path])
                    self_inner.seek(0)
                return self_inner

            def __exit__(self_inner, *_exc):
                if "w" in mode:
                    sftp.files[path] = self_inner.getvalue()
                return False

        return _Handle()

    def posix_rename(self, src: str, dst: str) -> None:
        self.files[dst] = self.files.pop(src)


def test_list_dir_sorts_directories_first() -> None:
    sftp = _FakeSftp()
    sftp.dirs["/srv"] = [
        _FakeAttr("readme.txt", _FakeSftp.FILE_MODE, 10),
        _FakeAttr("zzz", _FakeSftp.DIR_MODE),
        _FakeAttr("Apps", _FakeSftp.DIR_MODE),
    ]
    names = [(entry.name, entry.is_dir) for entry in SftpFileService(sftp).list_dir("/srv")]
    assert names == [("Apps", True), ("zzz", True), ("readme.txt", False)]


def test_write_file_backs_up_existing_then_writes_new() -> None:
    sftp = _FakeSftp()
    sftp.files["/etc/app.conf"] = b"old\n"
    service = SftpFileService(sftp)
    backup = service.write_file("/etc/app.conf", b"new\n")
    assert backup == "/etc/app.conf~"
    assert sftp.files["/etc/app.conf~"] == b"old\n"
    assert sftp.files["/etc/app.conf"] == b"new\n"


def test_write_new_file_makes_no_backup() -> None:
    sftp = _FakeSftp()
    service = SftpFileService(sftp)
    backup = service.write_file("/etc/brand_new.conf", b"hi\n")
    assert backup is None
    assert sftp.files["/etc/brand_new.conf"] == b"hi\n"


def test_read_file_returns_bytes() -> None:
    sftp = _FakeSftp()
    sftp.files["/x"] = b"payload"
    assert SftpFileService(sftp).read_file("/x") == b"payload"


def test_remote_entry_is_a_simple_record() -> None:
    entry = RemoteEntry(name="a", is_dir=False, size=1, mtime=2.0)
    assert (entry.name, entry.is_dir, entry.size, entry.mtime) == ("a", False, 1, 2.0)
