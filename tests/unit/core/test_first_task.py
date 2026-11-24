"""The first-task sentence (FUX-09): an empty place names what fills it, with its live key."""

from __future__ import annotations

from quill.core.first_task import NextAction, first_task_line, named

ADD = NextAction("&Add Podcast...", "cast.add", "finds one by name")
IMPORT = NextAction("Import OPML", "cast.opml")


def test_one_action_names_its_label_key_and_what_it_does() -> None:
    line = first_task_line("No podcasts yet", [ADD], {"cast.add": "Ctrl+N"}.get)
    assert line == "No podcasts yet. Add Podcast (Ctrl+N) finds one by name."


def test_two_actions_read_as_a_choice() -> None:
    keys = {"cast.add": "Ctrl+N", "cast.opml": "Ctrl+Alt+I"}
    line = first_task_line("No podcasts yet.", [ADD, IMPORT], keys.get)
    assert line == (
        "No podcasts yet. Add Podcast (Ctrl+N) finds one by name, or Import OPML (Ctrl+Alt+I)."
    )


def test_a_rebound_key_is_the_key_said_and_an_unbound_one_is_never_invented() -> None:
    assert named(ADD, {"cast.add": "F7"}.get).startswith("Add Podcast (F7)")
    assert named(ADD, {}.get) == "Add Podcast finds one by name"


def test_a_fixed_key_stands_in_only_when_the_command_has_no_binding() -> None:
    button = NextAction("Add Files", "conv.add", key="Alt+A")
    assert named(button, {}.get) == "Add Files (Alt+A)"
    assert named(button, {"conv.add": "Ctrl+O"}.get) == "Add Files (Ctrl+O)"


def test_a_broken_lookup_names_the_label_alone() -> None:
    def broken(_command_id: str) -> str:
        raise RuntimeError("keymap gone")

    assert named(ADD, broken) == "Add Podcast finds one by name"


def test_more_than_two_actions_is_a_menu_so_only_two_are_named() -> None:
    third = NextAction("Search")
    line = first_task_line("Nothing yet", [ADD, IMPORT, third])
    assert "Search" not in line
