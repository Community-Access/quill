"""Tests for the on-demand Faster Whisper engine installer (#669 follow-up)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from quill.core.speech import engine_install as ei


class _FakeResult:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture(autouse=True)
def _restore_sys_path():
    before = list(sys.path)
    yield
    sys.path[:] = before


def _make_runner(captured: dict, result: _FakeResult | None = None):
    def runner(command, *, timeout_seconds):
        captured["command"] = list(command)
        captured["timeout"] = timeout_seconds
        return result if result is not None else _FakeResult()

    return runner


def test_install_builds_wheel_only_target_command(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ei, "is_faster_whisper_available", lambda: True)
    captured: dict = {}
    dest = tmp_path / "fw"
    out = ei.install_faster_whisper(
        dest_dir=dest,
        requirements=("faster-whisper>=1.0",),
        python_executable="py.exe",
        runner=_make_runner(captured),
    )
    cmd = captured["command"]
    assert out == dest and dest.is_dir()
    assert cmd[0] == "py.exe"
    assert cmd[1:4] == ["-m", "pip", "install"]
    assert "--only-binary=:all:" in cmd
    assert "--target" in cmd and cmd[cmd.index("--target") + 1] == str(dest)
    assert "faster-whisper>=1.0" in cmd
    assert str(dest) in sys.path  # activated on success


def test_install_blocked_in_safe_mode(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(ei.EngineInstallError, match="Safe Mode"):
        ei.install_faster_whisper(dest_dir=tmp_path / "fw", runner=_make_runner({}))


def test_install_unsupported_runtime_raises(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ei, "faster_whisper_install_supported", lambda: False)
    with pytest.raises(ei.EngineInstallError, match="pip is"):
        ei.install_faster_whisper(dest_dir=tmp_path / "fw", runner=_make_runner({}))


def test_install_nonzero_exit_surfaces_pip_output(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ei, "is_faster_whisper_available", lambda: True)
    runner = _make_runner({}, _FakeResult(returncode=1, stderr="No matching distribution"))
    with pytest.raises(ei.EngineInstallError, match="No matching distribution"):
        ei.install_faster_whisper(dest_dir=tmp_path / "fw", runner=runner)


def test_install_succeeds_but_not_importable_raises(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ei, "is_faster_whisper_available", lambda: False)
    with pytest.raises(ei.EngineInstallError, match="could not be imported"):
        ei.install_faster_whisper(dest_dir=tmp_path / "fw", runner=_make_runner({}))


def test_install_wraps_runner_exception(monkeypatch, tmp_path: Path) -> None:
    def boom(command, *, timeout_seconds):
        raise OSError("launch failed")

    with pytest.raises(ei.EngineInstallError, match="Could not run the installer"):
        ei.install_faster_whisper(dest_dir=tmp_path / "fw", runner=boom)


def test_install_vosk_falls_back_to_pypi_when_not_self_hosted(monkeypatch, tmp_path: Path) -> None:
    """With no uploaded assets-v1 wheel, Vosk installs from PyPI (no --no-index)."""
    monkeypatch.setattr(ei, "is_vosk_available", lambda: True)
    monkeypatch.setattr(ei, "_maybe_fetch_vosk_wheel", lambda progress: None)
    captured: dict = {}
    ei.install_vosk(
        dest_dir=tmp_path / "vosk", python_executable="py.exe", runner=_make_runner(captured)
    )
    cmd = captured["command"]
    assert "vosk>=0.3.45" in cmd
    assert "--no-index" not in cmd  # PyPI path may reach the index


def test_install_vosk_uses_self_hosted_wheel_when_pinned(monkeypatch, tmp_path: Path) -> None:
    """When a verified assets-v1 wheel is available, vosk is pinned to that file.

    The index stays enabled (no --no-index): vosk depends on ``cffi`` at install
    time, and --no-index + --target leaves pip with no source for cffi, failing
    with "No matching distribution found for cffi". Passing the wheel file path as
    the requirement still pins vosk itself to the verified wheel.
    """
    monkeypatch.setattr(ei, "is_vosk_available", lambda: True)
    wheel = tmp_path / "vosk-0.3.45-py3-none-win_amd64.whl"
    wheel.write_text("fake wheel", encoding="utf-8")
    monkeypatch.setattr(ei, "_maybe_fetch_vosk_wheel", lambda progress: wheel)
    captured: dict = {}
    ei.install_vosk(
        dest_dir=tmp_path / "vosk", python_executable="py.exe", runner=_make_runner(captured)
    )
    cmd = captured["command"]
    assert str(wheel) in cmd  # pinned to our verified wheel
    assert "--no-index" not in cmd  # but deps (cffi) must be resolvable
    assert "vosk>=0.3.45" not in cmd


def test_maybe_fetch_vosk_wheel_returns_none_off_windows(monkeypatch) -> None:
    monkeypatch.setattr(ei.sys, "platform", "darwin")
    assert ei._maybe_fetch_vosk_wheel(None) is None


def test_vosk_asset_is_pinned_so_self_hosting_is_live() -> None:
    """The Vosk wheel is uploaded to assets-v1, so the asset is pinned and self-hosted."""
    from quill.core import release_assets

    assert release_assets.is_pinned(release_assets.ASSETS["vosk"]) is True


def test_maybe_fetch_vosk_wheel_fetches_when_pinned_on_windows(monkeypatch, tmp_path) -> None:
    """On Windows with a pinned asset, the wheel is fetched from assets-v1."""
    monkeypatch.setattr(ei.sys, "platform", "win32")
    from quill.core import release_assets

    wheel = tmp_path / "vosk-0.3.45-py3-none-win_amd64.whl"
    wheel.write_text("x", encoding="utf-8")
    calls: dict = {}

    def fake_fetch_file(component, dest_dir, **kwargs):
        calls["component"] = component
        return wheel

    monkeypatch.setattr(release_assets, "fetch_file", fake_fetch_file)
    assert ei._maybe_fetch_vosk_wheel(None) == wheel
    assert calls["component"] == "vosk"


def test_maybe_fetch_vosk_wheel_falls_back_when_unpinned(monkeypatch) -> None:
    """If the asset were unpinned (e.g. cleared), we fall back to PyPI (None)."""
    monkeypatch.setattr(ei.sys, "platform", "win32")
    from quill.core import release_assets

    monkeypatch.setitem(
        release_assets.ASSETS,
        "vosk",
        release_assets.ReleaseAsset("vosk", "assets-v1", "vosk.whl", ""),
    )
    assert ei._maybe_fetch_vosk_wheel(None) is None


def test_maybe_fetch_vosk_wheel_degrades_to_none_on_fetch_error(monkeypatch) -> None:
    """A download/verify failure never breaks the install — it falls back to PyPI."""
    monkeypatch.setattr(ei.sys, "platform", "win32")
    from quill.core import release_assets

    def boom(component, dest_dir, **kwargs):
        raise release_assets.ReleaseAssetError("network down")

    monkeypatch.setattr(release_assets, "fetch_file", boom)
    assert ei._maybe_fetch_vosk_wheel(None) is None


def test_activate_engine_packs_adds_nonempty_dir(monkeypatch, tmp_path: Path) -> None:
    pack = tmp_path / "fw"
    pack.mkdir()
    (pack / "marker.txt").write_text("x", encoding="utf-8")
    monkeypatch.setattr(ei, "faster_whisper_pack_dir", lambda: pack)
    ei.activate_engine_packs()
    assert str(pack) in sys.path
    # Idempotent: a second call does not duplicate the entry.
    ei.activate_engine_packs()
    assert sys.path.count(str(pack)) == 1


def test_activate_engine_packs_skips_missing_or_empty(monkeypatch, tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(ei, "faster_whisper_pack_dir", lambda: empty)
    ei.activate_engine_packs()
    assert str(empty) not in sys.path
    missing = tmp_path / "missing"
    monkeypatch.setattr(ei, "faster_whisper_pack_dir", lambda: missing)
    ei.activate_engine_packs()
    assert str(missing) not in sys.path


def test_kokoro_install_logs_pip_failure(tmp_path: Path, caplog) -> None:
    """A failed pip exit is logged with the stderr tail, so Help > Save
    Diagnostics captures the real cause instead of only a transient status-bar
    line (the gap behind Richard's "Kokoro download does nothing" report)."""
    runner = _make_runner(
        {}, _FakeResult(returncode=1, stderr="No matching distribution found for kokoro-onnx")
    )
    with caplog.at_level("ERROR", logger="quill.core.speech.engine_install"):
        with pytest.raises(ei.EngineInstallError):
            ei.install_kokoro_onnx(
                dest_dir=tmp_path / "kok", python_executable="py.exe", runner=runner
            )
    assert any(
        "Kokoro ONNX install failed" in r.getMessage()
        and "No matching distribution" in r.getMessage()
        for r in caplog.records
    )


def test_kokoro_install_logs_runner_launch_failure(tmp_path: Path, caplog) -> None:
    """When pip cannot even be launched, the traceback is logged too."""

    def boom(command, *, timeout_seconds):
        raise OSError("launch failed")

    with caplog.at_level("ERROR", logger="quill.core.speech.engine_install"):
        with pytest.raises(ei.EngineInstallError, match="Could not run the installer"):
            ei.install_kokoro_onnx(
                dest_dir=tmp_path / "kok", python_executable="py.exe", runner=boom
            )
    assert any("pip runner could not start" in r.getMessage() for r in caplog.records)


def test_kokoro_install_uses_bundled_wheelhouse_offline(monkeypatch, tmp_path: Path) -> None:
    """When the Offline Edition's local wheelhouse is present, install_kokoro_onnx
    resolves entirely from disk (--no-index --find-links) instead of PyPI."""
    wheelhouse = tmp_path / "app-root" / "wheels" / "kokoro"
    wheelhouse.mkdir(parents=True)
    (wheelhouse / "kokoro_onnx-0.5.0-py3-none-any.whl").write_bytes(b"x")
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "app-root"))
    monkeypatch.setattr(ei, "is_kokoro_onnx_available", lambda: True)
    captured: dict = {}
    ei.install_kokoro_onnx(
        dest_dir=tmp_path / "kok", python_executable="py.exe", runner=_make_runner(captured)
    )
    cmd = captured["command"]
    assert "--no-index" in cmd
    assert "--find-links" in cmd and cmd[cmd.index("--find-links") + 1] == str(wheelhouse)


