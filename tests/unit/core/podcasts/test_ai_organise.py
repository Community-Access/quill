"""The safety guarantees of the AI organise feature, which are the feature.

A model is asked where two hundred podcasts belong and answers in text. Every
test here is about the same question: what happens when that text is wrong? It
can name a show that does not exist, a folder that does not exist, the same show
twice, or nothing at all -- and none of those may move a single subscription.
"""

from __future__ import annotations

import json

from quill.core.podcasts.ai_organise import (
    Folder,
    Library,
    Proposal,
    Show,
    apply_plan,
    build_prompt,
    describe_plan,
    read_answer,
)


def _library() -> Library:
    return Library(
        shows=(
            Show("s1", "The Daily", "News from the New York Times.", ""),
            Show("s2", "Hard Fork", "Technology and where it is going.", "Tech"),
            Show("s3", "Radiolab", "Investigative stories about science."),
        ),
        folders=(Folder("f1", "Tech"), Folder("f2", "News")),
    )


def _answer(create: list[dict] | None = None, move: list[dict] | None = None) -> str:
    return json.dumps({"create": create or [], "move": move or []})


# -- the prompt ---------------------------------------------------------- #


def test_the_prompt_sends_titles_and_folders_and_nothing_else() -> None:
    """What the model cannot see, it cannot leak."""
    library = Library(
        shows=(Show("s1", "The Daily", "News.", "News"),),
        folders=(Folder("f1", "News"),),
    )
    prompt = build_prompt(library)
    assert "The Daily" in prompt and "News" in prompt and "s1" in prompt
    # No feed address, no file path, no id of anything but the show.
    assert "http" not in prompt
    assert "f1" not in prompt


def test_the_prompt_truncates_a_long_description() -> None:
    library = Library(shows=(Show("s1", "Show", "x" * 5000),))
    assert len(build_prompt(library)) < 2000


# -- reading a good answer ----------------------------------------------- #


def test_a_move_into_an_existing_folder_resolves_to_its_id() -> None:
    result = read_answer(
        _answer(move=[{"id": "s1", "folder": "News", "reason": "It is news"}]), _library()
    )
    assert len(result.proposals) == 1
    move = result.proposals[0]
    assert move.kind == "move"
    assert move.show_title == "The Daily"
    assert move.folder_id == "f2"  # "News" is f2 in the fixture; "Tech" is f1
    assert move.reason == "It is news"
    assert not result.discarded


def test_a_new_folder_and_the_moves_into_it_both_survive() -> None:
    result = read_answer(
        _answer(
            create=[{"name": "Science", "reason": "Three science shows"}],
            move=[{"id": "s3", "folder": "Science"}],
        ),
        _library(),
    )
    assert [p.kind for p in result.proposals] == ["create", "move"]
    # The move carries the name, not an id, because the folder does not exist yet.
    assert result.moves[0].folder_name == "Science"
    assert result.moves[0].folder_id == ""


def test_json_is_found_inside_prose_and_code_fences() -> None:
    """A model wraps JSON however it was asked not to."""
    body = _answer(move=[{"id": "s1", "folder": "News"}])
    for wrapped in (
        f"Here is my suggestion:\n```json\n{body}\n```\nHope that helps.",
        f"Sure!\n{body}",
    ):
        assert len(read_answer(wrapped, _library()).proposals) == 1


# -- refusing a bad answer ----------------------------------------------- #


def test_a_show_that_does_not_exist_is_discarded_with_a_reason() -> None:
    result = read_answer(_answer(move=[{"id": "nope", "folder": "News"}]), _library())
    assert result.proposals == []
    assert result.discarded and "nope" in result.discarded[0]


def test_a_folder_that_does_not_exist_and_was_not_proposed_is_discarded() -> None:
    """The model cannot move a show somewhere nobody agreed to create."""
    result = read_answer(_answer(move=[{"id": "s1", "folder": "Invented"}]), _library())
    assert result.proposals == []
    assert "Invented" in result.discarded[0]


def test_a_move_that_changes_nothing_is_discarded() -> None:
    """Hard Fork is already in Tech, so "put it in Tech" is not a suggestion."""
    result = read_answer(_answer(move=[{"id": "s2", "folder": "Tech"}]), _library())
    assert result.proposals == []
    assert "already in" in result.discarded[0]


def test_a_folder_that_already_exists_is_not_proposed_again() -> None:
    result = read_answer(_answer(create=[{"name": "tech"}]), _library())
    assert result.creates == []
    assert "already exists" in result.discarded[0]


def test_the_same_show_twice_keeps_the_first_and_says_so() -> None:
    result = read_answer(
        _answer(move=[{"id": "s1", "folder": "News"}, {"id": "s1", "folder": "Tech"}]),
        _library(),
    )
    assert len(result.moves) == 1
    assert result.moves[0].folder_name == "News"
    assert "more than once" in result.discarded[0]


def test_an_answer_that_is_not_json_yields_nothing_and_says_so() -> None:
    result = read_answer("I would put The Daily in News, probably.", _library())
    assert result.proposals == []
    assert "not in the format" in result.discarded[0]


def test_rubbish_shapes_do_not_raise() -> None:
    """Somebody else's output is input. It never crashes the app."""
    for answer in ('{"move": "not a list"}', '{"move": [1, 2, 3]}', "{}", "", "null", "[]"):
        result = read_answer(answer, _library())
        assert isinstance(result.proposals, list)


# -- the account given to the listener ----------------------------------- #


def test_describe_counts_both_kinds_and_the_discards() -> None:
    result = read_answer(
        _answer(
            create=[{"name": "Science"}],
            move=[{"id": "s3", "folder": "Science"}, {"id": "bogus", "folder": "Science"}],
        ),
        _library(),
    )
    sentence = describe_plan(result)
    assert "1 new folder" in sentence and "1 move" in sentence
    assert "Nothing has changed yet" in sentence
    assert "discarded" in sentence


def test_describe_says_so_when_the_library_is_already_tidy() -> None:
    assert "already reads as organised" in describe_plan(read_answer(_answer(), _library()))


def test_a_row_says_the_action_first() -> None:
    """Forty of these are read top to bottom; the verb decides whether to listen."""
    library = _library()
    move = read_answer(_answer(move=[{"id": "s1", "folder": "News"}]), library).moves[0]
    assert move.spoken().startswith("Move: The Daily")
    assert "from no folder to News" in move.spoken()
    create = read_answer(_answer(create=[{"name": "Science"}]), library).creates[0]
    assert create.spoken() == "Create folder: Science"


# -- applying, which this module deliberately cannot do ------------------- #


def test_apply_returns_creates_before_moves() -> None:
    """A move into a folder that has not been made yet cannot be carried out."""
    accepted = [
        Proposal(kind="move", show_id="s3", folder_name="Science"),
        Proposal(kind="create", folder_name="Science"),
    ]
    creates, moves = apply_plan(accepted)
    assert creates == ["Science"]
    assert [m.show_id for m in moves] == ["s3"]


def test_nothing_in_this_module_writes_to_a_library() -> None:
    """The guarantee, asserted rather than trusted.

    apply_plan is handed proposals and returns instructions; the caller owns
    every write. If this module ever grew a library argument, "nothing moves
    here" would have stopped being true.
    """
    import inspect

    from quill.core.podcasts import ai_organise

    for name, function in inspect.getmembers(ai_organise, inspect.isfunction):
        if name.startswith("_"):
            continue
        source = inspect.getsource(function)
        for writer in ("add_folder(", "apply_show_override(", "save_", "delete_folder("):
            assert writer not in source, f"{name} writes to a library via {writer}"
