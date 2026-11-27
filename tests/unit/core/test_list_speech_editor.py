"""The List Speech Templates editor's rules, with no window."""

from __future__ import annotations

from quill.core.list_speech import editor_state as es
from quill.core.list_speech import library as lib
from quill.core.list_speech.speak import SPEECH_COLUMN


def _open(list_type: str = "github_issues") -> es.EditorState:
    return es.start(lib.Library(), list_type)


def test_opens_on_the_usual_wording_with_a_balanced_starting_point() -> None:
    state = _open()
    assert state.source == "" and not state.dirty
    assert state.draft.fields == state.kind.presets[1].fields
    assert es.source_choices(state)[0] == ("", "Usual wording")
    assert [t for _r, t in es.source_choices(state)][1:4] == ["Brief", "Balanced", "Detailed"]


def test_choose_preset_and_say_so() -> None:
    state, message = es.choose_source(_open(), "builtin:brief")
    assert state.draft.fields == ("number", "title", "state") and message == "Brief chosen."


def test_move_announces_position_and_edges() -> None:
    state, index, message = es.move(_open(), 1, -1)
    assert index == 0 and message == "Title moved to position 1 of 5."
    assert state.dirty and state.source == "" and state.draft.fields[0] == "title"
    _s, index, message = es.move(state, 0, -1)
    assert index == 0 and message == "Title is already first."
    last = len(state.draft.fields) - 1
    assert es.move(state, last, 1)[2].endswith("is already last.")
    assert es.move(state, -1, 1)[2] == "Nothing is selected to move."


def test_add_and_remove_fields() -> None:
    state, message = es.add_field(_open(), "labels")
    assert state.draft.fields[-1] == "labels" and message == "Added Labels, position 6 of 6."
    assert es.add_field(state, "labels")[1] == "Labels is already in the template."
    assert es.add_field(state, "nope")[1] == "That field is not offered for this list."
    state, message = es.remove_field(state, 0)
    assert "number" not in state.draft.fields and message == "Removed Number. 5 left."
    assert es.remove_field(state, 99)[1] == "Nothing is selected to remove."


def test_editing_a_preset_makes_a_custom_draft_that_must_be_saved_first() -> None:
    state, _ = es.choose_source(_open(), "builtin:detailed")
    state, _ = es.set_labels(state, False)
    assert state.source == "" and state.dirty
    assert es.assign_current(state)[1] == "Save the template first, then use it."


def test_preview_follows_the_draft() -> None:
    state, _ = es.choose_source(_open(), "builtin:brief")
    assert es.preview(state) == "number 42, Login fails after password reset, open"
    state, _ = es.set_separator(state, " / ")
    assert " / " in es.preview(state)
    for _ in range(3):
        state, _m = es.remove_field(state, 0)
    assert es.preview(state) == "Nothing would be spoken. Add a field."


def test_save_use_rename_delete_cycle() -> None:
    state, _ = es.add_field(_open(), "labels")
    state, message = es.save_draft(state, "  My   issues ")
    assert message == "Saved My issues and now using it for GitHub issues."
    assert state.source == "user:My issues" and not state.dirty
    assert state.library.assignments["github_issues"] == "user:My issues"
    state, message = es.rename_saved(state, "Mine")
    assert (
        message == "Renamed to Mine." and state.library.assignments["github_issues"] == "user:Mine"
    )
    assert es.rename_saved(state, "Brief")[1].startswith("Brief is the name of a built-in")
    state, message = es.delete_saved(state)
    assert message.startswith("Deleted Mine.") and state.source == ""
    assert es.delete_saved(state)[1] == "Only a saved template can be deleted."


def test_reserved_name_is_refused_with_a_sentence() -> None:
    state, message = es.save_draft(_open(), "default")
    assert (
        message.startswith("default is the name of a built-in") and state.library == lib.Library()
    )


def test_assign_builtin_and_back_to_default() -> None:
    state, _ = es.choose_source(_open(), "builtin:brief")
    state, message = es.assign_current(state)
    assert message == "Now used for GitHub issues."
    assert lib.resolve(state.library, "github_issues").template is not None
    state, _ = es.choose_source(state, "")
    state, message = es.assign_current(state)
    assert message == "GitHub issues use the usual wording."
    assert "github_issues" not in state.library.assignments


def test_assign_similar_names_lists_that_keep_their_own() -> None:
    state, _ = es.choose_source(_open("github_pulls"), "builtin:brief")
    state, message = es.assign_current(state, similar=True)
    assert message == "Now used for GitHub pull requests and similar lists."
    assert state.library.assignments["github_issues"] == "builtin:brief"
    # Balanced for pull requests says the review status, which issues do not have.
    state, _ = es.choose_source(_open("github_pulls"), "builtin:balanced")
    state, message = es.assign_current(state, similar=True)
    assert "GitHub issues kept their own choice." in message
    assert "github_issues" not in state.library.assignments


def test_unavailable_fields_are_kept_and_explained() -> None:
    from dataclasses import replace

    state = _open()
    state = replace(state, draft=replace(state.draft, fields=(*state.draft.fields, "reactions")))
    assert "no longer offered" in es.unavailable_note(state) and "reactions" in es.unavailable_note(
        state
    )
    assert "reactions" in state.draft.fields  # kept, not dropped
    assert es.preview(state).count("reactions") == 0


def test_every_list_type_opens() -> None:
    from quill.core.list_speech.catalog import LIST_TYPES

    for kind in LIST_TYPES:
        state = es.start(lib.Library(), kind.id)
        assert es.preview(state) and SPEECH_COLUMN == "row"
