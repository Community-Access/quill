"""More Dictation Settings, and OpenAI's consent in Dictation Settings."""

from __future__ import annotations

from typing import Any

import pytest

from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")


@pytest.fixture(scope="module")
def wx_app():
    app = shared_wx_app()
    yield app


class _Settings:
    pass


def _dialog(**kwargs: Any) -> Any:
    from quill.ui.dictation_more_dialog import MoreDictationDialog

    said: list[str] = []
    dialog = MoreDictationDialog(None, _Settings(), said.append, load_models=False, **kwargs)
    return dialog, said


def test_the_defaults_and_every_choice_come_back_under_the_settings_names(wx_app) -> None:
    dialog, _said = _dialog()
    try:
        values = dialog.values()
        assert values["windows_dictation_hold_to_talk"] is False
        assert values["windows_dictation_preview"] == "show"
        assert values["windows_dictation_ai_send"] == "pause"
        assert values["windows_dictation_ai_pause"] == "long"
        assert values["windows_dictation_openai_consent"] is False
        dialog.hold.SetValue(True)
        dialog.preview.SetSelection(1)
        dialog.send.SetSelection(1)
        dialog.consent.SetValue(True)
        values = dialog.values()
        assert values["windows_dictation_hold_to_talk"] is True
        assert values["windows_dictation_preview"] == "speak"
        assert values["windows_dictation_ai_send"] == "enter"
        assert values["windows_dictation_openai_consent"] is True
    finally:
        dialog.Destroy()


def test_the_working_tick_is_a_choice_here_off_unless_saved_on(wx_app) -> None:
    """D-17: the editors default it off; QUILL Transcribe's settings say on."""
    dialog, _said = _dialog()
    try:
        assert dialog.values()["windows_dictation_working_tick"] is False
        dialog.working_tick.SetValue(True)
        assert dialog.values()["windows_dictation_working_tick"] is True
    finally:
        dialog.Destroy()
    from quill.core.transcribe.settings import TRANSCRIBE_DICTATION_DEFAULTS
    from quill.core.windows_dictation.anywhere import settings_from
    from quill.ui.dictation_more_dialog import MoreDictationDialog

    transcribe = settings_from(dict(TRANSCRIBE_DICTATION_DEFAULTS))
    dialog = MoreDictationDialog(None, transcribe, None, load_models=False)
    try:
        assert dialog.working_tick.GetValue() is True
    finally:
        dialog.Destroy()


def test_the_newest_model_is_preselected_from_openais_list(wx_app) -> None:
    dialog, said = _dialog()
    try:
        dialog.show_models(["gpt-live-transcribe", "gpt-transcribe"], "")
        assert dialog.values()["windows_dictation_openai_model"] == "gpt-live-transcribe"
        assert "2 speech models" in dialog.model_status.GetValue()
        assert said == []
    finally:
        dialog.Destroy()


def test_a_chosen_model_that_went_away_is_said_once_and_not_replaced(wx_app) -> None:
    dialog, said = _dialog(pending={"windows_dictation_openai_model": "gpt-4o-transcribe"})
    try:
        dialog.show_models(["gpt-live-transcribe", "gpt-transcribe"], "")
        assert len(said) == 1 and "gpt-4o-transcribe" in said[0]
        assert dialog.model.GetSelection() == wx.NOT_FOUND
        assert dialog.values()["windows_dictation_openai_model"] == ""  # never a silent switch
        dialog.model.SetSelection(1)
        assert dialog.values()["windows_dictation_openai_model"] == "gpt-transcribe"
    finally:
        dialog.Destroy()


def test_a_list_that_could_not_be_read_says_why(wx_app) -> None:
    dialog, _said = _dialog()
    try:
        dialog.show_models([], "OpenAI could not be reached. Check the internet connection.")
        assert "could not be reached" in dialog.model_status.GetValue()
    finally:
        dialog.Destroy()


