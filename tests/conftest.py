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
    _configure_hypothesis()


def _configure_hypothesis() -> None:
    """Register the suite's Hypothesis profile (no-op if it isn't installed).

    ``deadline=None`` disables Hypothesis's per-example time limit. The default
    (200ms) measures wall-clock per generated example, which on a loaded CI
    runner -- four xdist workers plus AST-scanning gates -- turns an otherwise
    passing property into an intermittent DeadlineExceeded. Correctness, not
    latency, is what these properties assert; the suite-wide pytest ``timeout``
    still bounds a genuinely hung test.
    """
    try:
        from hypothesis import HealthCheck, settings
    except ModuleNotFoundError:  # property tests skip themselves without it
        return
    settings.register_profile(
        "quill",
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
    settings.load_profile("quill")


@pytest.fixture(autouse=True, scope="session")
def _enable_dev_build_for_tests() -> None:
    """Patch paths._DEV_BUILD=True for the whole test session."""
    import quill.core.paths as paths_mod

    paths_mod._DEV_BUILD = True


@pytest.fixture(autouse=True)
def _no_ambient_provider_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hide the developer's own provider API keys from every test.

    ``assistant_ai.environment_api_key`` falls back to these variables, so a
    machine that legitimately exports one for unrelated work would otherwise
    make key-related tests pass (or fail) for reasons that have nothing to do
    with the code under test, and would differ from CI. Derived from the
    provider table so a newly supported variable cannot be forgotten here.
    """
    from quill.core.assistant_ai import _PROVIDER_ENV_VARS

    for names in _PROVIDER_ENV_VARS.values():
        for name in names:
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _reclaim_leaked_wx_windows():
    """Destroy wx top-level windows a test created but never destroyed.

    Windows caps a process at 10,000 User (window) handles. A wx.Frame or
    wx.Dialog that simply falls out of scope keeps its native window alive for
    the life of the process -- Python's garbage collector does not destroy a wx
    window, only ``Destroy()`` does. Measured: an App plus one Frame, one
    Dialog and twenty controls is 28 USER objects; dropping the frame without
    destroying it leaks 2, and at roughly 2-4 leaked per widget test the suite
    reaches the ceiling about three quarters of the way through. Past it every
    CreateWindowEx fails and the run collapses into failures that look
    unrelated to their own tests ("Failed to create dialog. Incorrect
    DLGTEMPLATE?", "can't append invalid menu to menubar").

    ``Destroy()`` only SCHEDULES deletion -- the handle is reclaimed when wx
    processes its pending-delete list -- so the event loop must be pumped
    afterwards or nothing is actually freed. (A first attempt at this fixture
    pumped with ``app.ProcessIdle()``, which does not exist on ``wx.App``; the
    AttributeError was swallowed by a broad except and the fixture silently did
    nothing, which is why it appeared not to help.)

    Only windows that appeared *during* the test are destroyed, so a module- or
    session-scoped fixture's window survives. Teardown never fails a test.
    """
    import sys

    def _live_wx():
        """The real wx module with a running App, else None.

        Some tests install a ``types.SimpleNamespace`` stub as ``sys.modules
        ["wx"]``, so the module being importable proves nothing -- check that
        the functions actually exist before calling them. Explicit rather than
        a broad try/except: swallowing AttributeError here is what hid the
        ``ProcessIdle`` mistake described above.
        """
        wx = sys.modules.get("wx")
        get_app = getattr(wx, "GetApp", None)
        if (
            wx is None
            or not callable(get_app)
            or not callable(getattr(wx, "GetTopLevelWindows", None))
        ):
            return None
        return wx if get_app() is not None else None

    def _top_level_ids() -> set[int]:
        wx = _live_wx()
        if wx is None:
            return set()
        return {id(win) for win in wx.GetTopLevelWindows()}

    before = _top_level_ids()
    yield
    wx = _live_wx()
    if wx is None:
        return
    leaked = [win for win in wx.GetTopLevelWindows() if id(win) not in before]
    if not leaked:
        return  # nothing to reclaim: skip the pump entirely (it is not free)
    for win in leaked:
        try:
            win.Destroy()
        except Exception:  # noqa: BLE001 - an already-dead window is fine
            pass
    try:
        wx.GetApp().ProcessPendingEvents()
        wx.SafeYield()
    except Exception:  # noqa: BLE001
        pass


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
