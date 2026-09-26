"""Dictation Settings: the finer choices save, and Test Microphone reports."""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app


class _Settings:
    pass


def _run_now(name, work, *, on_success, on_failure):
    try:
        result = work()
    except Exception as error:  # noqa: BLE001 - handed on, as the worker would
        on_failure(name, error)
        return
    on_success(name, result)


def test_the_finer_choices_are_written_on_apply(wx_app) -> None:
    from quill.ui.windows_dictation_dialog import WindowsDictationDialog

    dialog = WindowsDictationDialog(None, _Settings())
    try:
        dialog.pause.SetSelection(2)
        dialog.silence.SetSelection(2)
        dialog.remove_fillers.SetValue(True)
        dialog.auto_punctuation.SetValue(False)
        dialog.continuous.SetValue(True)
        settings = _Settings()
        dialog.apply(settings)
        assert settings.windows_dictation_pause == "long"
        assert settings.windows_dictation_silence_minutes == 5
        assert settings.windows_dictation_remove_fillers is True
        assert settings.windows_dictation_auto_punctuation is False
        assert settings.windows_dictation_continuous is True
    finally:
        dialog.Destroy()


def test_the_window_fits_a_small_screen(wx_app) -> None:
    from quill.ui.windows_dictation_dialog import WindowsDictationDialog

    dialog = WindowsDictationDialog(None, _Settings())
    try:
        assert dialog.GetSize().height <= 700
    finally:
        dialog.Destroy()


def test_test_microphone_says_speak_now_then_what_it_heard(wx_app, monkeypatch) -> None:
    import quill.core.windows_dictation.local_recognizer as local
    import quill.ui.update_download as download
    from quill.ui.windows_dictation_dialog import WindowsDictationDialog

    monkeypatch.setattr(local, "record_and_hear", lambda _mic, _engine: (0.5, "hello there"))
    monkeypatch.setattr(download, "thread_submit", _run_now)
    monkeypatch.setattr(wx, "CallAfter", lambda fn, *args: fn(*args))
    said: list[str] = []
    dialog = WindowsDictationDialog(None, _Settings(), said.append)
    try:
        dialog._on_test_microphone(None)
        assert said[0] == "Speak now. Recording for four seconds."
        expected = 'The microphone is working: sound reached 50 percent. It heard: "hello there".'
        assert said[-1] == expected
        assert dialog.test_result.GetValue() == expected
        assert dialog.test_microphone.IsEnabled()
    finally:
        dialog.Destroy()


def test_a_failed_microphone_test_is_a_sentence(wx_app, monkeypatch) -> None:
    import quill.core.windows_dictation.local_recognizer as local
    import quill.ui.update_download as download
    from quill.core.windows_dictation.controller import DictationStartError
    from quill.ui.windows_dictation_dialog import WindowsDictationDialog

    def refuse(_mic, _engine):
        raise DictationStartError("The microphone could not be opened.")

    monkeypatch.setattr(local, "record_and_hear", refuse)
    monkeypatch.setattr(download, "thread_submit", _run_now)
    monkeypatch.setattr(wx, "CallAfter", lambda fn, *args: fn(*args))
    said: list[str] = []
    dialog = WindowsDictationDialog(None, _Settings(), said.append)
    try:
        dialog._on_test_microphone(None)
        assert said[-1] == "The microphone could not be opened."
    finally:
        dialog.Destroy()
