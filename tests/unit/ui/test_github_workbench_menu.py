"""QUILL's GitHub Workbench Mode on the real menu bar (main_frame_github_menu.py).

The plan's four checks (docs: the Workbench menu plan, section 6.2): rows move
and are never duplicated; one chord, one command, in both modes; the adapter
owns no view logic; and switching GitHub off ends the mode.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

from quill.core.github import workbench_menu as table  # noqa: E402

pytestmark = pytest.mark.machine_global

_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def frame(tmp_path_factory):
    app = shared_wx_app()
    from unittest.mock import patch

    from quill.ui.dialog_contract import set_transition_announcement_policy
    from quill.ui.main_frame import MainFrame

    data = str(tmp_path_factory.mktemp("workbench-menu-data"))
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("QUILL_DATA_DIR", data)
        with patch.object(MainFrame, "check_for_updates", lambda self, **_kwargs: None):
            built = MainFrame()
    yield built
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("QUILL_DATA_DIR", data)
        built.frame.Destroy()
    set_transition_announcement_policy(None)
    del app


def _walk(menu, path=()):
    for item in menu.GetMenuItems():
        if item.IsSeparator():
            continue
        label = item.GetItemLabelText()
        if item.GetSubMenu() is not None:
            yield from _walk(item.GetSubMenu(), (*path, label))
        else:
            yield (*path, label), item


def _rows_by_top(bar) -> dict[str, list[tuple[tuple[str, ...], object]]]:
    return {bar.GetMenuLabelText(i): list(_walk(bar.GetMenu(i))) for i in range(bar.GetMenuCount())}


def _command_ids(frame, rows) -> set[str]:
    by_id = {menu_id: cid for cid, menu_id in frame._command_to_menu_id_map().items()}
    return {by_id[item.GetId()] for _path, item in rows if item.GetId() in by_id}


def _set_mode(frame, on: bool) -> None:
    if frame._github_workbench_mode != on:
        frame.toggle_github_workbench_mode()
    assert frame._github_workbench_mode == on


def test_rows_move_into_the_github_menu_and_back(frame) -> None:
    _set_mode(frame, False)
    normal = _rows_by_top(frame.frame.GetMenuBar())
    assert "GitHub" not in normal
    moved = {
        *table.command_ids(table.NORMAL_REMOTE_ROWS),
        *table.command_ids(table.REPOSITORY_ROWS),
        *table.command_ids(table.LOCAL_GIT_ROWS),
    }
    in_file_and_tools = _command_ids(frame, normal["File"] + normal["Tools"])
    assert moved <= in_file_and_tools

    _set_mode(frame, True)
    workbench = _rows_by_top(frame.frame.GetMenuBar())
    titles = list(workbench)
    assert titles.index("GitHub") == titles.index("Tools") + 1
    github_ids = _command_ids(frame, workbench["GitHub"])
    assert moved <= github_ids
    # Moved, never duplicated: none of them is left in File or Tools.
    assert not (moved & _command_ids(frame, workbench["File"] + workbench["Tools"]))
    labels = [path[-1] for path, _item in workbench["GitHub"]]
    assert labels[0].startswith(("Repository: ", "Leave Workbench Mode"))
    _set_mode(frame, False)
    assert "GitHub" not in _rows_by_top(frame.frame.GetMenuBar())


def test_one_chord_one_command_in_both_modes(frame) -> None:
    _set_mode(frame, False)
    normal = {cid: frame.commands.keybinding_for(cid) for cid in frame._command_to_menu_id_map()}
    _set_mode(frame, True)
    workbench = {cid: frame.commands.keybinding_for(cid) for cid in frame._command_to_menu_id_map()}
    _set_mode(frame, False)
    for cid in set(normal) & set(workbench):
        assert normal[cid] == workbench[cid], cid
    for mapping in (normal, workbench):
        chords = [chord.lower() for chord in mapping.values() if chord]
        assert len(chords) == len(set(chords))


def test_the_switch_says_one_sentence_each_way(frame, monkeypatch) -> None:
    said: list[str] = []
    monkeypatch.setattr(frame, "_announce", lambda message, **_kw: said.append(message))
    _set_mode(frame, False)
    frame.toggle_github_workbench_mode()
    frame.toggle_github_workbench_mode()
    assert said == [table.ANNOUNCE_ON, table.ANNOUNCE_OFF]


def test_switching_github_off_ends_the_mode(frame, monkeypatch) -> None:
    _set_mode(frame, True)
    real = frame._feature_enabled
    monkeypatch.setattr(
        frame, "_feature_enabled", lambda fid: False if fid == "core.github_remote" else real(fid)
    )
    frame._build_menu()
    assert frame._github_workbench_mode is False
    bar = frame.frame.GetMenuBar()
    assert bar.FindMenu("GitHub") == -1
    view = bar.GetMenu(bar.FindMenu("View"))
    assert all("Workbench" not in item.GetItemLabelText() for item in view.GetMenuItems())
    monkeypatch.setattr(frame, "_feature_enabled", real)
    frame._build_menu()


def test_the_adapter_has_no_view_logic_of_its_own() -> None:
    """The view rows are GitHubWorkbenchCommands', shared with QUILL Lite."""
    source = (_ROOT / "quill" / "ui" / "main_frame_github_menu.py").read_text(encoding="utf-8")
    strings = {
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    for view in ("attention", "my_work", "notifications", "runs", "releases", "issues"):
        assert view not in strings, view
    assert "GitHubWorkbenchCommands" in source


def test_the_menu_title_literal_is_the_tables() -> None:
    source = (_ROOT / "quill" / "ui" / "main_frame_github_menu.py").read_text(encoding="utf-8")
    assert f'menu_bar.Append(menu, _("{table.GITHUB_MENU_TITLE}"))' in source
