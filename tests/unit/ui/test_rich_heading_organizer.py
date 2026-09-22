r"""The Heading Organizer over a rich document, on the real control.

"It should work there." The organizer refused in rich text on the grounds that a
rich heading is a point size on a run, so reordering sections means moving
formatted ranges rather than lines. That was true about the mechanism and wrong
about the conclusion -- those documents have headings, ``all_headings`` already
listed them, and the answer was to move formatted ranges rather than to withhold
the window.

Driven against the live RICHEDIT50W, and that is not optional here: the entire
question is whether formatting survives the move, and a mock would answer yes
whatever the code did. Skipped where there is no native control.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
import wx

from quill.core.markdown_sections import HeadingBlock
from quill.ui.heading_organizer_rich import (
    apply_rich_organizer_edits,
    rich_heading_blocks,
    unchanged,
)


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture()
def rich(wx_app):
    """A rich document of three headed sections, on the real control."""
    from quill.ui.richedit_rtf_surface import create_richedit_rtf

    frame = wx.Frame(None, size=(900, 600))
    control = create_richedit_rtf(wx, frame, wx.TE_MULTILINE)
    wrapper = getattr(control, "quill_richedit", None)
    if wrapper is None or not wrapper.rtf_available():
        frame.Destroy()
        pytest.skip("no native Rich Edit / TOM on this build")
    wrapper.set_text_mode("rich")
    control.SetValue("Alpha\nbody a\nBravo\nbody b\nCharlie\nbody c\n")
    frame.Show()
    wx_app.Yield()
    for needle, level in (("Alpha", 1), ("Bravo", 2), ("Charlie", 3)):
        start = control.GetValue().find(needle)
        control.SetSelection(start, start + len(needle))
        wrapper.set_heading(level)
    wx_app.Yield()
    yield control, wrapper
    frame.Destroy()
    wx_app.Yield()


def _blocks(control, wrapper) -> list[HeadingBlock]:
    return rich_heading_blocks(control.GetValue(), wrapper.all_headings())


def test_the_headings_are_found_at_all(rich) -> None:
    control, wrapper = rich
    blocks = _blocks(control, wrapper)
    assert [block.title for block in blocks] == ["Alpha", "Bravo", "Charlie"]
    assert [block.level for block in blocks] == [1, 2, 3]


def test_a_section_runs_to_the_next_heading(rich) -> None:
    """The Markdown parser's convention, because the apply step is shared."""
    control, wrapper = rich
    blocks = _blocks(control, wrapper)
    text = control.GetValue()
    assert text[blocks[0].section_start : blocks[0].section_end] == "Alpha\nbody a\n"


def test_reordering_moves_the_words(rich, wx_app) -> None:
    control, wrapper = rich
    blocks = _blocks(control, wrapper)
    apply_rich_organizer_edits(wrapper, blocks, [blocks[2], blocks[0], blocks[1]])
    wx_app.Yield()
    assert control.GetValue() == "Charlie\nbody c\nAlpha\nbody a\nBravo\nbody b\n"


def test_reordering_keeps_every_heading_at_its_level(rich, wx_app) -> None:
    """The whole question. Moving lines as text would arrive unformatted and
    flatten all three headings into body text on the way."""
    control, wrapper = rich
    blocks = _blocks(control, wrapper)
    apply_rich_organizer_edits(wrapper, blocks, [blocks[2], blocks[0], blocks[1]])
    wx_app.Yield()
    assert [(level, title) for _start, level, title in wrapper.all_headings()] == [
        (3, "Charlie"),
        (1, "Alpha"),
        (2, "Bravo"),
    ]


def test_a_level_change_is_applied_to_the_moved_heading(rich, wx_app) -> None:
    control, wrapper = rich
    blocks = _blocks(control, wrapper)
    promoted = replace(blocks[2], level=1)
    apply_rich_organizer_edits(wrapper, blocks, [promoted, blocks[0], blocks[1]])
    wx_app.Yield()
    levels = {title: level for _start, level, title in wrapper.all_headings()}
    assert levels["Charlie"] == 1
    assert levels["Alpha"] == 1
    assert levels["Bravo"] == 2


def test_a_rename_keeps_the_heading_a_heading(rich, wx_app) -> None:
    """A renamed heading that came back as body text would be a rename that
    silently demoted it -- invisible to somebody who cannot see the size."""
    control, wrapper = rich
    blocks = _blocks(control, wrapper)
    renamed = replace(blocks[0], title="Alpha renamed")
    apply_rich_organizer_edits(wrapper, blocks, [renamed, blocks[1], blocks[2]])
    wx_app.Yield()
    found = {title: level for _start, level, title in wrapper.all_headings()}
    assert found.get("Alpha renamed") == 1


def test_text_above_the_first_heading_is_not_eaten(rich, wx_app) -> None:
    """A title line, a note, a stray blank line: not part of any section, and
    the organizer has no business dropping it."""
    control, wrapper = rich
    control.SetValue("a preamble\nAlpha\nbody a\nBravo\nbody b\n")
    wx_app.Yield()
    for needle, level in (("Alpha", 1), ("Bravo", 2)):
        start = control.GetValue().find(needle)
        control.SetSelection(start, start + len(needle))
        wrapper.set_heading(level)
    wx_app.Yield()
    blocks = _blocks(control, wrapper)
    apply_rich_organizer_edits(wrapper, blocks, [blocks[1], blocks[0]])
    wx_app.Yield()
    assert control.GetValue().startswith("a preamble\n")
    assert "Bravo" in control.GetValue()
    assert "Alpha" in control.GetValue()


def test_one_undo_takes_the_whole_reorder_back(rich, wx_app) -> None:
    """The user did one thing, so Ctrl+Z is one thing."""
    control, wrapper = rich
    before = control.GetValue()
    blocks = _blocks(control, wrapper)
    apply_rich_organizer_edits(wrapper, blocks, [blocks[2], blocks[1], blocks[0]])
    wx_app.Yield()
    assert control.GetValue() != before
    control.Undo()
    wx_app.Yield()
    assert control.GetValue() == before


def test_nothing_to_do_is_recognised(rich) -> None:
    control, wrapper = rich
    blocks = _blocks(control, wrapper)
    assert unchanged(blocks, list(blocks))
    assert not unchanged(blocks, [blocks[1], blocks[0], blocks[2]])
