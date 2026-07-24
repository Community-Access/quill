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


class _Wx:
    YES_NO = 1
    ICON_QUESTION = 2
    ICON_INFORMATION = 4
    YES = 100
    NO = 101


class _OfferHost(MenuBindingsMixin):
    def __init__(self, answer: int) -> None:
        self.said: list[str] = []
        self.prompts: list[str] = []
        self.submitted: list[str] = []
        self._wx = _Wx()
        self._answer = answer

    def _announce(self, message: str, *, force: bool = False) -> None:
        self.said.append(message)

    def _show_message_box(self, message: str, caption: str, style: int) -> int:
        self.prompts.append(message)
        return self._answer

    class _TM:
        def __init__(self, outer: _OfferHost) -> None:
            self._outer = outer

        def submit(self, name, work, *, on_success=None, on_failure=None):  # noqa: ANN001
            self._outer.submitted.append(name)

    @property
    def _task_manager(self):  # noqa: ANN202
        return _OfferHost._TM(self)


def test_offer_download_when_frozen_and_missing_asks_and_submits(monkeypatch) -> None:
    import quill.core.app_launcher as launcher
    import quill.core.companion_install as ci

    monkeypatch.setattr(launcher, "launch_app", lambda key, **_k: False)
    monkeypatch.setattr(ci, "can_offer_download", lambda key: True)  # pretend frozen
    host = _OfferHost(answer=_Wx.YES)
    host.open_companion_app("weather")
    assert any("isn't installed yet" in p for p in host.prompts)  # the gentle ask
    assert host.submitted == ["companion-install"]  # download kicked off


def test_offer_download_declined_is_gentle(monkeypatch) -> None:
    import quill.core.app_launcher as launcher
    import quill.core.companion_install as ci

    monkeypatch.setattr(launcher, "launch_app", lambda key, **_k: False)
    monkeypatch.setattr(ci, "can_offer_download", lambda key: True)
    host = _OfferHost(answer=_Wx.NO)
    host.open_companion_app("weather")
    assert host.submitted == []  # nothing downloaded
    assert any("any time from this menu" in s for s in host.said)