def test_choosing_openai_asks_first_and_no_puts_the_engine_back(wx_app, monkeypatch) -> None:
    from quill.core.windows_dictation import engines, openai_models
    from quill.ui import windows_dictation_dialog as module

    monkeypatch.setattr(openai_models, "cloud_problem", lambda **_k: "")
    monkeypatch.setattr(
        engines,
        "engine_choices",
        lambda saved="": [("moonshine", "Moonshine"), ("openai", "OpenAI")],
    )
    monkeypatch.setattr(module, "engine_choices", engines.engine_choices)
    asked: list[str] = []
    answers = iter([wx.NO, wx.YES])
    monkeypatch.setattr(
        module, "show_message_box", lambda text, *_a, **_k: asked.append(text) or next(answers)
    )
    opened: list[bool] = []
    said: list[str] = []
    dialog = module.WindowsDictationDialog(None, _Settings(), said.append)
    monkeypatch.setattr(dialog, "open_more", lambda **kwargs: opened.append(kwargs["focus_model"]))
    try:
        dialog.engine.SetSelection(1)
        dialog._on_engine(None)
        assert "sends what you say to OpenAI" in asked[0]
        assert dialog.engine.GetSelection() == 0 and "Nothing was sent" in said[-1]
        dialog.engine.SetSelection(1)
        dialog._on_engine(None)
        assert opened == [True]
        settings = _Settings()
        dialog.apply(settings)
        assert settings.windows_dictation_engine == "openai"
        assert settings.windows_dictation_openai_consent is True
    finally:
        dialog.Destroy()


def test_more_dictation_settings_is_reachable_from_dictation_settings(wx_app) -> None:
    from quill.ui.windows_dictation_dialog import WindowsDictationDialog

    dialog = WindowsDictationDialog(None, _Settings())
    try:
        assert dialog.more_button.GetLabel() == "More Dict&ation Settings..."
    finally:
        dialog.Destroy()


def test_the_command_word_strict_mode_and_timeout_are_here(wx_app, monkeypatch) -> None:
    """D-1: the command word, strict mode (on in QUILL Transcribe, off in the
    editors) and command mode's timeout, under the shared settings' names; OK
    is refused, with the reason, for a common word or one of My Words."""
    import quill.ui.dialog_contract as contract

    dialog, _said = _dialog(my_words=["Kubernetes"])
    shown: list[str] = []
    monkeypatch.setattr(contract, "show_message_box", lambda text, *_a, **_k: shown.append(text))
    try:
        values = dialog.values()
        assert values["windows_dictation_command_prefix"] == "QUILL"
        assert values["windows_dictation_command_prefix_required"] is False
        assert values["windows_dictation_command_timeout"] == 8
        dialog.command_prefix.SetValue("  Jarvis ")
        dialog.command_required.SetValue(True)
        dialog.command_timeout.SetValue(20)
        values = dialog.values()
        assert values["windows_dictation_command_prefix"] == "Jarvis"
        assert values["windows_dictation_command_prefix_required"] is True
        assert values["windows_dictation_command_timeout"] == 20
        assert dialog.command_word_problem() == ""
        dialog.command_prefix.SetValue("Kubernetes")
        assert "My Words" in dialog.command_word_problem()

        class _Event:
            skipped = False

            def Skip(self) -> None:  # noqa: N802
                self.skipped = True

        event = _Event()
        dialog._on_ok(event)
        assert not event.skipped and shown and "My Words" in shown[0]
        dialog.command_prefix.SetValue("QUILL")
        event = _Event()
        dialog._on_ok(event)
        assert event.skipped
    finally:
        dialog.Destroy()
    from quill.core.transcribe.settings import TRANSCRIBE_DICTATION_DEFAULTS
    from quill.core.windows_dictation.anywhere import settings_from
    from quill.ui.dictation_more_dialog import MoreDictationDialog

    transcribe = settings_from(dict(TRANSCRIBE_DICTATION_DEFAULTS))
    dialog = MoreDictationDialog(None, transcribe, None, load_models=False)
    try:
        assert dialog.command_required.GetValue() is True
    finally:
        dialog.Destroy()


def test_the_buttons_that_close_the_window_check_the_command_word_too(wx_app, monkeypatch) -> None:
    """Add or Change OpenAI Key, My Dictation Instructions and Dictate in Other
    Programs close this window and its values are saved, so a refused word was
    saved through them until 2026-10-15 -- and then every phrase that started
    with it typed nothing. They pass the same check as OK now."""
    import quill.ui.dialog_contract as contract
    from quill.ui.dictation_more_dialog import (
        DICTATE_ANYWHERE,
        EDIT_INSTRUCTIONS,
        EDIT_OPENAI_KEY,
    )

    dialog, _said = _dialog()
    shown: list[str] = []
    ended: list[int] = []
    monkeypatch.setattr(contract, "show_message_box", lambda text, *_a, **_k: shown.append(text))
    monkeypatch.setattr(dialog, "EndModal", ended.append)
    try:
        dialog.command_prefix.SetValue("the")
        for code in (EDIT_OPENAI_KEY, EDIT_INSTRUCTIONS, DICTATE_ANYWHERE):
            dialog._end_if_ready(code)
        assert ended == [] and len(shown) == 3
        dialog.command_prefix.SetValue("QUILL")
        dialog._end_if_ready(DICTATE_ANYWHERE)
        assert ended == [DICTATE_ANYWHERE]
    finally:
        dialog.Destroy()


