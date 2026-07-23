"""QUILL's Tools > Companion Apps launchers: open_companion_app hands off to the
sibling-app launcher and announces success or an honest failure, never raising."""

from __future__ import annotations

from quill.ui.main_frame_menu_bindings import MenuBindingsMixin


class _Host(MenuBindingsMixin):
    def __init__(self) -> None:
        self.said: list[str] = []

    def _announce(self, message: str, *, force: bool = False) -> None:
        self.said.append(message)


def test_open_companion_app_launches_and_announces(monkeypatch) -> None:
    import quill.core.app_launcher as launcher

    calls: list[str] = []
    monkeypatch.setattr(launcher, "launch_app", lambda key, **_k: calls.append(key) or True)
    host = _Host()
    host.open_companion_app("weather")
    assert calls == ["weather"]
    assert host.said == ["Opening Quill Weather."]


def test_open_companion_app_reports_failure(monkeypatch) -> None:
    import quill.core.app_launcher as launcher

    monkeypatch.setattr(launcher, "launch_app", lambda key, **_k: False)
    host = _Host()
    host.open_companion_app("radio")
    assert "could not be opened" in host.said[0]
    assert "Quill Radio" in host.said[0]