def test_kokoro_install_falls_back_to_pypi_without_wheelhouse(monkeypatch, tmp_path: Path) -> None:
    """No bundled wheelhouse (the regular installer, portable, or a source run)
    means the existing live-PyPI install path is unchanged."""
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    monkeypatch.setattr(ei, "is_kokoro_onnx_available", lambda: True)
    captured: dict = {}
    ei.install_kokoro_onnx(
        dest_dir=tmp_path / "kok", python_executable="py.exe", runner=_make_runner(captured)
    )
    cmd = captured["command"]
    assert "--no-index" not in cmd
    assert "--find-links" not in cmd


def test_kokoro_install_ignores_wheelhouse_when_requirements_overridden(
    monkeypatch, tmp_path: Path
) -> None:
    """An explicit `requirements` override (tests / advanced callers) is used
    as-is, matching the Vosk pinned-wheel pattern -- it skips the bundled
    wheelhouse lookup entirely rather than mixing the two."""
    wheelhouse = tmp_path / "app-root" / "wheels" / "kokoro"
    wheelhouse.mkdir(parents=True)
    (wheelhouse / "kokoro_onnx-0.5.0-py3-none-any.whl").write_bytes(b"x")
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "app-root"))
    monkeypatch.setattr(ei, "is_kokoro_onnx_available", lambda: True)
    captured: dict = {}
    ei.install_kokoro_onnx(
        dest_dir=tmp_path / "kok",
        requirements=("kokoro-onnx==0.5.0",),
        python_executable="py.exe",
        runner=_make_runner(captured),
    )
    cmd = captured["command"]
    assert "--no-index" not in cmd
    assert "kokoro-onnx==0.5.0" in cmd


