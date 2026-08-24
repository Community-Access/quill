"""11.3: one step of undo, and what it is honest about.

The slot is deliberately one deep -- a listener who has to remember how many
times to press Ctrl+Z has been given a puzzle, not an undo -- so the tests
that matter are about displacement, single use, and the sentences.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.undo_last import (
    UndoableAction,
    UndoSlot,
    discard_held,
    hold_files,
    restore_held,
)


def _action(verb: str = "Unsubscribe", **kwargs: object) -> UndoableAction:
    defaults: dict = {
        "verb": verb,
        "subject": "The Daily",
        "restores": "412 episodes and 3 downloaded files",
        "undo": lambda: None,
    }
    defaults.update(kwargs)
    return UndoableAction(**defaults)  # type: ignore[arg-type]


def test_the_offer_names_what_would_come_back() -> None:
    assert _action().offer() == (
        "Undo Unsubscribe: brings back The Daily, with 412 episodes and 3 downloaded files."
    )


def test_the_caveat_rides_along_in_the_same_breath() -> None:
    action = _action(caveat="The private-feed password is not restored")
    assert action.offer().endswith("The private-feed password is not restored.")
    assert action.done().startswith("Undid Unsubscribe. Brought back The Daily")


def test_an_action_with_nothing_to_enumerate_still_reads() -> None:
    action = _action("Delete Recording", subject="WQXR 2026-08-24.mp3", restores="")
    assert action.offer() == "Undo Delete Recording: brings back WQXR 2026-08-24.mp3."


def test_remembering_displaces_and_disposes_of_the_step_before() -> None:
    disposed: list[str] = []
    slot = UndoSlot()
    slot.remember(_action("First", dispose=lambda: disposed.append("first")))
    assert disposed == []
    slot.remember(_action("Second"))
    assert disposed == ["first"], "the displaced step's files must stop being held"
    assert slot.menu_label() == "Undo Second"


def test_undo_is_once_not_a_rewind() -> None:
    slot = UndoSlot()
    slot.remember(_action())
    assert slot.take() is not None
    assert slot.take() is None
    assert slot.offer_sentence() == "Nothing to undo."
    assert slot.menu_label() == "Undo"


def test_taking_the_action_does_not_dispose_of_its_files() -> None:
    """Take means "I am about to undo this" -- disposing would delete what
    the undo is about to restore."""
    disposed: list[str] = []
    slot = UndoSlot()
    slot.remember(_action(dispose=lambda: disposed.append("x")))
    slot.take()
    assert disposed == []


def test_clearing_disposes_of_what_was_held() -> None:
    disposed: list[str] = []
    slot = UndoSlot()
    slot.remember(_action(dispose=lambda: disposed.append("x")))
    slot.clear()
    assert disposed == ["x"]
    assert slot.peek() is None


def test_a_disposer_that_raises_does_not_take_the_app_down() -> None:
    def _boom() -> None:
        raise OSError("the file is open in another program")

    slot = UndoSlot()
    slot.remember(_action(dispose=_boom))
    slot.remember(_action("Second"))
    assert slot.menu_label() == "Undo Second"


# -- holding files --------------------------------------------------------------


def test_held_files_move_aside_and_come_back(tmp_path: Path) -> None:
    source = tmp_path / "downloads"
    source.mkdir()
    first = source / "ep1.mp3"
    second = source / "ep2.mp3"
    first.write_bytes(b"one")
    second.write_bytes(b"two")

    held = hold_files([first, second], tmp_path / "undo-hold")
    assert len(held) == 2
    assert not first.exists() and not second.exists()

    assert restore_held(held) == 2
    assert first.read_bytes() == b"one"
    assert second.read_bytes() == b"two"


def test_files_with_the_same_name_do_not_collide_in_the_hold(tmp_path: Path) -> None:
    show_a = tmp_path / "a"
    show_b = tmp_path / "b"
    show_a.mkdir()
    show_b.mkdir()
    (show_a / "episode.mp3").write_bytes(b"a")
    (show_b / "episode.mp3").write_bytes(b"b")

    held = hold_files([show_a / "episode.mp3", show_b / "episode.mp3"], tmp_path / "hold")
    assert len(held) == 2, "an index prefix keeps same-named files apart"
    restore_held(held)
    assert (show_a / "episode.mp3").read_bytes() == b"a"
    assert (show_b / "episode.mp3").read_bytes() == b"b"


def test_a_missing_file_is_skipped_rather_than_failing_the_whole_hold(tmp_path: Path) -> None:
    present = tmp_path / "here.mp3"
    present.write_bytes(b"x")
    held = hold_files([present, tmp_path / "gone.mp3"], tmp_path / "hold")
    assert len(held) == 1


def test_discarding_is_where_the_delete_actually_happens(tmp_path: Path) -> None:
    target = tmp_path / "ep.mp3"
    target.write_bytes(b"x")
    held = hold_files([target], tmp_path / "hold")
    assert list(held)[0].exists()
    discard_held(held)
    assert not list(held)[0].exists()
    assert not target.exists()


def test_restoring_recreates_a_folder_the_delete_emptied(tmp_path: Path) -> None:
    folder = tmp_path / "Podcasts" / "The Daily"
    folder.mkdir(parents=True)
    episode = folder / "ep.mp3"
    episode.write_bytes(b"x")
    held = hold_files([episode], tmp_path / "hold")
    folder.rmdir()
    assert restore_held(held) == 1
    assert episode.exists()
