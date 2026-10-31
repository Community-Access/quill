"""Give a control a name a Windows screen reader actually speaks (#1693).

``wx.Window.SetName`` is not an accessible name on Windows: wxMSW keeps it as
the window's own lookup key, and NVDA, JAWS and Narrator never read it. What
they read is the MSAA ``accName`` of the control, which for a plain edit field,
list or combo box Windows derives from the ``wx.StaticText`` created just
before it. A control with no such label -- or whose label is built in another
function, or only exists as a ``SetName`` -- announces as a bare role.

There are two supported ways to set ``accName`` from Python:

* ``wx.Window.SetAccessibleName`` -- added in wxWidgets 3.3.4 (PR #27056) and
  exposed from wxPython 4.3.2. QUILL pins 4.3.1, which does not have it, so
  this path is taken only when the running wxPython offers it.
* ``wx.Window.SetAccessible`` with a ``wx.Accessible`` whose ``GetName`` answers
  for the control itself. Available in every wxPython on Windows (it is built
  with ``wxUSE_ACCESSIBILITY``); wxMSW answers ``WM_GETOBJECT`` with it and
  passes every method the subclass does not implement to the standard
  ``IAccessible`` the control would have had anyway. QUILL already relies on
  this for the Sound Enhancements sliders, the Audio Studio wizard and the
  Table Studio grid.

:func:`set_spoken_name` uses the first when it exists and the second when it
does not. It never touches the window name, because window names double as F1
help-topic keys and ``FindWindowByName`` targets. On macOS it also pushes the
name onto the native ``NSAccessibility`` label, the same push
:mod:`quill.ui.accessible_names` makes for VoiceOver (#1012).

The name is answered **only for the control itself** (MSAA child id 0). A list
box, list control or tree reports its rows as MSAA children of the same window;
answering the control's name for those would make every row speak as the list.
Rows fall through to the standard object, exactly as before.
"""

from __future__ import annotations

import sys
from typing import Any

try:  # wx is optional for the fakes-based tests that import this module.
    import wx
except Exception:  # noqa: BLE001 - no wx at all: every call is a no-op
    wx = None  # type: ignore[assignment]

#: The attribute a helper is kept alive under. ``SetAccessible`` does not keep
#: a Python reference, so without one the helper is collected and the name
#: tests as present and speaks as absent.
_HELPER_ATTR = "_spoken_name_helper"
_PART_HELPERS_ATTR = "_spoken_name_part_helpers"

#: The ``wx.Accessible`` subclass once built; ``False`` once known unavailable.
_NAMED_CLASS: Any = None


def _named_accessible_class() -> type | None:
    """The ``wx.Accessible`` subclass, built once; ``None`` off Windows."""
    global _NAMED_CLASS
    if _NAMED_CLASS is not None:
        return _NAMED_CLASS or None
    accessible = getattr(wx, "Accessible", None) if wx is not None else None
    if accessible is None:
        _NAMED_CLASS = False
        return None
    acc_ok = wx.ACC_OK
    not_implemented = wx.ACC_NOT_IMPLEMENTED

    class _SpokenName(accessible):  # type: ignore[misc, valid-type]
        """Answers ``accName`` for the control and defers on everything else."""

        def __init__(self, name: str) -> None:
            super().__init__()
            self.spoken_name = name

        def GetName(self, childId: int) -> tuple[int, str]:  # noqa: N802,N803 - wx API casing
            if childId == 0:
                return (acc_ok, self.spoken_name)
            return (not_implemented, "")

    _NAMED_CLASS = _SpokenName
    return _SpokenName


def _attach(ctrl: Any, name: str) -> Any | None:
    """Attach the helper to one window; return it, or ``None`` if unsupported."""
    cls = _named_accessible_class()
    if cls is None:
        return None
    existing = getattr(ctrl, _HELPER_ATTR, None)
    if existing is not None:
        # Renaming: update the live helper instead of replacing it, so a
        # reader holding the old IAccessible hears the new name too.
        existing.spoken_name = name
        return existing
    try:
        helper = cls(name)
        ctrl.SetAccessible(helper)
        setattr(ctrl, _HELPER_ATTR, helper)
    except (AttributeError, NotImplementedError, TypeError, RuntimeError):
        return None
    return helper


def _name_parts(ctrl: Any, name: str) -> None:
    """Name the inner edit and spinner of a composite spin control.

    ``wx.SpinCtrlDouble`` is a ``TextCtrl`` plus a ``SpinButton``, and UIA sees
    them as separate focusable elements. The helpers are anchored on the
    composite, because wxPython hands out a fresh proxy for a C++-created child
    on every ``GetChildren`` call and an attribute set on it would die with it.
    """
    if wx is None:
        return
    parts: tuple[type, ...] = tuple(
        cls for cls in (getattr(wx, "TextCtrl", None), getattr(wx, "SpinButton", None)) if cls
    )
    if not parts or not isinstance(ctrl, getattr(wx, "SpinCtrlDouble", ())):
        return
    anchored: list[Any] = []
    try:
        children = list(ctrl.GetChildren())
    except Exception:  # noqa: BLE001
        return
    for child in children:
        if isinstance(child, parts):
            helper = _attach(child, name)
            if helper is not None:
                anchored.append(helper)
    if anchored:
        setattr(ctrl, _PART_HELPERS_ATTR, anchored)


def set_spoken_name(ctrl: Any, name: object) -> bool:
    """Give *ctrl* an accessible name that Windows screen readers speak.

    *name* is cleaned the way a visible label is (``&`` mnemonic, trailing
    colon and ellipsis removed). Returns True when a name reached the
    accessibility layer, False when the platform offers no way to set one
    (non-Windows without ``SetAccessibleName``) or the name was empty. Never
    raises: a naming failure must not break building a dialog.
    """
    from quill.ui.accessible_names import _macos_native_label, accessible_label

    text = accessible_label(name)
    if not text or ctrl is None:
        return False
    if sys.platform == "darwin":
        _macos_native_label(ctrl, text)
    set_native = getattr(ctrl, "SetAccessibleName", None)
    if callable(set_native):
        try:
            set_native(text)
            return True
        except Exception:  # noqa: BLE001 - fall back to wx.Accessible
            pass
    if _attach(ctrl, text) is None:
        return sys.platform == "darwin"
    _name_parts(ctrl, text)
    return True


def spoken_name(ctrl: Any) -> str:
    """The name :func:`set_spoken_name` gave *ctrl*, or ``""``.

    For tests and diagnostics. Reads ``GetAccessibleName`` where wxPython has
    it, otherwise asks the attached helper the way MSAA would.
    """
    getter = getattr(ctrl, "GetAccessibleName", None)
    if callable(getter):
        try:
            value = getter()
            if value:
                return str(value)
        except Exception:  # noqa: BLE001
            pass
    helper = getattr(ctrl, _HELPER_ATTR, None)
    if helper is None:
        return ""
    status, value = helper.GetName(0)
    return str(value) if wx is not None and status == wx.ACC_OK else ""