def test_bundled_wheelhouse_dir_none_without_app_root(monkeypatch) -> None:
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    assert ei._bundled_wheelhouse_dir("kokoro") is None


def test_bundled_wheelhouse_dir_none_when_empty(monkeypatch, tmp_path: Path) -> None:
    empty = tmp_path / "wheels" / "kokoro"
    empty.mkdir(parents=True)
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path))
    assert ei._bundled_wheelhouse_dir("kokoro") is None


def test_bundled_wheelhouse_dir_found_when_populated(monkeypatch, tmp_path: Path) -> None:
    wheelhouse = tmp_path / "wheels" / "kokoro"
    wheelhouse.mkdir(parents=True)
    (wheelhouse / "soundfile-0.14.0-py3-none-any.whl").write_bytes(b"x")
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path))
    assert ei._bundled_wheelhouse_dir("kokoro") == wheelhouse


def test_bundled_wheelhouse_dir_is_name_scoped(monkeypatch, tmp_path: Path) -> None:
    """Each engine's wheelhouse is independent -- a populated kokoro wheelhouse
    must not be mistaken for a faster-whisper one."""
    kokoro = tmp_path / "wheels" / "kokoro"
    kokoro.mkdir(parents=True)
    (kokoro / "kokoro_onnx-0.5.0-py3-none-any.whl").write_bytes(b"x")
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path))
    assert ei._bundled_wheelhouse_dir("faster-whisper") is None


