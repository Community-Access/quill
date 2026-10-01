"""Alt+Tab back into QUILL Lite lands in the document.

Reported 2026-09-29: "if I have a file open, if I Alt+Tab to another
application and then back to QUILL Lite, focus doesn't always return to the
edit box... The bug is hard to reproduce because pressing Ctrl+Tab in the
editor moved focus to the edit box as expected. Since then, Alt+Tabbing back
has also returned focus directly to the edit box."

That last sentence is the whole diagnosis. QUILL Lite is MDI: the one top-level
window is the shell, and documents are ``wx.MDIChildFrame`` children, which
Alt+Tab cannot see. So Alt+Tab activates the *shell*, and Windows restores
focus to whatever HWND the shell last had -- which can be the shell itself, the
MDI client, or the child frame, none of which a listener can type into. The
shell had no ``EVT_ACTIVATE`` handler at all, so nothing moved focus on from
there.

Ctrl+F6 and Ctrl+Tab go through ``LiteApp.focus_frame``, which calls
``control.SetFocus()`` explicitly -- so switching documents once repaired what
Windows remembered, and the bug stopped happening for the rest of the session.
That is what made it "hard to reproduce" rather than intermittent: it is
deterministic, on a piece of state the reporter had already changed by the time
they went looking.

The guard matters as much as the fix. Focus is only moved when it is on a
container nobody can type into, or nowhere at all. A control the listener
actually moved to keeps it -- a Find box, a field they tabbed to, a dialog that
opened as the window came forward. Yanking focus back to the document from
those would be a worse bug, and a genuinely unpredictable one.

Nothing here announces. The screen reader announces a focus move itself
(GATE-13); saying so as well is the over-announcing that gate exists to stop.
"""

from __future__ import annotations

import pytest

from quill.apps.lite_shell import QuillLiteShell


class _Control:
    """Enough of the editor for the focus return to act on."""

    def __init__(self) -> None:
        self.focused = 0

    def SetFocus(self) -> None:  # noqa: N802 - wx spelling
        self.focused += 1


class _DyingControl(_Control):
    def SetFocus(self) -> None:  # noqa: N802 - wx spelling
        raise RuntimeError("wrapped C/C++ object has been deleted")


class _Child:
    def __init__(self, control: object | None) -> None:
        self.control = control


class _App:
    def __init__(self, active_frame: object | None = None) -> None:
        self.active_frame = active_frame


class _Client:
    """The MDI client window: a container, never a focus target."""


class _Shell:
    """A stand-in for the shell that the *shipped* methods are bound to.

    The methods under test are ``QuillLiteShell``'s own, called unbound against
    this object -- not reimplementations. Building a real ``wx.MDIParentFrame``
    would drag in a display and prove less.
    """

    def __init__(self, child: object | None, app: object | None = None) -> None:
        self._child = child
        self.app = app if app is not None else _App()
        self.client = _Client()

    def GetActiveChild(self):  # noqa: N802 - wx spelling
        return self._child

    def GetClientWindow(self):  # noqa: N802 - wx spelling
        return self.client

    def return_focus_to_document(self) -> None:
        return QuillLiteShell.return_focus_to_document(self)


