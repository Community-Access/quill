"""Tests for the ContextHelpMixin show_control_help dialog contract."""

from __future__ import annotations


def test_show_control_help_uses_show_modal_dialog(monkeypatch) -> None:
    import types

    from quill.ui.context_help import ContextHelpMixin

    # Minimal stand-in for wx.
    fake_wx = types.ModuleType("wx")
    fake_wx.ID_OK = 5100  # type: ignore[attr-defined]
    fake_wx.ID_HELP = 5199  # type: ignore[attr-defined]
    fake_wx.DEFAULT_DIALOG_STYLE = 0  # type: ignore[attr-defined]
    fake_wx.RESIZE_BORDER = 0  # type: ignore[attr-defined]

    modal_calls: list[tuple[object, str]] = []

    class _FakeDialog:
        def __init__(self, *_args, **_kwargs):
            pass

        def ShowModal(self):
            raise AssertionError("ShowModal must not be called directly")

        def Destroy(self):
            pass

    class _FakeMixin(ContextHelpMixin):
        _last_focused_ctrl = None

        def __init__(self):
            self._modal_calls = modal_calls

        def _show_modal_dialog(self, dlg, label, **_kw):
            modal_calls.append((dlg, label))
            return fake_wx.ID_OK

    # Patch ContextHelpDialog so no wx is needed.
    import quill.ui.context_help as ch_mod

    monkeypatch.setattr(ch_mod, "ContextHelpDialog", _FakeDialog)
    # Patch describe_focused to return minimal topics.
    from quill.core.help import HelpTopic

    monkeypatch.setattr(
        ch_mod,
        "describe_focused",
        lambda _ctrl: (None, HelpTopic(id="test", title="Test Control", body="body")),
    )

    import wx as real_wx

    monkeypatch.setattr(real_wx.Window, "FindFocus", staticmethod(lambda: None))

    mixin = _FakeMixin()
    mixin.show_control_help()

    assert len(modal_calls) == 1
    assert modal_calls[0][1] == "Context Help"


def test_warm_help_topics_is_idempotent(monkeypatch) -> None:
    """#179: ``warm_help_topics`` must be safe to call repeatedly; the first
    call decodes ``topics.json`` and subsequent calls short-circuit."""
    import quill.ui.context_help as ch_mod

    calls: list[int] = []

    class _Renderer:
        def get(self, topic_id: str):
            return None

    class _FakeHelpRenderer:
        @staticmethod
        def from_file() -> _Renderer:
            calls.append(1)
            return _Renderer()

    monkeypatch.setattr(ch_mod, "HelpRenderer", _FakeHelpRenderer)
    # Reset the module-level cache so each test runs in isolation.
    monkeypatch.setattr(ch_mod, "_renderer", None)

    assert ch_mod.warm_help_topics() is True
    assert ch_mod.warm_help_topics() is True
    assert ch_mod.warm_help_topics() is True
    # HelpRenderer.from_file() must be called exactly once even though
    # warm_help_topics is called three times.
    assert len(calls) == 1


def test_warm_help_topics_swallows_exceptions(monkeypatch) -> None:
    """A corrupt ``topics.json`` must not break startup; warm_help_topics
    returns ``False`` and the renderer lazy-loads on first F1."""
    import quill.ui.context_help as ch_mod

    def _boom() -> None:
        raise OSError("topics.json corrupt")

    class _FakeHelpRenderer:
        from_file = staticmethod(_boom)

    monkeypatch.setattr(ch_mod, "HelpRenderer", _FakeHelpRenderer)
    monkeypatch.setattr(ch_mod, "_renderer", None)

    assert ch_mod.warm_help_topics() is False
