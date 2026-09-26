"""Tests for libmpv discovery and backend preference (no real DLL needed)."""

from __future__ import annotations

from pathlib import Path

from quill.ui.audio.mpv_engine import find_libmpv, mpv_pack_dir


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
    import quill.ui.audio.mpv_engine as me

    monkeypatch.delenv("QUILL_LIBMPV", raising=False)
    pack = tmp_path / "engine-packs" / "mpv"
    pack.mkdir(parents=True)
    (pack / "libmpv-2.dll").write_bytes(b"MZ")
    monkeypatch.setattr(me, "mpv_pack_dir", lambda: pack)
    assert find_libmpv() == pack / "libmpv-2.dll"


def test_find_libmpv_absent(monkeypatch, tmp_path: Path) -> None:
    import quill.ui.audio.mpv_engine as me

    monkeypatch.delenv("QUILL_LIBMPV", raising=False)
    monkeypatch.setattr(me, "mpv_pack_dir", lambda: tmp_path / "empty")
    monkeypatch.setattr(me.sys, "executable", str(tmp_path / "nowhere" / "quill.exe"))
    assert find_libmpv() is None


def test_preferred_backend_tracks_dll_presence(monkeypatch, tmp_path: Path) -> None:
    import quill.ui.audio.mpv_engine as me
    from quill.ui.audio.audio_engine import preferred_backend

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


def test_the_client_reads_no_mpv_conf_and_never_runs_a_host_yt_dlp(monkeypatch) -> None:
    """Set before mpv_initialize, where "config" only takes effect: no mpv.conf
    from the user's profile, and no ytdl hook shelling out to a yt-dlp.exe on
    the host's PATH (which would write ~/.cache/yt-dlp from a portable copy)."""
    from unittest import mock

    import quill.ui.audio.mpv_engine as me

    lib = mock.MagicMock()
    lib.mpv_create.return_value = 1
    lib.mpv_initialize.return_value = 0
    order: list[str] = []

    def _option(_handle: object, key: bytes, value: bytes) -> int:
        order.append(f"{key.decode()}={value.decode()}")
        return 0

    lib.mpv_set_option_string.side_effect = _option
    lib.mpv_initialize.side_effect = lambda _h: order.append("init") or 0
    monkeypatch.setattr(me.ctypes, "CDLL", lambda _path: lib)

    me._MpvClient(Path("libmpv-2.dll"))

    assert "config=no" in order and "ytdl=no" in order
    assert order.index("config=no") < order.index("init")
