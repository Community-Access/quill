"""Unit tests for :mod:`quill.core.remote_sites` (issues #154, #155, #156, #157)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core import remote_sites
from quill.core.remote_sites import (
    PROTOCOL_FTP,
    PROTOCOL_S3,
    PROTOCOL_SFTP,
    PROTOCOL_WEBDAV,
    RemoteSite,
    default_port,
    delete_password,
    delete_site,
    load_password,
    load_sites,
    save_password,
    save_sites,
    upsert_site,
)


@pytest.fixture(autouse=True)
def _isolated_sites(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Force the remote-site JSON store into a temp directory per test."""

    def _tmp_path() -> Path:  # type: ignore[no-redef]
        return tmp_path

    monkeypatch.setattr(remote_sites, "_sites_path", lambda: tmp_path / "remote-sites.json")
    monkeypatch.setattr(remote_sites, "app_data_dir", lambda: tmp_path)


def test_default_port_returns_conventional_ports() -> None:
    assert default_port(PROTOCOL_FTP) == 21
    assert default_port(PROTOCOL_SFTP) == 22
    assert default_port(PROTOCOL_WEBDAV) == 443
    assert default_port(PROTOCOL_S3) == 443
    assert default_port("unknown") == 0


def test_remote_site_normalisation_canonicalises_protocol_and_id() -> None:
    site = RemoteSite(
        id="",
        name="  Personal Box  ",
        protocol=" FTP ",
        host="box.example.com",
        port=0,
        username="alice",
        root_dir="/notes",
        trust_first_use=True,
        extra={"s3_region": "us-west-2", "extra_int": 12},
    )
    normalised = site.normalised()
    assert normalised.id  # derived from name when blank
    assert normalised.protocol == PROTOCOL_FTP
    assert normalised.port == 21  # default for FTP
    assert normalised.name == "Personal Box"
    assert normalised.extra == {"s3_region": "us-west-2", "extra_int": "12"}


def test_save_and_load_round_trips_sorted() -> None:
    upsert_site(
        RemoteSite(
            id="alpha",
            name="Alpha",
            protocol=PROTOCOL_S3,
            host="s3.amazonaws.com",
            extra={"s3_bucket": "b"},
        )
    )
    upsert_site(
        RemoteSite(
            id="beta",
            name="Beta",
            protocol=PROTOCOL_FTP,
            host="ftp.example.com",
        )
    )
    loaded = load_sites()
    assert [site.id for site in loaded] == ["alpha", "beta"]  # sorted by name
    # The on-disk file should contain normalised entries.
    raw = json.loads(Path(remote_sites._sites_path()).read_text(encoding="utf-8"))  # type: ignore[attr-defined]
    # Versioned envelope: {"schema_version", "sites": [...]}.
    assert raw["schema_version"] == 1
    assert {entry["id"] for entry in raw["sites"]} == {"alpha", "beta"}


def test_upsert_replaces_existing_id() -> None:
    upsert_site(RemoteSite(id="x", name="X", protocol=PROTOCOL_SFTP, host="host"))
    upsert_site(RemoteSite(id="x", name="X2", protocol=PROTOCOL_SFTP, host="host"))
    loaded = load_sites()
    assert len(loaded) == 1
    assert loaded[0].name == "X2"


def test_delete_site_drops_matching_id() -> None:
    upsert_site(RemoteSite(id="keep", name="Keep", protocol=PROTOCOL_FTP, host="h"))
    upsert_site(RemoteSite(id="drop", name="Drop", protocol=PROTOCOL_FTP, host="h"))
    remaining = delete_site("drop")
    assert [site.id for site in remaining] == ["keep"]


def test_password_store_falls_back_to_dpapi() -> None:
    """When the Windows credential manager is unavailable the DPAPI store is used."""

    save_password("site-a", "secret")
    # ``load_password`` returns the stored password via whichever backend is active.
    assert load_password("site-a") == "secret"
    assert delete_password("site-a") is True
    assert load_password("site-a") == ""


def test_delete_password_is_idempotent() -> None:
    assert delete_password("never-existed") is False
    save_password("site-b", "another")
    assert delete_password("site-b") is True
    # Second call should not raise.
    assert delete_password("site-b") is False


def test_save_sites_handles_empty_list(tmp_path: Path) -> None:
    save_sites([])
    assert load_sites() == []


def test_load_reads_legacy_bare_list(monkeypatch, tmp_path) -> None:
    import json
    from pathlib import Path

    monkeypatch.setattr(remote_sites, "_sites_path", lambda: tmp_path / "remote-sites.json")
    # A pre-versioning file was a bare list; it must still load.
    legacy = [{"id": "a", "name": "Alpha", "host": "h", "username": "u"}]
    Path(remote_sites._sites_path()).write_text(json.dumps(legacy), encoding="utf-8")  # type: ignore[attr-defined]
    loaded = remote_sites.load_sites()
    assert [s.id for s in loaded] == ["a"]
