"""The Transcribe a Recording window, shared by QUILL and QUILL Lite, and
QUILL's adapter delivering the transcript.

The window is built for real; the model store and OpenAI are faked, so what is
on this computer and whether a key is saved are decided by the test.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

wx = pytest.importorskip("wx")


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app


@pytest.fixture
def models(monkeypatch):
    from quill.core.windows_dictation import model_store, openai_models
    from quill.core.windows_dictation.model_catalog import downloadable

    have: list[str] = []
    key = {"problem": "No key."}
    monkeypatch.setattr(
        model_store, "installed_models", lambda: [downloadable(name) for name in have]
    )
    monkeypatch.setattr(openai_models, "cloud_problem", lambda **_k: key["problem"])
    return have, key


def _dialog(**kwargs: Any) -> Any:
    from quill.ui.dictation_transcribe_dialog import TranscribeFileDialog

    warned: list[str] = []
    kwargs.setdefault("weak", True)
    dialog = TranscribeFileDialog(None, load_openai=False, warn=warned.append, **kwargs)
    return dialog, warned


def _ok(dialog: Any) -> bool:
    """Press Transcribe; True when the window accepted it."""
    event = wx.CommandEvent(wx.wxEVT_BUTTON, wx.ID_OK)
    dialog._on_ok(event)
    return dialog.choice() is not None


def test_the_most_accurate_model_is_chosen_and_explained(wx_app, models, tmp_path) -> None:
    have, _key = models
    have.extend(["parakeet", "whisper_base"])
    recording = tmp_path / "talk.wav"
    _write_wav(recording, seconds=2)
    dialog, _warned = _dialog(paths=[recording])
    try:
        assert dialog.selected_model().id == "parakeet"
        about = dialog.about.GetValue()
        assert "The recording is 2 seconds long." in about
        assert "With NVIDIA Parakeet TDT 0.6B v3, transcribing it should take" in about
        assert dialog.destination.GetSelection() == 0  # a new document by default
        assert not dialog.timestamps.GetValue() and not dialog.obey.GetValue()
        assert _ok(dialog)
        choice = dialog.choice()
        assert choice.paths == (recording,)
        assert choice.destination == "new"
    finally:
        dialog.Destroy()


def test_timestamps_are_off_until_checked_and_both_states_come_back(
    wx_app, models, tmp_path
) -> None:
    wx.HelpProvider.Set(wx.SimpleHelpProvider())  # SetHelpText stores nothing without one
    recording = tmp_path / "talk.wav"
    _write_wav(recording, seconds=1)
    for checked in (False, True):
        dialog, _warned = _dialog(paths=[recording])
        try:
            assert dialog.timestamps.GetValue() is False  # off for everyone, every time
            assert dialog.timestamps.GetLabel() == "Add &timestamps"
            assert dialog.timestamps.GetHelpText().startswith("Off unless you check it.")
            dialog.timestamps.SetValue(checked)
            assert _ok(dialog)
            assert dialog.choice().timestamps is checked
        finally:
            dialog.Destroy()


def test_spanish_keeps_only_spanish_models(wx_app, models) -> None:
    have, _key = models
    have.append("parakeet_unified")
    dialog, _warned = _dialog()
    try:
        dialog.language.SetSelection(1)
        dialog._fill_models()
        ids = [model.id for model in dialog._models]
        assert ids == ["whisper"]
    finally:
        dialog.Destroy()


def test_openai_joins_when_its_list_arrives_and_is_never_preselected(wx_app, models) -> None:
    _have, key = models
    key["problem"] = ""
    dialog, _warned = _dialog()
    try:
        before = dialog.selected_model().id
        dialog.show_openai(["gpt-live-transcribe", "gpt-transcribe"])
        labels = [model.label for model in dialog._models]
        assert any("gpt-transcribe" in label for label in labels)
        assert not any("gpt-live-transcribe" in label for label in labels)
        assert dialog.selected_model().id == before
    finally:
        dialog.Destroy()


def test_nothing_starts_without_a_recording_that_exists(wx_app, models, tmp_path) -> None:
    dialog, warned = _dialog()
    try:
        assert not _ok(dialog)
        assert warned[-1].startswith("Choose a recording")
        dialog.set_paths([tmp_path / "missing.mp3"])
        assert not _ok(dialog)
        assert "missing.mp3 was not found" in warned[-1]
    finally:
        dialog.Destroy()


def test_several_recordings_and_a_running_one(wx_app, models, tmp_path) -> None:
    first, second = tmp_path / "a.wav", tmp_path / "b.wav"
    _write_wav(first, 1)
    _write_wav(second, 1)
    dialog, _warned = _dialog(running="meeting.mp3, 40 percent done.")
    try:
        assert dialog.running.GetValue() == "meeting.mp3, 40 percent done."
        dialog.set_paths([first, second])
        assert dialog.file.GetValue().startswith("2 recordings: a.wav; b.wav")
        assert _ok(dialog)
        assert dialog.choice().paths == (first, second)
    finally:
        dialog.Destroy()


def _write_wav(path: Path, seconds: float) -> None:
    import wave

    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(16_000)
        out.writeframes(b"\x00\x00" * int(16_000 * seconds))


# --------------------------------------------------------------------------- #
# QUILL's adapter: the same command, QUILL's document and task manager
# --------------------------------------------------------------------------- #


class _Editor:
    def __init__(self, text: str) -> None:
        self.text = text
        self.selection = (len(text), len(text))

    def GetSelection(self) -> tuple[int, int]:  # noqa: N802 - wx API shape
        return self.selection

    def GetRange(self, start: int, end: int) -> str:  # noqa: N802
        return self.text[start:end]

    def GetLastPosition(self) -> int:  # noqa: N802
        return len(self.text)

    def IsEditable(self) -> bool:  # noqa: N802
        return True

    def Replace(self, start: int, end: int, text: str) -> None:  # noqa: N802
        self.text = self.text[:start] + text + self.text[end:]

    def __bool__(self) -> bool:
        return True


def _quill_host(text: str = "Minutes.") -> Any:
    from quill.ui.main_frame_windows_dictation import WindowsDictationCommandsMixin

    class Host(WindowsDictationCommandsMixin):
        def __init__(self) -> None:
            self.editor = _Editor(text)
            self.tabs: list[str] = []
            self._task_manager = object()

        def _power_tools_open_text_in_new_buffer(self, text: str, status: str) -> None:
            self.tabs.append(text)

        def _dictation_after_edit(self) -> None:
            pass

    return Host()


def test_quill_opens_the_transcript_in_a_new_tab() -> None:
    from quill.core.windows_dictation.file_transcribe import FileJob

    host = _quill_host()
    where = host._transcribe_deliver("Hello there.", FileJob(Path("a.mp3"), "moonshine"))
    assert where == "in a new document"
    assert host.tabs == ["Hello there."]
    assert host._dictation_task_manager() is host._task_manager


def test_quill_puts_it_at_the_cursor_as_paragraphs_of_its_own() -> None:
    from quill.core.windows_dictation.file_transcribe import FileJob

    host = _quill_host("Minutes.")
    job = FileJob(Path("a.mp3"), "moonshine", destination="cursor")
    assert host._transcribe_deliver("Hello there.", job) == "at the cursor"
    assert host.editor.text == "Minutes.\n\nHello there."
    assert host.tabs == []
