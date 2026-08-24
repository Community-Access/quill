"""11.3 wiring: the slot is claimed by an app, and QUILL is left alone.

The off switch is the load-bearing part. ``hold_or_delete`` moves files aside
*only* while an app owns undo; in QUILL -- whose Ctrl+Z is the editor's, and
where nobody could ever reach the slot -- a delete has to stay a delete, or
the bytes would sit in a holding folder for good.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.ui import undo_last_ui


@pytest.fixture(autouse=True)
def _fresh_slot() -> object:
    """Every test starts with no owner; module state never leaks between them."""
    undo_last_ui._slot = None
    undo_last_ui._data_dir = None
    yield
    undo_last_ui._slot = None
    undo_last_ui._data_dir = None


def test_without_an_owner_nothing_is_remembered_and_deletes_are_deletes(tmp_path: Path) -> None:
    target = tmp_path / "ep.mp3"
    target.write_bytes(b"x")
    assert undo_last_ui.is_active() is False
    assert undo_last_ui.remember("Unsubscribe", "The Daily", "", lambda: None) is False
    assert undo_last_ui.hold_or_delete([target]) == {}
    assert not target.exists(), "QUILL must not hold bytes for a slot nobody can reach"


def test_the_offer_is_only_appended_where_ctrl_z_means_undo() -> None:
    assert undo_last_ui.offer("Unsubscribed from The Daily") == "Unsubscribed from The Daily"
    undo_last_ui.activate(Path("."))
    assert undo_last_ui.offer("Unsubscribed from The Daily") == (
        "Unsubscribed from The Daily. Ctrl+Z undoes this."
    )
    assert undo_last_ui.offer("Removed 3 files.") == "Removed 3 files. Ctrl+Z undoes this."


def test_an_owning_app_holds_the_files_and_can_put_them_back(tmp_path: Path) -> None:
    undo_last_ui.activate(tmp_path)
    target = tmp_path / "ep.mp3"
    target.write_bytes(b"x")
    held = undo_last_ui.hold_or_delete([target])
    assert held and not target.exists()
    assert undo_last_ui.restore(held) == 1
    assert target.read_bytes() == b"x"


def test_activate_sweeps_a_holding_folder_a_crash_left_behind(tmp_path: Path) -> None:
    stale = tmp_path / undo_last_ui.HELD_DIR_NAME
    stale.mkdir()
    (stale / "0000-old.mp3").write_bytes(b"stale")
    undo_last_ui.activate(tmp_path)
    assert list(stale.iterdir()) == [], "a step nobody can reach must not be kept"


def test_retention_deletes_inside_the_block_are_held_not_unlinked(tmp_path: Path) -> None:
    from quill.core.podcasts import retention

    undo_last_ui.activate(tmp_path)
    first = tmp_path / "a.mp3"
    second = tmp_path / "b.mp3"
    first.write_bytes(b"a")
    second.write_bytes(b"b")

    with undo_last_ui.capturing_deletes() as held:
        retention._delete_file(str(first))
        retention._delete_file(str(second))

    assert len(held) == 2
    assert not first.exists() and not second.exists()
    assert undo_last_ui.restore(held) == 2
    assert first.read_bytes() == b"a"
    assert second.read_bytes() == b"b"


def test_the_delete_hook_is_removed_again_when_the_block_ends(tmp_path: Path) -> None:
    from quill.core.podcasts import retention

    undo_last_ui.activate(tmp_path)
    with undo_last_ui.capturing_deletes():
        pass
    outside = tmp_path / "after.mp3"
    outside.write_bytes(b"x")
    retention._delete_file(str(outside))
    assert not outside.exists(), "an ordinary retention delete must still delete"


def test_the_handler_refuses_honestly_with_an_empty_slot() -> None:
    said: list[str] = []

    class _Frame(undo_last_ui.UndoLastMixin):
        def _announce(self, message: str) -> None:
            said.append(message)

    undo_last_ui.activate(Path("."))
    _Frame().undo_last_action()
    assert said == ["Nothing to undo."]


def test_the_handler_says_what_it_brought_back() -> None:
    said: list[str] = []
    undone: list[str] = []

    class _Frame(undo_last_ui.UndoLastMixin):
        def _announce(self, message: str) -> None:
            said.append(message)

    undo_last_ui.activate(Path("."))
    undo_last_ui.remember("Unsubscribe", "The Daily", "412 episodes", lambda: undone.append("ran"))
    frame = _Frame()
    assert frame.undo_last_menu_label() == "Undo Unsubscribe"
    frame.undo_last_action()
    assert undone == ["ran"]
    assert said == ["Undid Unsubscribe. Brought back The Daily, with 412 episodes."]
    frame.undo_last_action()
    assert said[-1] == "Nothing to undo."


def test_an_undo_that_fails_says_so_rather_than_claiming_success() -> None:
    said: list[str] = []

    class _Frame(undo_last_ui.UndoLastMixin):
        def _announce(self, message: str) -> None:
            said.append(message)

    def _boom() -> None:
        raise OSError("the library file is read-only")

    undo_last_ui.activate(Path("."))
    undo_last_ui.remember("Unsubscribe", "The Daily", "", _boom)
    _Frame().undo_last_action()
    assert said == ["Could not undo Unsubscribe: the library file is read-only."]
