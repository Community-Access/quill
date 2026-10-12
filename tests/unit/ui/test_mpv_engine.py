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
    # And the repo's own build staging, which a SOURCE run is allowed to find
    # since 2026-09-29. Pointing the module's __file__ at an empty tree is
    # how "no libmpv anywhere" is still expressible from inside a checkout
    # that has one.
    monkeypatch.setattr(
        me, "__file__", str(tmp_path / "tree" / "quill" / "ui" / "audio" / "mpv_engine.py")
    )
    assert find_libmpv() is None


def test_preferred_backend_tracks_dll_presence(monkeypatch, tmp_path: Path) -> None:
    import quill.ui.audio.mpv_engine as me
    from quill.ui.audio.audio_engine import preferred_backend

    monkeypatch.delenv("QUILL_LIBMPV", raising=False)
    monkeypatch.setattr(me, "mpv_pack_dir", lambda: tmp_path / "empty")
    monkeypatch.setattr(me.sys, "executable", str(tmp_path / "nowhere" / "quill.exe"))
    # And the repo's own build staging, which a SOURCE run is allowed to find
    # since 2026-09-29. Pointing the module's __file__ at an empty tree is
    # how "no libmpv anywhere" is still expressible from inside a checkout
    # that has one.
    monkeypatch.setattr(
        me, "__file__", str(tmp_path / "tree" / "quill" / "ui" / "audio" / "mpv_engine.py")
    )
    assert preferred_backend() == "wx"
    dll = tmp_path / "libmpv-2.dll"
    dll.write_bytes(b"MZ")
    monkeypatch.setenv("QUILL_LIBMPV", str(dll))
    assert preferred_backend() == "mpv"


def test_mpv_pack_dir_under_engine_packs() -> None:
    assert mpv_pack_dir().name == "mpv"
    assert mpv_pack_dir().parent.name != ""


def test_destroying_a_child_does_not_close_the_parent_audio_engine() -> None:
    from types import SimpleNamespace

    from quill.ui.audio.mpv_engine import MpvAudioEngine

    parent = object()
    calls: list[str] = []
    engine = SimpleNamespace(_parent=parent, _parent_id=42, terminate=lambda: calls.append("close"))
    child_event = SimpleNamespace(
        GetId=lambda: 43, GetWindow=lambda: object(), Skip=lambda: calls.append("skip")
    )
    MpvAudioEngine._on_parent_destroyed(engine, child_event)
    assert calls == ["skip"]
    parent_event = SimpleNamespace(
        GetId=lambda: 42, GetWindow=lambda: object(), Skip=lambda: calls.append("skip")
    )
    MpvAudioEngine._on_parent_destroyed(engine, parent_event)
    assert calls == ["skip", "skip", "close"]


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
    for option in (
        "load-scripts",
        "load-stats-overlay",
        "load-console",
        "load-auto-profiles",
        "load-select",
        "load-positioning",
        "load-commands",
        "load-context-menu",
    ):
        assert f"{option}=no" in order
        assert order.index(f"{option}=no") < order.index("init")
    assert order.index("config=no") < order.index("init")


def test_radio_parent_destruction_matches_native_id_not_python_wrapper() -> None:
    from types import SimpleNamespace

    from quill.ui.radio.mpv_radio_engine import MpvRadioEngine

    calls: list[str] = []
    engine = SimpleNamespace(
        _parent=object(), _parent_id=42, terminate=lambda: calls.append("terminate")
    )
    for identifier in (43, 42):
        event = SimpleNamespace(
            GetId=lambda identifier=identifier: identifier, Skip=lambda: calls.append("skip")
        )
        MpvRadioEngine._on_parent_destroyed(engine, event)
    assert calls == ["skip", "skip", "terminate"]


def test_find_libmpv_beside_the_runtime_without_app_root(monkeypatch, tmp_path: Path) -> None:
    # Started straight through QuillVilleRuntime.exe (a taskbar pin), no
    # launcher exported QUILL_APP_ROOT; the runtime's own tools\mpv still counts.
    import quill.ui.audio.mpv_engine as me

    monkeypatch.delenv("QUILL_LIBMPV", raising=False)
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    monkeypatch.setattr(me, "mpv_pack_dir", lambda: tmp_path / "empty")
    runtime = tmp_path / "Runtime" / "3.13"
    (runtime / "tools" / "mpv").mkdir(parents=True)
    (runtime / "tools" / "mpv" / "libmpv-2.dll").write_bytes(b"MZ")
    monkeypatch.setattr(me.sys, "executable", str(runtime / "QuillVilleRuntime.exe"))
    assert find_libmpv() == runtime / "tools" / "mpv" / "libmpv-2.dll"
