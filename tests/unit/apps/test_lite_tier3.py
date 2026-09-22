"""The Tier 2 and Tier 3 crossings into QuillLite (bad.md P2.13, P3.6).

Five capabilities QUILL had and QuillLite did not, and the rule that put them
here: a capability that is editor-core, already shared, worth a listener's time
and switchable off belongs in both products (bad.md 4.2). Each of these is a
thing a sighted reader gets from scrolling and glancing.

What is asserted is behaviour, not shape. The gate that brought these tests into
existence (GATE-LITE-COVER) detects a *call*, and it does so because a test that
listed handler names in a table is exactly what let ``cmd_start_extend_selection``
ship with a key, a label, a handler, a passing test, and extend mode that had
never once worked from the keyboard.
"""

from __future__ import annotations

import pytest

DOC = "# Title\n\nFirst paragraph here.\n\n## Section two\n\nSecond paragraph.\n"


@pytest.fixture()
def markdown_window(lite_window):
    """A window holding a Markdown document with two headings in it."""
    return lite_window(DOC, cursor=0, name="notes.md")


# --------------------------------------------------------------------- #
# Extend Selection Mode -- the sticky Shift (P2.13, Tier 2)
# --------------------------------------------------------------------- #


def test_extend_selection_mode_says_it_is_on_and_where_it_started(markdown_window) -> None:
    """The state is invisible: no selection on screen, no changed control, no
    focus move. Silence here is a key that appears to have done nothing."""
    markdown_window.control.SetInsertionPoint(10)

    markdown_window.cmd_toggle_extend_selection_mode()

    assert markdown_window.extend_selection_active() is True
    assert "Extend selection mode on" in markdown_window.announcements[-1]
    assert "line 3" in markdown_window.announcements[-1]


def test_extend_selection_mode_turns_off_again(markdown_window) -> None:
    markdown_window.cmd_toggle_extend_selection_mode()
    markdown_window.cmd_toggle_extend_selection_mode()

    assert markdown_window.extend_selection_active() is False
    assert markdown_window.announcements[-1] == "Extend selection mode off."


def test_escape_leaves_extend_selection_mode(markdown_window) -> None:
    """A separate state from a waiting F8 marker -- the marker is a place, the
    mode is a Shift that stays down. Both are invisible, so both answer Escape."""
    markdown_window.cmd_toggle_extend_selection_mode()

    assert markdown_window.cancel_extend_selection_mode() is True
    assert markdown_window.extend_selection_active() is False
    # And with the mode off it declines the key, so Escape carries on to
    # whatever else would have had it.
    assert markdown_window.cancel_extend_selection_mode() is False


# --------------------------------------------------------------------- #
# The Heading Organizer (P2.13, Tier 2)
# --------------------------------------------------------------------- #


def test_the_heading_organizer_refuses_a_plain_document(lite_window) -> None:
    """Its job is rewriting heading *syntax*, and a .txt has none."""
    win = lite_window("just some text\n", cursor=0, name="notes.txt")
    win.set_document_language("plain", announce=False)

    win.cmd_heading_organizer()

    assert "Markdown or HTML" in win.announcements[-1]


def test_the_heading_organizer_no_longer_refuses_a_rich_document(lite_window) -> None:
    """It used to, and the report was one sentence long: "it should work there".

    It was right. A rich document has headings, ``all_headings`` already listed
    them, and the only thing missing was a way to move a *formatted* range
    rather than a line. What a rich document without the native control gets is
    an honest "needs the Windows Rich Edit control", never the old "needs a
    Markdown or HTML document" -- which was a statement about this editor's
    limits dressed up as a statement about the document.
    """
    win = lite_window("", cursor=0, mode="rich")

    win.cmd_heading_organizer()

    assert "Markdown or HTML" not in win.announcements[-1]


