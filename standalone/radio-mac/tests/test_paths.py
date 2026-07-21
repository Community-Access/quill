"""Tests for quill_radio_mac.core.paths.

Covers the full data-directory resolution order: the QUILL_DATA_DIR
environment override, portable mode (QUILL_PORTABLE with and without
QUILL_APP_ROOT), and the per-platform defaults (darwin, win32, other
POSIX). Platform and home directory are monkeypatched so the suite
passes identically on Windows and macOS with no real environment
leakage. All tests are pure filesystem tests against tmp_path; no
network, no wx.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _clear_env(monkeypatch) -> None:
    """Remove every environment variable paths.py consults."""
    monkeypatch.delenv("QUILL_DATA_DIR", raising=False)
    monkeypatch.delenv("QUILL_PORTABLE", raising=False)
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)


def test_app_data_dir_macos(monkeypatch, tmp_path):
    monkeypatch.delenv("QUILL_DATA_DIR", raising=False)
    monkeypatch.delenv("QUILL_PORTABLE", raising=False)
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    from quill_radio_mac.core import paths
    assert paths.app_data_dir() == tmp_path / "Library" / "Application Support" / "Quill"


def test_app_data_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "custom"))
    from quill_radio_mac.core import paths
    assert paths.app_data_dir() == tmp_path / "custom"


def test_app_data_dir_creates_directory(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "made" / "here"))
    from quill_radio_mac.core import paths
    result = paths.app_data_dir()
    assert result.is_dir()


def test_app_data_dir_portable_app_root(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("QUILL_PORTABLE", "1")
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "bundle"))
    from quill_radio_mac.core import paths
    assert paths.app_data_dir() == tmp_path / "bundle" / "data"


def test_app_data_dir_portable_beside_executable(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("QUILL_PORTABLE", "1")
    fake_exe = tmp_path / "bin" / "quill-radio-mac"
    monkeypatch.setattr("sys.executable", str(fake_exe))
    from quill_radio_mac.core import paths
    assert paths.app_data_dir() == tmp_path / "bin" / "data"


def test_env_override_beats_portable(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "override"))
    monkeypatch.setenv("QUILL_PORTABLE", "1")
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "bundle"))
    from quill_radio_mac.core import paths
    assert paths.app_data_dir() == tmp_path / "override"


def test_app_data_dir_win32(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    from quill_radio_mac.core import paths
    assert paths.app_data_dir() == tmp_path / "Roaming" / "Quill"


def test_app_data_dir_linux_default(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    from quill_radio_mac.core import paths
    assert paths.app_data_dir() == tmp_path / ".local" / "share" / "Quill"


def test_recordings_dir(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "root"))
    from quill_radio_mac.core import paths
    assert paths.recordings_dir() == tmp_path / "root" / "radio_recordings"
    assert paths.recordings_dir().is_dir()


def test_importing_paths_never_imports_wx(monkeypatch):
    """The core package must stay importable without wxPython."""
    import quill_radio_mac
    import quill_radio_mac.core.paths  # noqa: F401
    # wx may already be importable on this machine; the contract is that
    # the paths module itself holds no wx reference.
    assert "wx" not in vars(sys.modules["quill_radio_mac.core.paths"])
