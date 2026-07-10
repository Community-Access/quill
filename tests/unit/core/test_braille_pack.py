"""#243 (BR-020): optional braille pack detection and on-demand install."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import quill.core.braille_pack as pack


def _no_managed_dir(monkeypatch, tmp_path: Path) -> None:
    """Point the managed braille dir at an empty temp dir for a clean env."""
    monkeypatch.setattr(pack, "managed_braille_dir", lambda: tmp_path / "braille-pack")


def test_not_installed_in_default_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pack.shutil, "which", lambda _name: None)
    monkeypatch.setattr(pack.importlib.util, "find_spec", lambda _name: None)
    _no_managed_dir(monkeypatch, tmp_path)
    for name in ("louis", "lou_translate"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    assert pack.is_braille_pack_installed() is False
    assert pack.braille_pack_version() is None


def test_installed_from_managed_download(monkeypatch, tmp_path: Path) -> None:
    # A downloaded pack (managed dir with lou_translate.exe) is detected, and
    # BRF profiles resolve from it -- the footprint-unbundle resolution.
    monkeypatch.setattr(pack.shutil, "which", lambda _name: None)
    monkeypatch.setattr(pack.importlib.util, "find_spec", lambda _name: None)
    managed = tmp_path / "braille-pack"
    managed.mkdir()
    (managed / "lou_translate.exe").write_bytes(b"x")
    (managed / "brf_profiles.json").write_text('{"profiles": [{"id": "p1"}]}', encoding="utf-8")
    monkeypatch.setattr(pack, "managed_braille_dir", lambda: managed)
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    assert pack.is_braille_pack_installed() is True
    assert pack.get_brf_profiles() == [{"id": "p1"}]


def test_braille_install_supported_only_on_windows(monkeypatch) -> None:
    """#47: the managed pack download ships the Windows lou_translate.exe binary,
    so the download is gated Windows-only; macOS uses Homebrew liblouis instead."""
    monkeypatch.setattr(pack.sys, "platform", "win32")
    assert pack.braille_install_supported() is True
    monkeypatch.setattr(pack.sys, "platform", "darwin")
    assert pack.braille_install_supported() is False


def test_version_reads_liblouis_version_from_manifest(monkeypatch, tmp_path: Path) -> None:
    # braille_pack.py never imports liblouis in-process (BR-020); the version
    # comes from the pack's own manifest.json (baked in at build time by
    # build_braille_pack.py), the same file get_brf_profiles() already reads
    # brf_profiles.json alongside.
    monkeypatch.setattr(pack.shutil, "which", lambda _name: None)
    monkeypatch.setattr(pack.importlib.util, "find_spec", lambda _name: None)
    managed = tmp_path / "braille-pack"
    managed.mkdir()
    (managed / "lou_translate.exe").write_bytes(b"x")
    (managed / "manifest.json").write_text(
        '{"version": 1, "liblouis_version": "3.30.0"}', encoding="utf-8"
    )
    monkeypatch.setattr(pack, "managed_braille_dir", lambda: managed)
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    assert pack.braille_pack_version() == "3.30.0"


def test_version_is_unknown_when_manifest_missing_the_field(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pack.shutil, "which", lambda _name: None)
    monkeypatch.setattr(pack.importlib.util, "find_spec", lambda _name: None)
    managed = tmp_path / "braille-pack"
    managed.mkdir()
    (managed / "lou_translate.exe").write_bytes(b"x")
    (managed / "manifest.json").write_text('{"version": 1}', encoding="utf-8")
    monkeypatch.setattr(pack, "managed_braille_dir", lambda: managed)
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    assert pack.braille_pack_version() == "unknown"


def test_install_downloads_via_release_assets(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def _fake_fetch(component, target_dir, *, progress=None, should_cancel=None, label=""):
        captured["component"] = component
        captured["target"] = target_dir
        return target_dir

    monkeypatch.setattr("quill.core.release_assets.fetch_component", _fake_fetch)
    monkeypatch.setattr(pack, "managed_braille_dir", lambda: tmp_path / "braille-pack")
    result = pack.install_braille_pack()
    assert captured["component"] == "braille"
    assert result == tmp_path / "braille-pack"


def test_installed_when_module_present(monkeypatch) -> None:
    monkeypatch.setattr(pack.shutil, "which", lambda _name: None)
    monkeypatch.setitem(sys.modules, "lou_translate", types.ModuleType("lou_translate"))
    assert pack.is_braille_pack_installed() is True


def test_installed_when_cli_on_path(monkeypatch) -> None:
    monkeypatch.setattr(
        pack.shutil,
        "which",
        lambda name: "/usr/bin/lou_translate" if name == "lou_translate" else None,
    )
    assert pack.is_braille_pack_installed() is True


def test_release_asset_pinned_and_registered() -> None:
    # The braille pack must be a real, pinned assets-v1 entry (no moving ref).
    from quill.core.release_assets import ASSETS, is_pinned

    asset = ASSETS["braille"]
    assert asset.tag == "assets-v1"
    assert asset.filename == "braille-pack.zip"
    assert asset.expect_member == "lou_translate.exe"
    assert is_pinned(asset)


def test_ui_wiring_present() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    speech = (root / "quill" / "ui" / "main_frame_speech.py").read_text(encoding="utf-8")
    assert "def download_braille_pack" in speech
    # The hub dispatches braille to the download handler, passing the reopen-hub
    # callback so the user lands back in the hub afterwards (stay-in-hub).
    assert '"braille": lambda: self.download_braille_pack(on_done=_back)' in speech
    braille = (root / "quill" / "ui" / "main_frame_braille.py").read_text(encoding="utf-8")
    # When the pack is absent, the Braille menu offers the on-demand download.
    assert "download_braille_pack" in braille
    assert "Download Braille" in braille
    # Braille appears in the unified Download Optional Components list.
    oc = (root / "quill" / "core" / "optional_components.py").read_text(encoding="utf-8")
    assert '"braille"' in oc
