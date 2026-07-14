"""Tests for libmpv discovery and backend preference (no real DLL needed)."""

from __future__ import annotations

from pathlib import Path

from quill.ui.audio_studio.mpv_engine import find_libmpv, mpv_pack_dir


def test_find_libmpv_env_override_file(tmp_path: Path, monkeypatch) -> None:
    dll = tmp_path / "libmpv-2.dll"
    dll.write_bytes(b"MZ")
    monkeypatch.setenv("QUILL_LIBMPV", str(dll))
    assert find_libmpv() == dll


def test_find_libmpv_env_override_folder(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "mpv-2.dll").write_bytes(b"MZ")
    monkeypatch.setenv("QUILL_LIBMPV", str(tmp_path))
    assert find_libmpv() == tmp_path / "mpv-2.dll"


def test_find_libmpv_pack_dir(tmp_path: Path, monkeypatch) -> None:
    import quill.ui.audio_studio.mpv_engine as me

    monkeypatch.delenv("QUILL_LIBMPV", raising=False)
    pack = tmp_path / "engine-packs" / "mpv"
    pack.mkdir(parents=True)
    (pack / "libmpv-2.dll").write_bytes(b"MZ")
    monkeypatch.setattr(me, "mpv_pack_dir", lambda: pack)
    assert find_libmpv() == pack / "libmpv-2.dll"


def test_find_libmpv_absent(monkeypatch, tmp_path: Path) -> None:
    import quill.ui.audio_studio.mpv_engine as me

    monkeypatch.delenv("QUILL_LIBMPV", raising=False)
    monkeypatch.setattr(me, "mpv_pack_dir", lambda: tmp_path / "empty")
    monkeypatch.setattr(me.sys, "executable", str(tmp_path / "nowhere" / "quill.exe"))
    assert find_libmpv() is None


def test_preferred_backend_tracks_dll_presence(monkeypatch, tmp_path: Path) -> None:
    import quill.ui.audio_studio.mpv_engine as me
    from quill.ui.audio_studio.audio_engine import preferred_backend

    monkeypatch.delenv("QUILL_LIBMPV", raising=False)
    monkeypatch.setattr(me, "mpv_pack_dir", lambda: tmp_path / "empty")
    monkeypatch.setattr(me.sys, "executable", str(tmp_path / "nowhere" / "quill.exe"))
    assert preferred_backend() == "wx"
    dll = tmp_path / "libmpv-2.dll"
    dll.write_bytes(b"MZ")
    monkeypatch.setenv("QUILL_LIBMPV", str(dll))
    assert preferred_backend() == "mpv"


def test_mpv_pack_dir_under_engine_packs() -> None:
    assert mpv_pack_dir().name == "mpv"
    assert mpv_pack_dir().parent.name != ""
