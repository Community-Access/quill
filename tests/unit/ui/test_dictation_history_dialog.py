"""Tests for the Dictation History & Review dialog (list + actions)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest  # type: ignore[import-not-found]

from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

from quill.ui.dictation_history_dialog import DictationHistoryDialog  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = shared_wx_app()
    yield app
    app.Destroy()


class _FakeRepo:
    def __init__(self) -> None:
        self.deleted: list[str] = []
        self._items = [
            SimpleNamespace(
                session=SimpleNamespace(
                    session_id="s1",
                    started_at=0.0,
                    transcript="hello world",
                    transcription_state="done",
                    insertion_state="deferred",
                ),
                transcript_path=None,
            )
        ]

    def list_incomplete(self) -> list[object]:
        return list(self._items)

    def delete(self, session_id: str) -> None:
        self.deleted.append(session_id)
        self._items = [i for i in self._items if i.session.session_id != session_id]


def test_history_lists_inserts_and_discards(wx_app):
    inserted: list[str] = []
    frame = wx.Frame(None)
    repo = _FakeRepo()
    dlg = DictationHistoryDialog(
        frame, repo=repo, on_insert=inserted.append, on_copy=lambda _t: None
    )
    try:
        assert dlg._list.GetItemCount() == 1  # the one pending recording
        dlg._list.Select(0)
        dlg._on_insert_clicked()
        assert inserted == ["hello world"]
        assert repo.deleted == ["s1"]  # inserting removes it from recovery
        assert dlg._list.GetItemCount() == 0  # reloaded -> empty
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def _dialog(monkeypatch, answer):
    """The window, with the Discard question answered *answer*."""
    from quill.ui import dictation_history_dialog

    asked: list[str] = []

    def box(message, *_a, **_k):
        asked.append(message)
        return answer

    monkeypatch.setattr(dictation_history_dialog, "show_message_box", box)
    frame = wx.Frame(None)
    repo = _FakeRepo()
    dlg = DictationHistoryDialog(
        frame, repo=repo, on_insert=lambda _t: None, on_copy=lambda _t: None
    )
    return frame, repo, dlg, asked


def test_the_state_column_is_words_not_codes(wx_app, monkeypatch):
    frame, _repo, dlg, _asked = _dialog(monkeypatch, wx.NO)
    try:
        assert dlg._list.GetItemText(0, 1) == "Transcribed, not inserted yet"
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_discard_asks_first_and_no_keeps_the_recording(wx_app, monkeypatch):
    frame, repo, dlg, asked = _dialog(monkeypatch, wx.NO)
    try:
        dlg._list.Select(0)
        dlg._on_discard_clicked()
        assert repo.deleted == [] and dlg._list.GetItemCount() == 1
        assert "cannot be brought back" in asked[0] and "transcript" in asked[0]
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_discard_after_yes_deletes(wx_app, monkeypatch):
    frame, repo, dlg, _asked = _dialog(monkeypatch, wx.YES)
    try:
        dlg._list.Select(0)
        dlg._on_discard_clicked()
        assert repo.deleted == ["s1"] and dlg._list.GetItemCount() == 0
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_a_recording_that_could_not_be_kept_is_said_once(wx_call_after):
    """save_audio's failure was swallowed: nobody learned the speech was unprotected."""
    from quill.ui import dictation_history_dialog
    from quill.ui.main_frame_dictation_hotkeys import _LiveDictationServices

    calls: list[tuple] = []
    wx_call_after(lambda fn, *a, **k: calls.append((fn, a, k)))

    class Frame:
        def _announce(self, *_a, **_k):
            pass

    class Broken:
        def save_audio(self, *_a):
            raise OSError("disk full")

    frame = Frame()
    services = _LiveDictationServices(frame)
    services._repo = Broken()
    services.save_audio(SimpleNamespace(), None)
    services.save_audio(SimpleNamespace(), None)
    assert calls == [
        (frame._announce, (dictation_history_dialog.NOT_KEPT_SENTENCE,), {"force": True})
    ]


def test_the_launch_sentence_is_the_shared_one(monkeypatch):
    from quill.core.speech.dictation import recovery
    from quill.ui.main_frame_dictation_hotkeys import DictationHotkeysMixin

    item = SimpleNamespace(
        session=SimpleNamespace(started_at=0.0, transcript="hello world"),
        transcript_path=None,
    )
    monkeypatch.setattr(
        recovery.DictationRecoveryRepository, "list_incomplete", lambda _self: [item]
    )
    heard: list[tuple] = []
    host = SimpleNamespace(_announce=lambda text, **k: heard.append((text, k)))
    DictationHotkeysMixin.check_dictation_recovery_on_startup(host)
    assert heard == [(recovery.startup_sentence([item]), {"force": True})]
    assert "(s)" not in heard[0][0] and "hello world" in heard[0][0]