def test_a_cancelled_organizer_changes_nothing_and_says_so(markdown_window, monkeypatch) -> None:
    """A window that opens and closes with no sentence is indistinguishable
    from one that failed."""
    from quill.ui import heading_organizer_dialog as organizer

    monkeypatch.setattr(organizer, "_show_dialog", lambda *_a, **_k: None)

    markdown_window.cmd_heading_organizer()

    assert markdown_window.control.GetValue() == DOC
    assert markdown_window.announcements[-1] == "Heading Organizer cancelled"


def test_the_organizer_writes_its_changes_back_as_one_edit(markdown_window, monkeypatch) -> None:
    """One Replace over the document, because the organizer's changes are a
    single edit as far as the person is concerned and Ctrl+Z should agree."""
    from dataclasses import replace as dataclass_replace

    from quill.ui import heading_organizer_dialog as organizer

    def _promote_everything(_parent, *, headings, **_kwargs):
        return [dataclass_replace(h, level=max(1, h.level - 1)) for h in headings]

    monkeypatch.setattr(organizer, "_show_dialog", _promote_everything)

    markdown_window.cmd_heading_organizer()

    assert "# Section two" in markdown_window.control.GetValue()
    assert markdown_window.modified is True
    assert markdown_window.announcements[-1] == "Applied heading organizer changes"


# --------------------------------------------------------------------- #
# Folding over Markdown sections (P3.6, Tier 3)
# --------------------------------------------------------------------- #


def test_folding_a_section_says_how_many_lines_went_with_it(markdown_window) -> None:
    """The count is the answer to "did I just fold the bit I meant to"."""
    markdown_window.control.SetInsertionPoint(DOC.index("Second paragraph"))

    markdown_window.cmd_toggle_fold()

    assert markdown_window.announcements[-1].startswith("Folded:")
    assert "lines under" in markdown_window.announcements[-1]


def test_folding_the_same_section_again_unfolds_it(markdown_window) -> None:
    markdown_window.control.SetInsertionPoint(DOC.index("Second paragraph"))
    markdown_window.cmd_toggle_fold()

    markdown_window.cmd_toggle_fold()

    assert markdown_window.announcements[-1].startswith("Unfolded:")


def test_a_plain_document_has_nothing_to_fold(lite_window) -> None:
    win = lite_window("one\ntwo\n", cursor=0, name="log.txt")
    win.set_document_language("plain", announce=False)

    win.cmd_toggle_fold()

    assert win.announcements[-1] == "Nothing to fold in this document"


def test_walking_sections_says_the_heading_its_state_and_its_size(markdown_window) -> None:
    """That sentence *is* the skim: it is what a sighted reader gets from
    scrolling past a heading and glancing at how much is under it."""
    markdown_window.control.SetInsertionPoint(0)

    markdown_window.cmd_next_fold()

    said = markdown_window.announcements[-1]
    assert "expanded" in said
    assert "lines" in said


def test_walking_sections_is_undone_by_back(markdown_window) -> None:
    """Every jump in the app is one Alt+Left can undo (bad.md L8)."""
    markdown_window.control.SetInsertionPoint(DOC.index("Second paragraph"))

    markdown_window.cmd_previous_fold()

    assert markdown_window.locations.back(markdown_window.control.GetInsertionPoint()) is not None


def test_unfold_all_says_how_many_it_opened(markdown_window) -> None:
    markdown_window.control.SetInsertionPoint(DOC.index("Second paragraph"))
    markdown_window.cmd_toggle_fold()

    markdown_window.cmd_unfold_all()

    assert markdown_window.announcements[-1] == "Unfolded 1 section"


def test_unfold_all_with_nothing_folded_says_so(markdown_window) -> None:
    """A command that quietly does nothing is indistinguishable, to a listener,
    from a key that is not bound."""
    markdown_window.cmd_unfold_all()

    assert markdown_window.announcements[-1] == "Nothing is folded"


# --------------------------------------------------------------------- #
# The snippet gallery (P3.6, Tier 3)
# --------------------------------------------------------------------- #


