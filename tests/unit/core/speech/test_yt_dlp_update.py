"""The pip-free YouTube-support repair (no network: fetch/download are fakes)."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from quill.core.speech import yt_dlp_update as up

_HOST = "https://files.pythonhosted.org/packages/aa/bb/"


def _wheel_bytes(tmp_path: Path, module: str, dist: str, version: str) -> Path:
    path = tmp_path / f"{dist.replace('-', '_')}-{version}-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(f"{module}/__init__.py", f"VERSION = {version!r}\n")
        zf.writestr(f"{module}/version.py", f"__version__ = {version!r}\n")
        zf.writestr(f"{dist.replace('-', '_')}-{version}.dist-info/METADATA", "Name: x\n")
        zf.writestr(f"{dist.replace('-', '_')}-{version}.data/data/share/man/x.1", "man")
    return path


def _document(wheel: Path, version: str, requires: list[str] | None = None) -> bytes:
    return json.dumps({
        "info": {"version": version, "requires_dist": requires or []},
        "urls": [
            {"packagetype": "sdist", "filename": "x.tar.gz", "url": _HOST + "x.tar.gz"},
            {
                "packagetype": "bdist_wheel",
                "filename": wheel.name,
                "url": _HOST + wheel.name,
                "digests": {"sha256": hashlib.sha256(wheel.read_bytes()).hexdigest()},
            },
        ],
    }).encode()


class _Net:
    """Fake PyPI: JSON by URL, wheels copied (hash-checked like the real path)."""

    def __init__(self) -> None:
        self.json: dict[str, bytes] = {}
        self.files: dict[str, Path] = {}
        self.downloads: list[str] = []

    def fetch(self, url: str) -> bytes:
        return self.json[url]

    def download(self, url: str, dest: Path, sha256: str) -> None:
        self.downloads.append(url)
        data = self.files[url].read_bytes()
        assert hashlib.sha256(data).hexdigest() == sha256
        dest.write_bytes(data)


def _serve(net: _Net, tmp_path: Path, module: str, dist: str, version: str, requires=None):
    wheel = _wheel_bytes(tmp_path, module, dist, version)
    doc = _document(wheel, version, requires)
    net.files[_HOST + wheel.name] = wheel
    return doc


def test_version_tuple_orders_dates_and_build_numbers() -> None:
    assert up.version_tuple("2026.08.19") == (2026, 8, 19)
    assert up.version_tuple("2026.9.16.232951.dev0") == (2026, 9, 16, 232951)
    assert up.version_tuple("2026.9.16.232951") > up.version_tuple("2026.09.16")
    assert up.version_tuple("garbage") == ()


def test_pick_wheel_refuses_an_unexpected_host(tmp_path: Path) -> None:
    wheel = _wheel_bytes(tmp_path, "yt_dlp", "yt-dlp", "2026.9.1")
    doc = json.loads(_document(wheel, "2026.9.1"))
    doc["urls"][1]["url"] = "https://evil.example/x.whl"
    with pytest.raises(up.YtDlpRepairError, match="unexpected address"):
        up.pick_wheel(doc)


def test_pick_wheel_requires_a_published_sha256(tmp_path: Path) -> None:
    wheel = _wheel_bytes(tmp_path, "yt_dlp", "yt-dlp", "2026.9.1")
    doc = json.loads(_document(wheel, "2026.9.1"))
    doc["urls"][1]["digests"] = {}
    with pytest.raises(up.YtDlpRepairError, match="SHA-256"):
        up.pick_wheel(doc)


def test_ejs_pin_reads_the_pin_extra() -> None:
    requires = ['yt-dlp-ejs==0.8.0; extra == "default"', 'yt-dlp-ejs==0.9.1; extra == "pin"']
    assert up.ejs_pin(requires) == "0.9.1"
    assert up.ejs_pin(["requests"]) == ""


def test_repair_installs_only_the_package_and_dist_info(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(up, "bundled_version", lambda *_a, **_k: "2026.08.19")
    net = _Net()
    net.json["https://pypi.org/pypi/yt-dlp/json"] = _serve(
        net, tmp_path, "yt_dlp", "yt-dlp", "2026.9.20"
    )
    dest = tmp_path / "pack"
    assert up.repair(dest, floor="2026.8.19", fetch=net.fetch, download=net.download) == (
        "2026.9.20"
    )
    assert (dest / "yt_dlp" / "version.py").is_file()
    assert (dest / "yt_dlp-2026.9.20.dist-info").is_dir()
    assert not list(dest.glob("*.data"))
    assert up.pack_version(dest) == "2026.9.20"
    assert up.pack_is_newer_than_bundled(dest)


def test_repair_says_already_current_and_changes_nothing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(up, "bundled_version", lambda *_a, **_k: "2026.08.19")
    net = _Net()
    net.json["https://pypi.org/pypi/yt-dlp/json"] = _serve(
        net, tmp_path, "yt_dlp", "yt-dlp", "2026.8.19"
    )
    dest = tmp_path / "pack"
    with pytest.raises(up.YtDlpAlreadyCurrent, match="2026.08.19"):
        up.repair(dest, floor="2026.8.19", fetch=net.fetch, download=net.download)
    assert net.downloads == []
    assert not dest.exists()


def test_repair_refuses_a_release_older_than_the_floor(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(up, "bundled_version", lambda *_a, **_k: "")
    net = _Net()
    net.json["https://pypi.org/pypi/yt-dlp/json"] = _serve(
        net, tmp_path, "yt_dlp", "yt-dlp", "2026.7.4"
    )
    with pytest.raises(up.YtDlpRepairError, match="older"):
        up.repair(tmp_path / "pack", floor="2026.8.19", fetch=net.fetch, download=net.download)


def test_repair_fetches_the_matching_solver_when_the_pin_moves(tmp_path: Path, monkeypatch) -> None:
    versions = {"yt-dlp": "2026.08.19", "yt-dlp-ejs": "0.8.0"}
    monkeypatch.setattr(up, "bundled_version", lambda _p, dist="yt-dlp", *_a: versions[dist])
    net = _Net()
    net.json["https://pypi.org/pypi/yt-dlp/json"] = _serve(
        net, tmp_path, "yt_dlp", "yt-dlp", "2026.10.1", ['yt-dlp-ejs==0.9.0; extra == "pin"']
    )
    net.json["https://pypi.org/pypi/yt-dlp-ejs/0.9.0/json"] = _serve(
        net, tmp_path, "yt_dlp_ejs", "yt-dlp-ejs", "0.9.0"
    )
    dest = tmp_path / "pack"
    up.repair(dest, floor="2026.8.19", fetch=net.fetch, download=net.download)
    assert (dest / "yt_dlp_ejs" / "__init__.py").is_file()
    assert up.pack_version(dest, "yt-dlp-ejs") == "0.9.0"


def test_repair_drops_a_stale_solver_when_the_bundled_one_matches(
    tmp_path: Path, monkeypatch
) -> None:
    versions = {"yt-dlp": "2026.08.19", "yt-dlp-ejs": "0.8.0"}
    monkeypatch.setattr(up, "bundled_version", lambda _p, dist="yt-dlp", *_a: versions[dist])
    dest = tmp_path / "pack"
    (dest / "yt_dlp_ejs").mkdir(parents=True)
    (dest / "yt_dlp_ejs-0.7.0.dist-info").mkdir()
    net = _Net()
    net.json["https://pypi.org/pypi/yt-dlp/json"] = _serve(
        net, tmp_path, "yt_dlp", "yt-dlp", "2026.10.1", ['yt-dlp-ejs==0.8.0; extra == "pin"']
    )
    up.repair(dest, floor="2026.8.19", fetch=net.fetch, download=net.download)
    assert not (dest / "yt_dlp_ejs").exists()
    assert not list(dest.glob("yt_dlp_ejs-*"))


def test_an_unsafe_wheel_path_is_refused(tmp_path: Path) -> None:
    wheel = tmp_path / "bad.whl"
    with zipfile.ZipFile(wheel, "w") as zf:
        zf.writestr("yt_dlp/__init__.py", "")
        zf.writestr("yt_dlp/../../escape.py", "")
    with pytest.raises(up.YtDlpRepairError, match="unsafe"):
        up._install_wheel(wheel, tmp_path / "pack", "yt_dlp", "yt-dlp")
    assert not (tmp_path / "escape.py").exists()


def test_bundled_version_ignores_the_pack(tmp_path: Path, monkeypatch) -> None:
    """The pack's own dist-info must never be mistaken for the bundled copy."""
    import sys

    pack = tmp_path / "pack"
    (pack / "yt_dlp-2999.1.1.dist-info").mkdir(parents=True)
    (pack / "yt_dlp-2999.1.1.dist-info" / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: yt-dlp\nVersion: 2999.1.1\n", encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(pack))
    assert str(pack) in sys.path
    assert up.bundled_version(pack) != "2999.1.1"
