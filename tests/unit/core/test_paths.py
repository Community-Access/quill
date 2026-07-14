"""Tests for the QUILL_DATA_DIR override constraint (H-1-core).

The ``QUILL_DATA_DIR`` env var is documented as a *dev-only* override for
the user data directory. Release builds must ignore it; dev builds
(``QUILL_DEV_BUILD=1``) accept it only when the resolved path stays
inside the user's home directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from quill.core import paths


@pytest.fixture
def isolated_data_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Use a fresh data dir and clear other env vars that influence app_data_dir."""
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "quill"))
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("QUILL_PORTABLE_ROOT", raising=False)
    return tmp_path


def test_default_returns_home_quill(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """L-1: on non-Windows, app_data_dir falls back to $HOME/.quill when APPDATA missing."""
    monkeypatch.delenv("QUILL_DATA_DIR", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("QUILL_PORTABLE_ROOT", raising=False)
    monkeypatch.setattr(paths, "Path", paths.Path)  # ensure no stub
    monkeypatch.setattr(paths, "_DEV_BUILD", False)
    monkeypatch.setattr(paths.sys, "platform", "linux")
    # Force Path.home() to a known value for determinism.
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: fake_home))
    result = paths.app_data_dir()
    assert result == fake_home / ".quill"


def test_windows_raises_when_appdata_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """L-1: on Windows, missing APPDATA raises RuntimeError instead of using a hidden dir."""
    monkeypatch.delenv("QUILL_DATA_DIR", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("QUILL_PORTABLE_ROOT", raising=False)
    monkeypatch.setattr(paths, "_DEV_BUILD", False)
    monkeypatch.setattr(paths.sys, "platform", "win32")
    with pytest.raises(RuntimeError, match="APPDATA is not set"):
        paths.app_data_dir()


def test_release_build_ignores_quill_data_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """H-1-core: in a release build, the env var is ignored entirely."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.setattr(paths, "_DEV_BUILD", False)
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "override"))
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("QUILL_PORTABLE_ROOT", raising=False)
    monkeypatch.setattr(paths.sys, "platform", "linux")
    result = paths.app_data_dir()
    assert result == fake_home / ".quill"


def test_dev_build_accepts_override_under_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """H-1-core: a dev build honours QUILL_DATA_DIR when it is under $HOME."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    target = fake_home / "quill-dev"
    target.mkdir()
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.setattr(paths, "_DEV_BUILD", True)
    monkeypatch.setenv("QUILL_DATA_DIR", str(target))
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("QUILL_PORTABLE_ROOT", raising=False)
    result = paths.app_data_dir()
    assert result == target.resolve()


def test_app_data_dir_resolves_custom_storage_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """#615: a saved "custom" storage mode redirects app_data_dir()."""
    from quill.core.storage_mode import save_storage_mode

    monkeypatch.delenv("QUILL_DATA_DIR", raising=False)
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    target = tmp_path / "CustomQuillData"
    save_storage_mode("custom", path=target)

    assert paths.app_data_dir() == target.resolve()


def test_dev_build_rejects_override_outside_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """H-1-core: a dev build falls back when the override escapes $HOME."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.setattr(paths, "_DEV_BUILD", True)
    # On Linux/macOS ``/etc`` is outside $HOME; on Windows use a fixed
    # path under the system drive that is provably outside the user's
    # profile. We pick a platform-agnostic absolute path under /tmp.
    outside = Path("/etc").resolve()
    if sys.platform == "win32":
        # ``C:\Windows\System32`` is outside any per-user profile.
        outside = Path("C:/Windows/System32/quill-data").resolve()
    monkeypatch.setenv("QUILL_DATA_DIR", str(outside))
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("QUILL_PORTABLE_ROOT", raising=False)
    monkeypatch.setattr(paths.sys, "platform", "linux")
    result = paths.app_data_dir()
    # We must NOT return the outside path; we fall back to $HOME/.quill.
    assert result == fake_home / ".quill"
    assert result.resolve() != outside
