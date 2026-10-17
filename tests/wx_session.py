"""One ``wx.App`` per test process, and one sanctioned way to patch ``wx.CallAfter``.

**The App.** Two hundred and thirty test files used to build their own
``wx.App()`` -- per test, per module, or inline -- and many destroyed it in
teardown. wx supports one App per process. Whether a file met an App another
file had already destroyed (its Python object alive, its C++ half gone: "The
wx.App object must be created first!") was decided by which files shared a
pytest-xdist worker, so adding an unrelated file could fail an old one; it
did, on 2026-09-12 (``tests/unit/apps/conftest.py`` ``wx_app`` has the story).
:func:`shared_wx_app` hands every caller the same live App and never lets a
test destroy it: ``Destroy()`` on it is a no-op, so the old teardown lines are
harmless and every test's meaning ("I need an App") is unchanged. The
``wx_session_app`` fixture in ``tests/conftest.py`` is the fixture form.

**CallAfter.** Replacing ``wx.CallAfter`` replaces it for the whole process --
every module that did ``import wx`` sees the same attribute, and so does any
background thread still running from an earlier test. :func:`patch_call_after`
is the one place that does it: always through the test's own ``monkeypatch``
(so it is undone at teardown, never left behind), always on the real ``wx``
module (patching ``some_module.wx`` is the same object, written in a way a
reader cannot see is global), and it records every call it intercepted. The
``wx_call_after`` fixture is the fixture form.

``tests/unit/test_wx_test_hygiene.py`` fails when a test file builds its own
App or patches ``CallAfter`` any other way. Imports wx lazily, so importing
this module never fails collection where wx is absent.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["CallAfterCapture", "patch_call_after", "shared_wx_app"]

_APP: Any = None


def _alive(app: Any) -> bool:
    try:
        app.GetAppName()  # raises once the C++ peer is gone
    except Exception:  # noqa: BLE001 - any failure means "not usable"
        return False
    return True


def shared_wx_app() -> Any:
    """The process's one live ``wx.App``, created on first use.

    An App somebody else made (a test of a real app class) is returned while
    it lives; otherwise the session App is (re)built. Its ``Destroy`` does
    nothing: the App outlives every test.
    """
    global _APP
    import wx

    current = wx.GetApp()
    if current is not None and _alive(current):
        return current

    class _SessionApp(wx.App):
        """The test process's App. Tests may call Destroy; it stays."""

        def Destroy(self) -> None:  # noqa: N802 - wx's name
            return None

    _APP = _SessionApp(False)
    return _APP


class CallAfterCapture:
    """What a patched ``wx.CallAfter`` received during one test."""

    def __init__(self) -> None:
        self.calls: list[tuple[Callable[..., Any], tuple[Any, ...], dict[str, Any]]] = []

    def __len__(self) -> int:
        return len(self.calls)


def patch_call_after(
    monkeypatch: Any,
    replacement: Callable[..., Any] | None = None,
) -> CallAfterCapture:
    """Replace ``wx.CallAfter`` for the rest of this test only.

    *replacement* receives exactly what ``CallAfter`` would; ``None`` runs the
    callback at once, inline, which is what most tests want. Returns a
    :class:`CallAfterCapture` listing every call, whatever *replacement* did.
    """
    import wx

    capture = CallAfterCapture()
    run = replacement if replacement is not None else (lambda fn, *a, **k: fn(*a, **k))

    def call_after(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        capture.calls.append((fn, args, kwargs))
        return run(fn, *args, **kwargs)

    monkeypatch.setattr(wx, "CallAfter", call_after)
    return capture
