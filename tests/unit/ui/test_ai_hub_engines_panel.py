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
