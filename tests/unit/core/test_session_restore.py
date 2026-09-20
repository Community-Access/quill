"""The session-restore decisions, which both editors take from one place."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.session_restore import (
    A_CROWD,
    ASK_ALWAYS,
    ASK_MODE_LABELS,
    ASK_MODES,
    ASK_NEVER,
    ASK_WHEN_IT_MATTERS,
    SessionEntry,
    describe_forgotten,
    describe_opened,
    forget,
    missing,
    openable,
    read_entries,
    should_ask,
    summarise,
)


@pytest.fixture
def three_files(tmp_path: Path) -> list[str]:
    paths = []
    for name in ("one.txt", "two.md", "three.rtf"):
        target = tmp_path / name
        target.write_text("x", encoding="utf-8")
        paths.append(str(target))
    return paths


def test_a_remembered_file_that_is_there_is_openable(three_files: list[str]) -> None:
    entries = read_entries(three_files)
    assert len(entries) == 3
    assert all(entry.exists for entry in entries)
    assert openable(entries) == entries
    assert missing(entries) == ()


def test_a_remembered_file_that_has_gone_is_a_row_not_an_omission(tmp_path: Path) -> None:
    """The silent path dropped it. A file that *moved* is exactly the news."""
    gone = str(tmp_path / "vanished.txt")
    entries = read_entries([gone])
    assert len(entries) == 1
    assert entries[0].exists is False
    assert openable(entries) == ()
    assert "no longer there" in entries[0].label


def test_the_list_is_read_defensively(tmp_path: Path) -> None:
    """A damaged settings file must not stop a launch."""
    real = tmp_path / "real.txt"
    real.write_text("x", encoding="utf-8")
    entries = read_entries([str(real), "", "   ", None, str(real)])
    # Blanks dropped, and the duplicate seen once.
    assert [entry.path for entry in entries] == [str(real)]
    assert read_entries("not a list") == ()
    assert read_entries(None) == ()


def test_one_file_that_is_still_there_is_not_worth_asking_about(three_files: list[str]) -> None:
    entries = read_entries(three_files[:1])
    assert should_ask(entries, mode=ASK_WHEN_IT_MATTERS) is False
    entries = read_entries(three_files[:2])
    assert should_ask(entries, mode=ASK_WHEN_IT_MATTERS) is False


def test_three_is_a_crowd(three_files: list[str]) -> None:
    entries = read_entries(three_files)
    assert len(entries) == A_CROWD
    assert should_ask(entries, mode=ASK_WHEN_IT_MATTERS) is True


def test_one_missing_file_is_worth_asking_about_on_its_own(tmp_path: Path) -> None:
    """Two files, one gone: silence here is indistinguishable from success."""
    here = tmp_path / "here.txt"
    here.write_text("x", encoding="utf-8")
    entries = read_entries([str(here), str(tmp_path / "gone.txt")])
    assert len(entries) < A_CROWD
    assert should_ask(entries, mode=ASK_WHEN_IT_MATTERS) is True


def test_the_two_other_modes_do_what_they_say(three_files: list[str]) -> None:
    one = read_entries(three_files[:1])
    three = read_entries(three_files)
    assert should_ask(one, mode=ASK_ALWAYS) is True
    assert should_ask(three, mode=ASK_NEVER) is False


def test_nothing_remembered_is_never_worth_asking_about() -> None:
    for mode in ASK_MODES:
        assert should_ask((), mode=mode) is False


def test_an_unknown_mode_behaves_like_the_default(three_files: list[str]) -> None:
    """A hand-edited settings file must not turn the feature into a coin toss."""
    three = read_entries(three_files)
    one = read_entries(three_files[:1])
    assert should_ask(three, mode="nonsense") is True
    assert should_ask(one, mode="nonsense") is False


def test_forgetting_only_drops_rows(three_files: list[str]) -> None:
    entries = read_entries(three_files)
    kept = forget(entries, [three_files[1]])
    assert kept == (three_files[0], three_files[2])
    # The whole point: the files are still there.
    assert all(Path(path).is_file() for path in three_files)


def test_forgetting_matches_the_remembered_string(tmp_path: Path) -> None:
    """Including for a row whose file has gone -- the likeliest one to forget."""
    gone = str(tmp_path / "gone.txt")
    entries = read_entries([gone])
    assert forget(entries, [gone]) == ()


def test_forgetting_nothing_keeps_everything(three_files: list[str]) -> None:
    entries = read_entries(three_files)
    assert forget(entries, []) == tuple(three_files)
    assert forget(entries, "not a list") == tuple(three_files)


def test_the_summary_leads_with_the_count_and_names_the_problem(tmp_path: Path) -> None:
    here = tmp_path / "here.txt"
    here.write_text("x", encoding="utf-8")
    assert summarise(()) == "Nothing was open last time."
    assert summarise(read_entries([str(here)])).startswith("1 document")
    two = read_entries([str(here), str(tmp_path / "gone.txt")])
    said = summarise(two)
    assert said.startswith("2 documents")
    assert "1 of which is no longer there" in said
    all_gone = read_entries([str(tmp_path / "a.txt"), str(tmp_path / "b.txt")])
    assert "none of the files are there any more" in summarise(all_gone)


def test_opening_says_how_many_even_when_it_is_none() -> None:
    """Silence after a command is indistinguishable from a command that failed."""
    assert describe_opened(0, 0) == "Nothing to reopen."
    assert describe_opened(0, 3) == "Opened none of the 3."
    assert describe_opened(2, 3) == "Reopened 2 of 3."
    assert describe_opened(1, 1) == "Reopened all 1 document."
    assert describe_opened(4, 4) == "Reopened all 4 documents."


def test_forgetting_says_the_files_are_untouched() -> None:
    said = describe_forgotten(2, 1)
    assert "Forgot 2 documents" in said
    assert "1 still remembered" in said
    assert "files themselves are untouched" in said
    assert "The list is empty now." in describe_forgotten(3, 0)
    assert describe_forgotten(0, 3) == "Nothing was forgotten."


def test_every_mode_has_a_label_and_the_labels_say_which_is_which() -> None:
    assert set(ASK_MODE_LABELS) == set(ASK_MODES)
    for mode, label in ASK_MODE_LABELS.items():
        assert len(label) > 10, mode
    # The default's label has to explain the trigger, or nobody can predict it.
    assert "moved" in ASK_MODE_LABELS[ASK_WHEN_IT_MATTERS]


def test_the_name_is_the_file_name(tmp_path: Path) -> None:
    entry = SessionEntry(str(tmp_path / "notes.md"), True)
    assert entry.name == "notes.md"
    assert entry.label.startswith("notes.md")
