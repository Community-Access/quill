"""Nothing reloads under your hands without being asked (bad.md F5, P0.7).

QUILL replaced a clean tab in place whenever the file changed on disk, for any
suffix, by calling ``path.read_text()``. For a text file a build regenerates
that is convenient. For a ``.docx`` rewritten by Word it replaced the document
with its own compressed bytes decoded into replacement characters and marked the
result clean -- and said nothing, so the only cue was that the text no longer
read as words, which is no cue at all to somebody listening rather than looking.

Decided 2026-09-18: ask for every format, with a "do not ask me again for this
format" answer on the question, so a build that rewrites .md files every few
seconds is answered once rather than every time.
"""

from __future__ import annotations

from quill.core.external_change import (
    CHANGE_DELETED,
    CHANGE_MODIFIED,
    CHANGE_NONE,
    REMEMBER_KEEP,
    REMEMBER_RELOAD,
    ReloadAction,
    decide_reload,
    format_key,
    remembered_answer,
)
from quill.core.settings import Settings, _suffix_list


def test_a_clean_tab_is_asked_about_not_replaced() -> None:
    decision = decide_reload(CHANGE_MODIFIED, buffer_dirty=False, file_name="report.docx")
    assert decision.action is ReloadAction.PROMPT_CLEAN
    assert decision.needs_prompt


def test_the_blanket_switch_still_reloads_for_anyone_who_wants_it() -> None:
    decision = decide_reload(
        CHANGE_MODIFIED,
        buffer_dirty=False,
        auto_reload_when_clean=True,
        file_name="build.md",
    )
    assert decision.action is ReloadAction.RELOAD


def test_a_dirty_tab_is_still_never_overwritten_silently() -> None:
    decision = decide_reload(CHANGE_MODIFIED, buffer_dirty=True, file_name="notes.md")
    assert decision.action is ReloadAction.PROMPT_CONFLICT


def test_a_remembered_reload_does_not_ask_again() -> None:
    decision = decide_reload(
        CHANGE_MODIFIED,
        buffer_dirty=False,
        file_name="build.md",
        remembered=REMEMBER_RELOAD,
    )
    assert decision.action is ReloadAction.RELOAD
    assert "build.md" in decision.announcement


def test_a_remembered_keep_says_it_is_keeping_what_is_open() -> None:
    decision = decide_reload(
        CHANGE_MODIFIED,
        buffer_dirty=False,
        file_name="report.docx",
        remembered=REMEMBER_KEEP,
    )
    assert decision.action is ReloadAction.KEEP_MINE
    assert "Keeping what is open" in decision.announcement


def test_a_remembered_answer_never_applies_to_a_deleted_file() -> None:
    """Deletion is a different question, and the answer to it is never "reload"."""
    decision = decide_reload(
        CHANGE_DELETED,
        buffer_dirty=False,
        file_name="report.docx",
        remembered=REMEMBER_RELOAD,
    )
    assert decision.action is ReloadAction.PROMPT_DELETED


def test_watching_off_and_no_change_still_do_nothing() -> None:
    assert decide_reload(CHANGE_NONE, buffer_dirty=False).action is ReloadAction.NONE
    assert (
        decide_reload(CHANGE_MODIFIED, buffer_dirty=False, watch_enabled=False).action
        is ReloadAction.NONE
    )


# -- the remembered answers themselves -----------------------------------------


def test_the_answer_is_keyed_on_the_format_not_the_file() -> None:
    assert format_key("Report FINAL.DOCX") == ".docx"
    assert format_key("Makefile") == ""


def test_a_format_with_no_answer_is_asked_about() -> None:
    assert remembered_answer("a.md", always_reload=[".docx"]) == ""


def test_a_remembered_format_is_matched_case_insensitively() -> None:
    assert remembered_answer("A.MD", always_reload=[".md"]) == REMEMBER_RELOAD
    assert remembered_answer("a.md", always_keep=["MD"]) == ""  # keys carry the dot


def test_reload_wins_a_format_listed_in_both() -> None:
    """Of the two ways to be wrong, quietly showing stale text is the unnoticed one."""
    answer = remembered_answer("a.md", always_reload=[".md"], always_keep=[".md"])
    assert answer == REMEMBER_RELOAD


def test_a_file_with_no_extension_is_never_answered_for_you() -> None:
    assert remembered_answer("Makefile", always_reload=[""]) == ""


def test_the_stored_list_survives_a_hand_edited_settings_file() -> None:
    """An entry somebody got wrong costs that entry, not the app starting."""
    assert _suffix_list(["DOCX", " .md ", "", 3, ".md", None]) == [".docx", ".md"]
    assert _suffix_list("not a list") == []


def test_nothing_is_answered_for_you_out_of_the_box() -> None:
    settings = Settings()
    assert settings.external_change_auto_reload_when_clean is False
    assert settings.external_change_always_reload == []
    assert settings.external_change_always_keep == []