def _return_focus(shell: _Shell, focused: object, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the shipped focus return with ``FindFocus`` answering *focused*."""
    import quill.apps.lite_shell as shell_module

    class _Window:
        @staticmethod
        def FindFocus():  # noqa: N802 - wx spelling
            return focused

    monkeypatch.setattr(shell_module.wx, "Window", _Window)
    QuillLiteShell.return_focus_to_document(shell)


# -- focus is on a container nobody can type into: move it to the document ----


def test_focus_left_on_the_shell_goes_to_the_document(monkeypatch) -> None:
    control = _Control()
    shell = _Shell(_Child(control))
    _return_focus(shell, shell, monkeypatch)
    assert control.focused == 1


def test_focus_left_on_the_mdi_client_goes_to_the_document(monkeypatch) -> None:
    # The window Alt+Tab most often leaves focus on: the client area that holds
    # the children, which is not itself a control.
    control = _Control()
    shell = _Shell(_Child(control))
    _return_focus(shell, shell.client, monkeypatch)
    assert control.focused == 1


def test_focus_left_on_the_child_frame_goes_to_the_document(monkeypatch) -> None:
    control = _Control()
    child = _Child(control)
    shell = _Shell(child)
    _return_focus(shell, child, monkeypatch)
    assert control.focused == 1


def test_focus_nowhere_at_all_goes_to_the_document(monkeypatch) -> None:
    # FindFocus answers None when the window that had focus has gone.
    control = _Control()
    shell = _Shell(_Child(control))
    _return_focus(shell, None, monkeypatch)
    assert control.focused == 1


# -- a real control keeps focus ----------------------------------------------


def test_a_control_the_listener_moved_to_keeps_focus(monkeypatch) -> None:
    """The guard: a Find box, a tabbed-to field, a dialog that just opened.

    Without this the fix would yank focus out of whatever a listener was using
    every time the window was activated -- including by the dialog itself.
    """
    control = _Control()
    shell = _Shell(_Child(control))
    find_box = object()
    _return_focus(shell, find_box, monkeypatch)
    assert control.focused == 0


# -- nothing to focus, and things on their way out ---------------------------


def test_no_active_child_falls_back_to_the_apps_active_frame(monkeypatch) -> None:
    """wxMSW can report no active child for a moment around activation.

    Giving up there is exactly the "sometimes it works" the report describes,
    so the app's own record of the active document answers instead.
    """
    control = _Control()
    shell = _Shell(None, app=_App(active_frame=_Child(control)))
    _return_focus(shell, shell, monkeypatch)
    assert control.focused == 1


def test_no_document_anywhere_does_nothing(monkeypatch) -> None:
    shell = _Shell(None, app=_App(active_frame=None))
    _return_focus(shell, shell, monkeypatch)  # must not raise


def test_a_document_on_its_way_out_never_raises(monkeypatch) -> None:
    # Activation can arrive while a child is being destroyed; the next one
    # focuses whatever replaces it.
    shell = _Shell(_Child(_DyingControl()))
    _return_focus(shell, shell, monkeypatch)  # must not raise


def test_a_shell_on_its_way_out_never_raises(monkeypatch) -> None:
    class _DyingShell(_Shell):
        def GetActiveChild(self):  # noqa: N802 - wx spelling
            raise RuntimeError("wrapped C/C++ object has been deleted")

    _return_focus(_DyingShell(None), None, monkeypatch)  # must not raise


# -- the activation handler itself -------------------------------------------


class _Event:
    def __init__(self, active: bool) -> None:
        self._active = active
        self.skipped = 0

    def GetActive(self) -> bool:  # noqa: N802 - wx spelling
        return self._active

    def Skip(self) -> None:  # noqa: N802 - wx spelling
        self.skipped += 1


def _activate(shell: object, event: _Event, monkeypatch: pytest.MonkeyPatch) -> list:
    import quill.apps.lite_shell as shell_module

    deferred: list = []
    monkeypatch.setattr(shell_module.wx, "CallAfter", lambda fn, *a: deferred.append(fn))
    QuillLiteShell._on_activate(shell, event)
    return deferred


def test_activation_defers_the_focus_return(monkeypatch) -> None:
    """CallAfter, not a direct call.

    The handler runs before Windows has finished restoring its own focus, so
    focus set here is overwritten a moment later -- which is what makes this
    class of bug look random rather than absent.
    """
    shell = _Shell(_Child(_Control()))
    event = _Event(active=True)
    deferred = _activate(shell, event, monkeypatch)
    assert len(deferred) == 1
    assert event.skipped == 1


def test_leaving_the_app_focuses_nothing(monkeypatch) -> None:
    event = _Event(active=False)
    deferred = _activate(_Shell(_Child(_Control())), event, monkeypatch)
    assert deferred == []
    assert event.skipped == 1


@pytest.mark.parametrize("interruption", ["none", "find", "menu", "deactivate", "close"])
def test_bounded_second_check_preserves_new_interaction(monkeypatch, interruption) -> None:
    import quill.apps.lite_shell as shell_module

    class Control(_Control):
        def SetFocus(self):  # noqa: N802
            super().SetFocus()
            current[0] = self

    control = Control()
    shell = _Shell(_Child(control))
    current = [shell]
    delayed = []
    monkeypatch.setattr(
        shell_module.wx,
        "Window",
        type("Window", (), {"FindFocus": staticmethod(lambda: current[0])}),
    )
    monkeypatch.setattr(shell_module.wx, "CallLater", lambda delay, fn: delayed.append((delay, fn)))
    queued = _activate(shell, _Event(True), monkeypatch)
    queued[0]()
    assert control.focused == 1
    assert len(delayed) == 1
    current[0] = shell
    if interruption == "find":
        current[0] = object()
    elif interruption == "menu":
        shell._menu_open = True
    elif interruption == "deactivate":
        _activate(shell, _Event(False), monkeypatch)
    elif interruption == "close":
        shell.app.shutting_down = True
    assert delayed[0][0] == 75
    delayed[0][1]()
    assert control.focused == (2 if interruption == "none" else 1)
    assert len(delayed) == 1


def test_old_activation_cannot_repair_new_activation(monkeypatch) -> None:
    control = _Control()
    shell = _Shell(_Child(control))
    first = _activate(shell, _Event(True), monkeypatch)
    _activate(shell, _Event(False), monkeypatch)
    _activate(shell, _Event(True), monkeypatch)
    first[0]()
    assert control.focused == 0


@pytest.mark.parametrize("predicate", ["IsActive", "IsShownOnScreen"])
def test_inactive_or_hidden_shell_never_repairs_focus(monkeypatch, predicate) -> None:
    control = _Control()
    shell = _Shell(_Child(control))
    setattr(shell, predicate, lambda: False)
    _return_focus(shell, shell, monkeypatch)
    assert control.focused == 0


@pytest.mark.machine_global
def test_live_mdi_container_repair_preserves_text_field_focus() -> None:
    from types import SimpleNamespace

    import wx

    application = wx.GetApp() or wx.App(False)
    owner = SimpleNamespace(shutting_down=False, active_frame=None)
    shell = QuillLiteShell(owner, (500, 300))
    child = wx.MDIChildFrame(shell, title="Focus regression document")
    child.control = wx.TextCtrl(child, value="Document", style=wx.TE_MULTILINE)
    find = wx.TextCtrl(child, value="Find")
    layout = wx.BoxSizer(wx.VERTICAL)
    layout.Add(child.control, 1, wx.EXPAND)
    layout.Add(find, 0, wx.EXPAND)
    child.SetSizer(layout)
    owner.active_frame = child
    try:
        shell.Show()
        child.Show()
        child.Activate()
        shell.Raise()
        application.Yield()
        shell._activation_active = True
        for _cycle in range(5):
            shell.GetClientWindow().SetFocus()
            application.Yield()
            shell.return_focus_to_document()
            application.Yield()
            assert wx.Window.FindFocus() is child.control
            find.SetFocus()
            application.Yield()
            shell.return_focus_to_document()
            assert wx.Window.FindFocus() is find
    finally:
        shell.Destroy()
        application.Yield()


def test_activation_never_takes_the_process_down(monkeypatch) -> None:
    """An exception escaping native activation dispatch crashes the app.

    QUILL learned this at #956; returning focus is a convenience and is never
    worth the process.
    """

    class _BadEvent(_Event):
        def GetActive(self) -> bool:  # noqa: N802 - wx spelling
            raise RuntimeError("activation mid-teardown")

    event = _BadEvent(active=True)
    deferred = _activate(_Shell(None), event, monkeypatch)
    assert deferred == []
    assert event.skipped == 1
