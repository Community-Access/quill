"""F1 in the windows that arrived in 2026-10: purpose first, then the control.

Each window is built for real, shown through the path the app uses (the dialog
contract binds F1 there), and sent a real F1. The answer must open with the
window's *authored* purpose -- not the generic paragraph -- and carry the
focused control's own ``SetHelpText``.

Why each check is here:

* The release-channel windows are ``wx.Dialog`` subclasses titled by a
  builder, so the help audit could not see their titles until it learned
  ``super().__init__(title=...)`` -- and in QUILL itself they answered F1 with
  the generic paragraph, because QUILL registered no purpose resolver.
* The dictation and hosted-AI windows are shared by QUILL and QUILL Lite;
  neither catalogue knew "Dictation Settings", "AI Conversation" or ten of the
  writing tools' result titles.
* "Key for <command>" was catalogued as an exact "Key for", which no real
  title equals.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core import control_help, lite_surface_help  # noqa: E402
from quill.core.updater.profiles import PROFILES  # noqa: E402
from quill.core.updater.wording import window_titles  # noqa: E402
from quill.ui import app_context_help, dialog_contract  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    app_context_help.ensure_help_provider(wx)
    yield app
    app.Destroy()


@pytest.fixture(autouse=True)
def _reset():
    yield
    dialog_contract.set_context_help_handler(None)
    app_context_help._purpose_resolver = None


def _resolvers() -> dict[str, Any]:
    from quill.core.podcasts import surface_help as cast
    from quill.core.radio import surface_help as radio
    from quill.ui.context_help import quill_window_purpose

    return {
        "quill": quill_window_purpose,
        "quilllite": lite_surface_help.purpose_for_title,
        "radio": radio.purpose_for_title,
        "cast": cast.purpose_for_title,
    }


@pytest.mark.parametrize("app_key", sorted(PROFILES))
def test_every_channel_window_has_its_purpose_in_every_app(app_key: str) -> None:
    resolve = _resolvers()[app_key]
    for title, purpose in window_titles(PROFILES[app_key].display_name).items():
        assert resolve(title) == purpose, f"{app_key}: F1 in {title!r} is not its purpose"


def test_quill_answers_the_shared_windows_and_nothing_else() -> None:
    from quill.ui.context_help import quill_window_purpose

    for title in lite_surface_help.SHARED_WITH_QUILL:
        assert quill_window_purpose(title) == lite_surface_help.PURPOSES[title], title
        assert "QUILL Lite" not in quill_window_purpose(title), (
            f"{title!r} is shown in QUILL too; its paragraph must not name QUILL Lite"
        )
    # QUILL's own windows keep their own help: a Lite paragraph for "Find" or
    # "Preferences" would describe the wrong editor.
    assert quill_window_purpose("Find") == ""
    assert quill_window_purpose("Preferences") == ""


def test_every_writing_tool_result_window_has_a_purpose() -> None:
    from quill.core.ai.writing_tools import ACTION_TITLES

    for title in ACTION_TITLES.values():
        assert lite_surface_help.is_known_title(title), title


def test_key_for_windows_are_matched_by_prefix() -> None:
    assert lite_surface_help.purpose_for_title("Key for Bold") != lite_surface_help.GENERIC_PURPOSE


# -- built windows, real F1 -------------------------------------------------------


def _press_f1_and_read(window: Any, control: Any, monkeypatch) -> tuple[Any, Any]:
    """Send F1 to *window* with *control* focused; return the composed topics."""
    answers: list[tuple[Any, Any]] = []
    dialog_contract.set_context_help_handler(
        lambda w: answers.append(app_context_help.topics_for(w, wx))
    )
    dialog_contract._install_context_help(window)
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: control))
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetEventObject(window)
    event.SetKeyCode(wx.WXK_F1)
    window.GetEventHandler().ProcessEvent(event)
    assert len(answers) == 1, "F1 did not reach the help handler"
    return answers[0]


def _assert_answer(window, control, monkeypatch, resolver) -> None:
    app_context_help._purpose_resolver = resolver
    surface, ctrl = _press_f1_and_read(window, control, monkeypatch)
    assert surface.title == window.GetTitle()
    assert surface.body == resolver(window.GetTitle())
    assert surface.body != control_help.GENERIC_PURPOSE
    assert control.GetHelpText(), "the control has no authored help"
    assert control.GetHelpText() in ctrl.body


def _channel_dialogs(app_name: str):
    from quill.core.updater.channels import ChannelState
    from quill.core.updater.switch import RiskContext, SwitchRequest, plan_switch
    from quill.ui.updates.channel_risk_dialog import RiskDialog
    from quill.ui.updates.release_channel_dialog import ReleaseChannelDialog
    from quill.ui.updates.update_history_dialog import UpdateHistoryDialog

    chooser = ReleaseChannelDialog(
        None,
        app_name=app_name,
        state=ChannelState(),
        siblings=[],
        describe=lambda target, also: plan_switch(
            SwitchRequest("quill", target, "1.0.0", also),  # type: ignore[arg-type]
            states={},
        ),
        show_history=lambda: None,
    )
    yield chooser, chooser._choices
    history = UpdateHistoryDialog(None, app_name=app_name, events=[])
    yield history, history._list
    risk = RiskDialog(
        None,
        RiskContext(
            app_key="radio",
            display_name=app_name,
            target="beta",  # type: ignore[arg-type]
            also_moving=(),
            snapshot_covers="your settings",
            snapshot_leaves="Nothing else is copied.",
            uses_shared_runtime=False,
        ),
        announce=lambda _text: None,
    )
    buttons = [c for c in risk.GetChildren() if isinstance(c, wx.Button)]
    yield risk, buttons[0]


@pytest.mark.parametrize("app_key", sorted(PROFILES))
def test_release_channel_windows_answer_f1(wx_app, monkeypatch, tmp_path, app_key) -> None:
    monkeypatch.setenv("QUILL_FAMILY_DIR", str(tmp_path / "QuillVille"))
    resolver = _resolvers()[app_key]
    seen = 0
    for window, control in _channel_dialogs(PROFILES[app_key].display_name):
        try:
            _assert_answer(window, control, monkeypatch, resolver)
            seen += 1
        finally:
            window.Destroy()
    assert seen == 3


@pytest.mark.parametrize("app_key", ["quill", "quilllite"])
def test_dictation_windows_answer_f1(wx_app, monkeypatch, app_key) -> None:
    from quill.ui.windows_dictation_dialog import (
        DictationCommandsDialog,
        RecentPhrasesDialog,
        WindowsDictationDialog,
    )

    resolver = _resolvers()[app_key]
    settings = WindowsDictationDialog(None, SimpleNamespace())
    commands = DictationCommandsDialog(None, "new paragraph: starts a new paragraph")
    recent = RecentPhrasesDialog(None, ["hello there"])
    for window, control in (
        (settings, settings.speech_language),
        (commands, commands.text),
        (recent, recent.list),
    ):
        try:
            _assert_answer(window, control, monkeypatch, resolver)
        finally:
            window.Destroy()


def test_youtube_video_window_answers_f1(wx_app, monkeypatch) -> None:
    from quill.core.radio import surface_help
    from quill.ui.radio.youtube_video_window import YouTubeVideoWindow

    host = SimpleNamespace(_announce=lambda _text: None, _task_manager=None)
    station = SimpleNamespace(display_name="A walk through Bristol")
    window = YouTubeVideoWindow(
        None, host=host, station=station, page_url="https://www.youtube.com/watch?v=abcdefghijk"
    )
    try:
        dialog_contract.show_modeless_surface(window.frame, window.frame.GetTitle())
        _assert_answer(window.frame, window._moments, monkeypatch, surface_help.purpose_for_title)
    finally:
        window.frame.Destroy()


def test_youtube_live_chat_window_answers_f1(wx_app, monkeypatch) -> None:
    from quill.core.radio import surface_help
    from quill.ui.radio.youtube_live_chat_window import YouTubeLiveChatWindow

    class _Reader:
        def start(self) -> None:
            pass

        def stop(self, timeout: float = 0) -> None:
            pass

        def drain(self, limit: int = 500) -> list:
            return []

    window = YouTubeLiveChatWindow(
        None,
        video_title="A stream",
        page_url="https://www.youtube.com/watch?v=abcdefghijk",
        announce=lambda _text: None,
        reader=_Reader(),
        can_send=False,
        send=None,
    )
    try:
        dialog_contract.show_modeless_surface(window.frame, window.frame.GetTitle())
        _assert_answer(window.frame, window._list, monkeypatch, surface_help.purpose_for_title)
    finally:
        window._timer.Stop()
        window.frame.Destroy()
