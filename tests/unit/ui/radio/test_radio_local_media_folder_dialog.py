"""Add a Folder's dialog and what it adds (Chris Nova, 2026-11-09).

The dialog is built and driven without being shown; the add itself runs
through ``local_media_ui.add_paths`` with no task manager, so it finishes
inline.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

from quill.core.radio.local_media import LocalMediaLibrary  # noqa: E402
from quill.ui.radio import local_media_folder_dialog as folder_dialog  # noqa: E402
from quill.ui.radio import local_media_ui as ui  # noqa: E402


@pytest.fixture
def app(quill_data_dir):
    application = shared_wx_app()
    yield application
    for window in wx.GetTopLevelWindows():
        window.Destroy()
    del application


class _Host:
    def __init__(self) -> None:
        self._local_media_library = LocalMediaLibrary()
        self._radio_history = SimpleNamespace()
        self._task_manager = None
        self.frame = None
        self.said: list[str] = []

    def _announce(self, text: str, *_args: object, **_kwargs: object) -> None:
        self.said.append(text)


def _downloads(tmp_path: Path) -> Path:
    root = tmp_path / "other files" / "downloads"
    (root / "Disc 2").mkdir(parents=True)
    (root / "12_days_of_Assistive_Tech_20261109_1203.mp3").write_bytes(b"x")
    (root / "talk.mp4").write_bytes(b"x")
    (root / "Disc 2" / "track 1.mp3").write_bytes(b"x")
    return root


def _dialog(**kwargs: object) -> tuple[folder_dialog.AddFolderDialog, list[str]]:
    said: list[str] = []
    built = folder_dialog.AddFolderDialog(wx, None, announce=said.append, **kwargs)  # type: ignore[arg-type]
    return built, said


def test_a_typed_path_that_is_not_a_folder_is_said_and_the_box_stays_open(app, tmp_path) -> None:
    built, said = _dialog(new_playlist=True, start=str(tmp_path / "nowhere"))
    problem = built.check()
    assert problem.startswith("There is no folder at")
    assert built.problem.GetLabel() == problem
    assert said == [problem]
    built.dialog.Destroy()


def test_a_pasted_path_with_quotes_and_spaces_is_accepted(app, tmp_path) -> None:
    root = _downloads(tmp_path)
    built, said = _dialog(new_playlist=True, start=f'"{root}"')
    assert built.check() == ""
    assert said == []
    choice = built.choice()
    assert choice == folder_dialog.FolderChoice(path=str(root), subfolders=True, follow=True)
    built.dialog.Destroy()


def test_both_choices_start_checked_and_follow_shows_only_for_a_new_playlist(app) -> None:
    new, _ = _dialog(new_playlist=True)
    assert new.subfolders.GetValue() and new.follow.GetValue()
    assert new.follow.IsShown()
    existing, _ = _dialog(new_playlist=False)
    assert not existing.follow.IsShown()
    existing.subfolders.SetValue(False)
    assert existing.choice().follow is False and existing.choice().subfolders is False
    new.dialog.Destroy()
    existing.dialog.Destroy()


def test_every_control_has_help_and_ok_and_cancel_carry_no_access_key(app) -> None:
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)  # SetHelpText stores nothing without one
    built, _ = _dialog(new_playlist=True)
    for control in (
        built.path,
        built.browse,
        built.subfolders,
        built.follow,
        built.ok,
        built.cancel,
    ):
        assert control.GetHelpText().strip()
    assert "&" not in built.ok.GetLabel() and "&" not in built.cancel.GetLabel()
    built.dialog.Destroy()


def test_without_subfolders_only_the_folder_itself_is_added_and_kept(app, tmp_path) -> None:
    root = _downloads(tmp_path)
    host = _Host()
    ui.add_paths(host, [str(root)], folder=str(root), subfolders=False, follow=False)
    playlist = host._local_media_library.playlists[0]
    assert {Path(item.path).name for item in playlist.items} == {
        "12_days_of_Assistive_Tech_20261109_1203.mp3",
        "talk.mp4",
    }
    assert playlist.subfolders is False and playlist.watch is False
    assert playlist.folder == str(root)
    assert host.said[-1] == "Made a playlist called downloads, with 1 audio file and 1 video."


def test_with_subfolders_the_discs_come_too_and_the_folder_is_followed(app, tmp_path) -> None:
    root = _downloads(tmp_path)
    host = _Host()
    ui.add_paths(host, [str(root)], folder=str(root))
    playlist = host._local_media_library.playlists[0]
    assert len(playlist.items) == 3
    assert playlist.subfolders is True and playlist.watch is True
    assert host.said[-1] == "Made a playlist called downloads, with 2 audio files and 1 video."


def test_ask_folder_choice_returns_none_on_cancel_and_remembers_the_last_folder(
    app, tmp_path, monkeypatch
) -> None:
    root = _downloads(tmp_path)
    host = _Host()
    answers = iter([wx.ID_CANCEL, wx.ID_OK])

    def _show(_host: object, dialog: object, _label: str) -> int:
        answer = next(answers)
        if answer == wx.ID_OK:
            boxes = [c for c in dialog.GetChildren() if isinstance(c, wx.TextCtrl)]  # type: ignore[attr-defined]
            boxes[0].SetValue(str(root))
        return answer

    monkeypatch.setattr(ui, "show_modal_dialog", _show)
    monkeypatch.setitem(folder_dialog._last_folder, "path", "")
    assert folder_dialog.ask_folder_choice(host, new_playlist=True) is None
    picked = folder_dialog.ask_folder_choice(host, new_playlist=True)
    assert picked is not None and picked.path == str(root)
    assert folder_dialog._last_folder["path"] == str(root)
