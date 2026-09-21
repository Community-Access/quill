"""The subclass trampoline outlives every message that can still be inside it.

:mod:`quill.ui.richedit_line_fix` puts a ``comctl32`` window subclass in the
editor's message loop so a screen reader's cross-process ``SendMessage`` gets
the corrected caret line. That is the point of it -- and it is also what makes
the callback's lifetime load-bearing in a way a pure-Python object's never is.
Free the trampoline while the window still points at it and the next message
lands in released memory: the process dies, mid-edit, with an access violation
inside ``DefSubclassProc``.

Which is what happened. QUILL crashed repeatedly in the nightly UIA run --
``access violation reading 0xFFFFFFFFFFFFFFFF``, then writing ``0x0`` -- and it
surfaced as two UI-automation tests failing to find the main window, so it read
as a flaky robot rather than as a crash.

Two defects, both here:

* ``remove_final_line_fix`` popped the callback out of the registry **before**
  calling ``RemoveWindowSubclass``, so a failure or an exception there left the
  window pointing at a trampoline nothing referenced.
* Removal was driven by ``EVT_WINDOW_DESTROY``, which wx sends while the HWND
  is still alive and still receiving messages. ``WM_NCDESTROY`` is the
  documented moment, and the only one after which nothing further can arrive.

These tests are pure bookkeeping -- a stub stands in for ``comctl32`` -- because
the bookkeeping is the bug. They run everywhere, including the Linux and macOS
runners where the real subclass never installs at all.
"""

from __future__ import annotations

import pytest

from quill.ui import richedit_line_fix as fix


class _StubComctl:
    """Enough of comctl32 to watch the registry, and to fail on demand."""

    def __init__(self, *, remove_raises: bool = False, remove_returns: bool = True) -> None:
        self.removed: list[tuple[int, int]] = []
        self._remove_raises = remove_raises
        self._remove_returns = remove_returns

    def SetWindowSubclass(self, hwnd, callback, subclass_id, ref):  # noqa: N802,ANN001
        return True

    def RemoveWindowSubclass(self, hwnd, callback, subclass_id):  # noqa: N802,ANN001
        if self._remove_raises:
            raise OSError("exception: access violation reading 0xFFFFFFFFFFFFFFFF")
        self.removed.append((hwnd.value if hasattr(hwnd, "value") else hwnd, subclass_id))
        return self._remove_returns

    def DefSubclassProc(self, hwnd, msg, wparam, lparam):  # noqa: N802,ANN001
        return 0


@pytest.fixture
def registry(monkeypatch):
    """A clean registry and a stub comctl32, restored afterwards."""

    def _install(**kwargs):
        stub = _StubComctl(**kwargs)
        monkeypatch.setattr(fix, "_comctl32", stub)
        monkeypatch.setattr(fix, "_AVAILABLE", True)
        monkeypatch.setattr(fix, "_INSTALLED", {})
        monkeypatch.setattr(fix, "_RETIRED", [])
        return stub

    return _install


def test_a_removed_callback_is_retired_not_released(registry) -> None:
    """The trampoline must still exist after the subclass comes off."""
    stub = registry()
    sentinel = object()
    fix._INSTALLED[4242] = sentinel

    assert fix.remove_final_line_fix(4242) is True
    assert stub.removed == [(4242, fix._SUBCLASS_ID)]
    assert 4242 not in fix._INSTALLED, "the hwnd is no longer installed"
    assert sentinel in fix._RETIRED, (
        "the callback was dropped instead of retired; a cross-process "
        "SendMessage still inside it would land in freed memory"
    )


def test_a_failed_removal_still_keeps_the_callback_alive(registry) -> None:
    """The case the old order got exactly backwards.

    It popped first and removed second, so a raising ``RemoveWindowSubclass``
    left the window pointing at a trampoline with no reference anywhere.
    """
    registry(remove_raises=True)
    sentinel = object()
    fix._INSTALLED[99] = sentinel

    assert fix.remove_final_line_fix(99) is False
    assert 99 not in fix._INSTALLED
    assert sentinel in fix._RETIRED, "a failed removal must never release the callback"


def test_a_refused_removal_still_keeps_the_callback_alive(registry) -> None:
    """``RemoveWindowSubclass`` returning FALSE is the same hazard, quietly."""
    registry(remove_returns=False)
    sentinel = object()
    fix._INSTALLED[7] = sentinel

    fix.remove_final_line_fix(7)
    assert sentinel in fix._RETIRED


def test_removing_twice_is_harmless(registry) -> None:
    stub = registry()
    fix._INSTALLED[5] = object()

    assert fix.remove_final_line_fix(5) is True
    assert fix.remove_final_line_fix(5) is False
    assert len(stub.removed) == 1, "the second call must not touch the window again"


def test_an_unknown_hwnd_is_not_an_error(registry) -> None:
    registry()
    assert fix.remove_final_line_fix(0) is False
    assert fix.remove_final_line_fix(12345) is False


def test_is_installed_tracks_the_registry(registry) -> None:
    registry()
    fix._INSTALLED[31] = object()
    assert fix.is_installed(31) is True
    fix.remove_final_line_fix(31)
    assert fix.is_installed(31) is False


def test_the_procedure_detaches_on_wm_ncdestroy() -> None:
    """The message the subclass must come off at, and the one it must not.

    ``WM_NCDESTROY`` is 0x0082. If this constant ever drifts, removal stops
    happening at the documented moment and the crash comes back.
    """
    assert fix._WM_NCDESTROY == 0x0082
    assert fix._WM_NCDESTROY not in fix._WATCHED, (
        "WM_NCDESTROY must pass through to DefSubclassProc after detaching, "
        "not be answered as one of the four questions"
    )
