"""A portable QuillLite keeps its settings on the stick, not on the host PC.

The whole promise of a portable build is that it leaves nothing behind on
somebody else's computer. QuillLite broke that promise silently: its data
folder resolves through
:func:`quill.core.storage_mode.portable_root_dir`, which only recognises a
bundle whose launcher name is in an allowlist -- and ``QuillLite.exe`` was not
in it. So a portable QuillLite wrote settings, recent files and recovery copies
of in-progress documents into ``%LOCALAPPDATA%\\QuillLite`` on the host machine,
announced nothing, and looked exactly like a working portable build.

Tested here as well as in ``tests/unit/core/test_storage_mode.py`` because the
allowlist and QuillLite's own path chain are two separate things that both have
to hold, and QuillLite is the product where getting it wrong is worst: a
recovery slot is an unsaved document, so the leak is the user's actual writing
rather than a window size.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core import storage_mode
from quill.core.lite import paths as lite_paths


@pytest.fixture(autouse=True)
def _no_ambient_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Neither the developer's environment nor a real bundle may leak in."""
    monkeypatch.delenv("QUILL_LITE_DATA_DIR", raising=False)
    monkeypatch.delenv("QUILL_PORTABLE", raising=False)
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    fake_exe_dir = tmp_path / "fake-python" / "bin"
    fake_exe_dir.mkdir(parents=True)
    monkeypatch.setattr(storage_mode.sys, "executable", str(fake_exe_dir / "python.exe"))


def _portable_quilllite_bundle(tmp_path: Path) -> Path:
    """What the portable zip extracts to: the launcher and a data/ folder."""
    root = tmp_path / "QuillLite"
    root.mkdir()
    (root / "QuillLite.exe").write_bytes(b"MZ\x00\x00")
    (root / "data").mkdir()
    return root


def test_portable_quilllite_writes_beside_itself(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = _portable_quilllite_bundle(tmp_path)
    monkeypatch.setenv("QUILL_APP_ROOT", str(root))
    monkeypatch.setenv("QUILL_PORTABLE", "1")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "host-profile"))

    data = lite_paths.data_dir()

    assert data == root / "data" / "QuillLite"
    assert not (tmp_path / "host-profile").exists(), (
        "a portable build must not create a folder in the host machine's profile"
    )


def test_the_recovery_and_settings_files_follow_the_data_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Recovery is the one that matters most: a slot is an unsaved document."""
    root = _portable_quilllite_bundle(tmp_path)
    monkeypatch.setenv("QUILL_APP_ROOT", str(root))
    monkeypatch.setenv("QUILL_PORTABLE", "1")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "host-profile"))

    stick = root / "data" / "QuillLite"
    assert lite_paths.settings_path().parent == stick
    assert lite_paths.recovery_dir().parent == stick
    assert lite_paths.inbox_dir().parent == stick


def test_an_installed_quilllite_still_uses_the_local_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The installed build ships no data/ folder and must not change."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "host-profile"))

    assert lite_paths.data_dir() == tmp_path / "host-profile" / "QuillLite"


def test_an_explicit_override_beats_everything(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """QUILL_LITE_DATA_DIR is what a support answer and the tests reach for."""
    root = _portable_quilllite_bundle(tmp_path)
    monkeypatch.setenv("QUILL_APP_ROOT", str(root))
    monkeypatch.setenv("QUILL_PORTABLE", "1")
    monkeypatch.setenv("QUILL_LITE_DATA_DIR", str(tmp_path / "chosen"))

    assert lite_paths.data_dir() == tmp_path / "chosen"
