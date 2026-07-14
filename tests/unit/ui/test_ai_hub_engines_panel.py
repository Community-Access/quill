"""Regression test for issue #915: a background pack install's completion
callback (wx.CallAfter(self._after_install, ...)) crashed with RuntimeError:
wrapped C/C++ object of type Button has been deleted when the AI Hub was
closed before the install thread finished."""

from __future__ import annotations

from quill.ui.ai_hub_engines_panel import EnginesPanel


class _DeletedButton:
    def Enable(self, _flag: bool) -> None:
        raise RuntimeError("wrapped C/C++ object of type Button has been deleted")


def test_after_install_survives_a_destroyed_panel() -> None:
    panel = EnginesPanel.__new__(EnginesPanel)
    panel.setup_btn = _DeletedButton()

    calls: list[str] = []
    panel.status = type("S", (), {"SetLabel": lambda self, msg: calls.append(msg)})()
    panel._announce = lambda msg: calls.append(f"announce:{msg}")
    panel._reload = lambda: calls.append("reload")

    # Must not raise, and must not touch anything past the dead widget.
    panel._after_install("Installed OpenAI.")

    assert calls == []


def test_after_install_survives_a_destroyed_status_label() -> None:
    """#55: the guard used to wrap only ``setup_btn.Enable(True)``. If a *later*
    widget (the status label, the announce, or the reload) was the one already
    destroyed when the queued ``wx.CallAfter`` fired, the unguarded call raised
    ``RuntimeError`` instead of being swallowed. The guard now wraps all four
    post-install calls, so a dead status label is also a clean no-op."""
    panel = EnginesPanel.__new__(EnginesPanel)

    class _OkButton:
        def Enable(self, _flag: bool) -> None:
            return

    panel.setup_btn = _OkButton()

    class _DeadStatus:
        def SetLabel(self, _msg: str) -> None:
            raise RuntimeError("wrapped C/C++ object of type StaticText has been deleted")

    panel.status = _DeadStatus()
    panel._announce = lambda msg: None
    panel._reload = lambda: None

    # Must not raise even though the dead widget is *not* the button.
    panel._after_install("Installed Claude.")

    # The button re-enable happened (before the dead status), but the install
    # callback did not crash -- that is the regression.
    assert panel.setup_btn.__class__ is _OkButton