# -- a host with no Review Dictation (Quill Inkwell, 2026-10-17) ----------------- #


class _Polishing:
    windows_dictation_polish = True
    windows_dictation_review_first = False


def _mnemonics(dialog: Any) -> list[str]:
    keys = []
    for child in dialog.GetChildren():
        label = child.GetLabel() if hasattr(child, "GetLabel") else ""
        if "&" in label.replace("&&", ""):
            keys.append(label[label.index("&") + 1].lower())
    return keys


def test_the_polishing_box_is_shown_where_review_dictation_exists(wx_app) -> None:
    dialog, _said = _dialog()
    try:
        assert dialog.polish is not None and dialog.polish.IsShown()
        assert dialog.values()["windows_dictation_polish"] is False
    finally:
        dialog.Destroy()


def test_without_review_dictation_the_box_is_gone_and_the_choice_is_kept(wx_app) -> None:
    from quill.ui.dictation_more_dialog import MoreDictationDialog

    dialog = MoreDictationDialog(None, _Polishing(), None, load_models=False, review=False)
    try:
        assert dialog.polish is None
        labels = [child.GetLabel() for child in dialog.GetChildren()]
        assert not any("polish" in label.lower() for label in labels)
        assert "windows_dictation_polish" not in dialog.values()  # left as saved
        # todo 55: Send dictation to review first goes the same way.
        assert dialog.review_first is None
        assert not any("review" in label.lower() for label in labels)
        assert "windows_dictation_review_first" not in dialog.values()
        keys = _mnemonics(dialog)
        assert len(keys) == len(set(keys))  # GATE-14 in this host too
    finally:
        dialog.Destroy()
    shown, _said = _dialog()
    try:
        keys = _mnemonics(shown)
        assert len(keys) == len(set(keys)) and "g" in keys and "v" in keys
        assert shown.review_first is not None and shown.review_first.IsShown()
        assert "windows_dictation_review_first" in shown.values()
    finally:
        shown.Destroy()


def test_inkwell_keeps_a_saved_review_first_choice(wx_app) -> None:
    """Inkwell's OK in Dictation Settings never writes review-first, whatever
    style is chosen: QUILL's True stays True (todo 55)."""
    from quill.ui.windows_dictation_dialog import WindowsDictationDialog

    class _Reviewing(_Polishing):
        windows_dictation_review_first = True

    for style in ("verbatim", "clean"):
        dialog = WindowsDictationDialog(None, _Reviewing(), review=False)
        try:
            dialog.style.SetSelection(dialog._styles.index(style))
            dialog._on_style(None)
            settings = _Reviewing()
            dialog.apply(settings)
            assert settings.windows_dictation_review_first is True
        finally:
            dialog.Destroy()


def test_inkwell_styles_never_touch_polishing(wx_app) -> None:
    from quill.ui.windows_dictation_dialog import WindowsDictationDialog

    dialog = WindowsDictationDialog(None, _Polishing(), review=False)
    try:
        dialog.style.SetSelection(dialog._styles.index("clean"))
        dialog._on_style(None)
        assert dialog._styles[dialog.style.GetSelection()] == "clean"
        settings = _Polishing()
        dialog.apply(settings)
        assert settings.windows_dictation_polish is True  # as QUILL left it
        assert settings.windows_dictation_self_repair is True
    finally:
        dialog.Destroy()
    editors = WindowsDictationDialog(None, _Polishing())
    try:
        editors.style.SetSelection(editors._styles.index("clean"))
        editors._on_style(None)
        settings = _Polishing()
        editors.apply(settings)
        assert settings.windows_dictation_polish is False  # Clean turns it off there
    finally:
        editors.Destroy()


def test_inkwell_opens_dictation_settings_without_review(monkeypatch) -> None:
    import quill.ui.windows_dictation_dialog as module
    from quill.apps.inkwell_dictation import InkwellDictationMixin

    seen: dict[str, Any] = {}

    class _Stop(Exception):
        pass

    def _record(*_args: Any, **kwargs: Any) -> Any:
        seen.update(kwargs)
        raise _Stop

    class _Host(InkwellDictationMixin):
        frame = None

        def _anywhere_settings(self) -> Any:
            return _Settings()

        def _announce(self, _text: str) -> None:
            pass

    monkeypatch.setattr(module, "WindowsDictationDialog", _record)
    with pytest.raises(_Stop):
        _Host().edit_anywhere_settings()
    assert seen.get("review") is False
