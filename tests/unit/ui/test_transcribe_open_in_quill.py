"""FUX-02: Review Transcript's Open in QUILL is said once and never silent.

It went through ``AppShell.open_in_quill``, which said nothing when QUILL
opened and never checked that an editor was installed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

wx = pytest.importorskip("wx")


def _open(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, editor: str, opens: bool):
    import quill.apps.transcribe_files as files
    from quill.ui import scribe_app_host

    path = tmp_path / "talk.txt"
    path.write_text("the whole talk", encoding="utf-8")

    class _Dialog:
        def __init__(self, _parent: Any, text: str) -> None:
            self.action, self.chosen_text = "quill", text

        def Destroy(self) -> None:  # noqa: N802
            pass

    opened: list[Path] = []
    said: list[str] = []

    class _Host(files.TranscribeFilesMixin):
        frame = None

        def _show_modal_dialog(self, _dialog: Any, _label: str) -> int:
            return wx.ID_OK

        def _announce(self, text: str, **_kw: object) -> None:
            said.append(text)

        def open_in_quill(self, *_paths: str) -> None:
            raise AssertionError("the silent path is not used")

    monkeypatch.setattr(files, "TranscriptReviewDialog", _Dialog)
    monkeypatch.setattr(scribe_app_host, "editor_name", lambda: editor)
    monkeypatch.setattr(
        scribe_app_host,
        "open_in_editor",
        lambda p, **_k: opened.append(p) or (editor if opens else ""),
    )
    _Host()._dictation_open_file(path)
    return path, opened, said


def test_opening_says_so_once(monkeypatch, tmp_path) -> None:
    path, opened, said = _open(monkeypatch, tmp_path, "QUILL", True)
    assert opened == [path]
    assert said == ["Opening the transcript in QUILL."]


def test_no_editor_is_said_once_and_offers_save_as(monkeypatch, tmp_path) -> None:
    _path, _opened, said = _open(monkeypatch, tmp_path, "", False)
    assert said == [
        "Neither QUILL nor QUILL Lite could be opened, so the transcript was not "
        "opened. Save As keeps a copy where you choose."
    ]