def test_faster_whisper_install_uses_bundled_wheelhouse_offline(
    monkeypatch, tmp_path: Path
) -> None:
    wheelhouse = tmp_path / "app-root" / "wheels" / "faster-whisper"
    wheelhouse.mkdir(parents=True)
    (wheelhouse / "faster_whisper-1.0-py3-none-any.whl").write_bytes(b"x")
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "app-root"))
    monkeypatch.setattr(ei, "is_faster_whisper_available", lambda: True)
    captured: dict = {}
    ei.install_faster_whisper(
        dest_dir=tmp_path / "fw", python_executable="py.exe", runner=_make_runner(captured)
    )
    cmd = captured["command"]
    assert "--no-index" in cmd
    assert "--find-links" in cmd and cmd[cmd.index("--find-links") + 1] == str(wheelhouse)


def test_mp3_install_uses_bundled_wheelhouse_offline(monkeypatch, tmp_path: Path) -> None:
    wheelhouse = tmp_path / "app-root" / "wheels" / "mp3"
    wheelhouse.mkdir(parents=True)
    (wheelhouse / "mutagen-1.48.1-py3-none-any.whl").write_bytes(b"x")
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "app-root"))
    monkeypatch.setattr(ei, "is_mp3_available", lambda: True)
    captured: dict = {}
    ei.install_mp3_support(
        dest_dir=tmp_path / "mp3", python_executable="py.exe", runner=_make_runner(captured)
    )
    cmd = captured["command"]
    assert "--no-index" in cmd
    assert "--find-links" in cmd and cmd[cmd.index("--find-links") + 1] == str(wheelhouse)


def test_vosk_install_prefers_bundled_wheelhouse_over_pinned_wheel(
    monkeypatch, tmp_path: Path
) -> None:
    """The wheelhouse also captures vosk's transitive cffi dependency (a full
    `pip download` closure), so --no-index is finally safe for Vosk here --
    unlike the single pinned assets-v1 wheel path below it, which cannot."""
    wheelhouse = tmp_path / "app-root" / "wheels" / "vosk"
    wheelhouse.mkdir(parents=True)
    (wheelhouse / "vosk-0.3.45-py3-none-win_amd64.whl").write_bytes(b"x")
    (wheelhouse / "cffi-1.16.0-cp313-cp313-win_amd64.whl").write_bytes(b"x")
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "app-root"))
    monkeypatch.setattr(ei, "is_vosk_available", lambda: True)

    def fail_if_called(progress):
        raise AssertionError("assets-v1 pinned-wheel fetch should not run when a wheelhouse exists")

    monkeypatch.setattr(ei, "_maybe_fetch_vosk_wheel", fail_if_called)
    captured: dict = {}
    ei.install_vosk(
        dest_dir=tmp_path / "vosk", python_executable="py.exe", runner=_make_runner(captured)
    )
    cmd = captured["command"]
    assert "--no-index" in cmd
    assert "--find-links" in cmd and cmd[cmd.index("--find-links") + 1] == str(wheelhouse)
    assert "vosk>=0.3.45" in cmd


def test_install_mp3_support_builds_wheel_only_command(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ei, "is_mp3_available", lambda: True)
    captured: dict = {}
    dest = tmp_path / "mp3"
    out = ei.install_mp3_support(
        dest_dir=dest, python_executable="py.exe", runner=_make_runner(captured)
    )
    cmd = captured["command"]
    assert out == dest and dest.is_dir()
    assert cmd[1:4] == ["-m", "pip", "install"]
    assert "mutagen>=1.48.1" in cmd
    assert str(dest) in sys.path  # activated on success


def test_install_mp3_support_blocked_in_safe_mode(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(ei.EngineInstallError, match="Safe Mode"):
        ei.install_mp3_support(dest_dir=tmp_path / "mp3", runner=_make_runner({}))