def test_the_snippet_gallery_says_when_abbreviations_are_off(markdown_window) -> None:
    markdown_window.app.abbreviations = None

    markdown_window.cmd_snippet_gallery()

    assert "switched off" in markdown_window.announcements[-1]


def test_the_snippet_gallery_inserts_the_one_chosen(markdown_window, monkeypatch) -> None:
    """The half QuillLite did not have: abbreviations expand when you type the
    trigger, which is useless for the fortieth one whose trigger you cannot
    remember."""
    from quill.apps import lite_window_typing as typing_mod
    from quill.core.abbreviations import Abbreviation, AbbreviationLibrary

    entry = Abbreviation(id="a1", abbreviation="sig", expansion="Yours sincerely")
    markdown_window.app.abbreviations = AbbreviationLibrary(version=1, abbreviations=[entry])
    monkeypatch.setattr(typing_mod, "choose_from_rows", lambda *_a, **_k: "a1", raising=False)
    monkeypatch.setattr(
        "quill.apps.lite_dialogs.choose_from_rows", lambda *_a, **_k: "a1", raising=False
    )
    markdown_window.control.SetInsertionPoint(0)

    markdown_window.cmd_snippet_gallery()

    assert "Yours sincerely" in markdown_window.control.GetValue()
    assert markdown_window.announcements[-1] == "Inserted sig"


def test_the_snippet_gallery_says_when_there_are_none(markdown_window, monkeypatch) -> None:
    from quill.core.abbreviations import AbbreviationLibrary

    markdown_window.app.abbreviations = AbbreviationLibrary(version=1, abbreviations=[])

    markdown_window.cmd_snippet_gallery()

    assert "no snippets yet" in markdown_window.announcements[-1]


# --------------------------------------------------------------------- #
# Print preview (P3.6, Tier 3)
# --------------------------------------------------------------------- #


def test_print_preview_says_so_when_there_is_no_printer(markdown_window, monkeypatch) -> None:
    """Not a traceback in the middle of somebody's afternoon."""
    monkeypatch.setattr(type(markdown_window), "_preview_pages", lambda _self: None)

    markdown_window.cmd_print_preview()

    assert "no printer" in markdown_window.announcements[-1].lower()


def test_print_preview_says_the_page_count_out_loud(markdown_window, monkeypatch) -> None:
    """The count is the whole answer for most of the people who asked for this.
    Said as well as shown, because the window's own text is not announced on
    open."""
    monkeypatch.setattr(
        type(markdown_window), "_preview_pages", lambda _self: [["# Title"], ["## Section two"]]
    )
    monkeypatch.setattr(
        "quill.apps.lite_dialogs.show_text_window", lambda *_a, **_k: None, raising=False
    )

    markdown_window.cmd_print_preview()

    assert markdown_window.announcements[-1].startswith("2 pages")


# --------------------------------------------------------------------- #
# The tutorial book (P3.2)
# --------------------------------------------------------------------- #


def test_the_tutorials_window_opens(markdown_window, monkeypatch) -> None:
    """Eight lessons in two tracks, through the window every QuillVille app
    shares -- so a lesson shows your key rather than the shipped one."""
    from quill.apps import lite_tutorials

    opened: list[object] = []
    monkeypatch.setattr(lite_tutorials, "_open", lambda host, app, slug="": opened.append(app))

    markdown_window.cmd_tutorials()

    assert opened and opened[0].app_id == "quilllite"
    assert len(opened[0].catalogue.tutorials) == 8


def test_every_lesson_step_names_a_command_quilllite_has() -> None:
    """A step names a command rather than a key, so the lesson can render the
    key you actually have -- and a step naming a handler that does not exist
    would render keyless and run nothing."""
    from quill.core.lite.commands import COMMANDS
    from quill.core.lite.tutorials import CATALOGUE

    handlers = {h for _m, _l, _k, h, kind in COMMANDS if kind != "sep" and h}
    missing = sorted(
        step.command
        for lesson in CATALOGUE.tutorials
        for step in lesson.steps
        if step.command and step.command not in handlers
    )
    assert missing == [], missing
