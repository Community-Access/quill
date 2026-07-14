"""Root test configuration.

Activates the ``_DEV_BUILD`` flag in :mod:`quill.core.paths` for the entire
test suite so that ``QUILL_DATA_DIR`` overrides (used by almost every test
fixture for isolation) are honoured.  Without this flag the guard added by
H-1-core silently ignores ``QUILL_DATA_DIR`` in non-dev builds, causing tests
to write to the real ``%APPDATA%\\Quill`` path and fail with stale state.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Force pytest's ``tmp_path`` base directory under ``$HOME``.

    ``paths.app_data_dir()`` only honours a ``QUILL_DATA_DIR`` override when
    it resolves under ``Path.home()`` (H-1-core: rejects an override that
    could redirect to an attacker-controlled path). Nearly every test that
    isolates ``QUILL_DATA_DIR`` does so via the ``tmp_path`` fixture -- but
    pytest's default tmp base is the OS temp directory, which on Windows
    happens to live under ``%USERPROFILE%`` (home-relative) but on macOS is
    ``/private/var/folders/...`` -- never under ``$HOME``. Every such test on
    macOS therefore silently failed the H-1-core check and fell through to
    the *real* ``~/.quill`` directory, reading and writing real state and
    cross-contaminating later tests. This was invisible until now because
    the macOS release CI job always segfaulted before pytest could report
    the resulting failures (see the voice_browser_dialog fix). Forcing
    basetemp under ``$HOME`` makes ``tmp_path`` satisfy the guard -- and
    thus provide real isolation -- on every platform, not just by accident
    on Windows.
    """
    if config.option.basetemp is None:
        config.option.basetemp = str(Path.home() / ".quill-pytest-tmp")


@pytest.fixture(autouse=True, scope="session")
def _enable_dev_build_for_tests() -> None:
    """Patch paths._DEV_BUILD=True for the whole test session."""
    import quill.core.paths as paths_mod

    paths_mod._DEV_BUILD = True


@pytest.fixture()
def quill_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Isolated QUILL_DATA_DIR guaranteed to be accepted by paths.app_data_dir().

    With _DEV_BUILD=True (set by the session fixture above), any resolvable
    path is accepted.  Use this fixture instead of a bare
    ``monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))`` when the test
    needs a clean data directory — it wires up the env var and returns the
    path so test code can inspect written files.
    """
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture()
def isolated_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point the user-profile env vars at a per-test temp directory.

    Opt-in isolation for tests that read ``APPDATA``/``LOCALAPPDATA``/``HOME``/
    ``USERPROFILE`` (directly or via a fallback path) so they cannot pick up the
    developer's real profile state — the class of bug that made
    ``test_storage_mode_uses_portable_root`` pass in CI but fail locally.

    Deliberately **not** autouse: a blanket autouse breaks ~36 core tests that
    legitimately depend on the real profile environment (e.g. atomic-write and
    legacy-migration checks). Request this fixture explicitly in tests that touch
    profile-derived paths. Returns the fake home directory.
    """
    home = tmp_path / "_home"
    appdata = home / "AppData" / "Roaming"
    local = home / "AppData" / "Local"
    for path in (appdata, local):
        path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("HOME", str(home))
    return home
