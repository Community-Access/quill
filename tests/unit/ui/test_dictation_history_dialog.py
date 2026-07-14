"""Tests for the Dictation History & Review dialog (list + actions)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.ui.dictation_history_dialog import DictationHistoryDialog  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
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
