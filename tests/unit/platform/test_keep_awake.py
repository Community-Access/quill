"""Unit tests for the keep-awake (prevent system standby) helper."""

from __future__ import annotations

import quill.platform.keep_awake as keep_awake


def test_non_windows_is_a_noop(monkeypatch) -> None:
    # On macOS/Linux the helper reports False (the OS was not asked) and never
    # touches ctypes.
    monkeypatch.setattr(keep_awake.sys, "platform", "linux")
    assert keep_awake.set_keep_awake(True) is False
    assert keep_awake.set_keep_awake(False) is False


def test_windows_calls_setthreadexecutionstate(monkeypatch) -> None:
    # Pretend we are on Windows and capture the flags passed to the OS call,
    # without depending on the real machine's platform.
    calls: list[int] = []

    class _FakeKernel:
        def SetThreadExecutionState(self, flags: int) -> int:
            calls.append(flags)
            return 1  # non-zero: success

    class _FakeWinDLL:
        kernel32 = _FakeKernel()

    monkeypatch.setattr(keep_awake.sys, "platform", "win32")

    import ctypes

    monkeypatch.setattr(ctypes, "windll", _FakeWinDLL(), raising=False)

    assert keep_awake.set_keep_awake(True) is True
    assert keep_awake.set_keep_awake(False) is True
    # First call sets ES_CONTINUOUS | ES_SYSTEM_REQUIRED; release keeps only
    # ES_CONTINUOUS (system standby allowed again).
    assert calls[0] == keep_awake._ES_CONTINUOUS | keep_awake._ES_SYSTEM_REQUIRED
    assert calls[1] == keep_awake._ES_CONTINUOUS
