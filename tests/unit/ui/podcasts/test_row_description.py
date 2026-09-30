"""The Row Description setting, finally read by something (ear.md R25).

The Off / Brief / Full choice shipped and nothing anywhere consulted it -- and the
reason was structural rather than an oversight: the Manager's episode list is
columns, and there was no description column for a description to go in.
``compose_row``, which does honour the setting, had **no callers at all**.
"""

from __future__ import annotations

from quill.core.podcasts.list_columns import EPISODES
from quill.core.podcasts.row_speech import (
    DESCRIPTION_BRIEF,
    DESCRIPTION_FULL,
    DESCRIPTION_OFF,
    format_description,
)

#: Deliberately longer than BRIEF_LIMIT, or brief and full are the same string
#: and the test would pass without testing anything.
NOTES = "Why chapters are hard, and what we did about it. " * 12


def test_the_episodes_surface_now_has_somewhere_to_put_a_description() -> None:
    ids = [column.id for column in EPISODES.columns]
    assert "description" in ids


def test_the_description_column_is_off_by_default() -> None:
    """A show-notes paragraph on every row is a great deal to arrow past for
    somebody who wanted the titles."""
    column = next(c for c in EPISODES.columns if c.id == "description")
    assert column.default_visible is False


def test_the_sample_row_covers_the_new_column() -> None:
    """The Choose Columns preview would otherwise show a blank for it."""
    assert EPISODES.sample.get("description")


def test_off_says_nothing() -> None:
    assert format_description(NOTES, DESCRIPTION_OFF) == ""


def test_brief_is_shorter_than_full_and_cut_on_a_word() -> None:
    """A description that ends mid-word reads as a fault rather than a summary."""
    from quill.core.podcasts.row_speech import BRIEF_LIMIT

    assert len(NOTES) > BRIEF_LIMIT
    brief = format_description(NOTES, DESCRIPTION_BRIEF)
    full = format_description(NOTES, DESCRIPTION_FULL)
    assert len(brief) < len(full)
    assert brief.endswith("...")
    assert not brief.removesuffix("...").endswith(" ")


def test_notes_shorter_than_the_limit_are_not_truncated() -> None:
    short = "One sentence."
    assert format_description(short, DESCRIPTION_BRIEF) == short


def test_an_episode_with_no_notes_says_nothing_in_any_mode() -> None:
    """It does not fetch anything: a feed that carried no notes has none."""
    for mode in (DESCRIPTION_OFF, DESCRIPTION_BRIEF, DESCRIPTION_FULL):
        assert format_description("", mode) == ""


def test_the_row_builder_asks_the_setting_rather_than_stamping_it() -> None:
    """Asked per row, so changing it takes effect on the next redraw rather than
    on the next feed refresh."""
    import inspect

    from quill.ui.podcasts import manager_row_view

    source = inspect.getsource(manager_row_view.ManagerRowViewMixin._episode_description)
    assert "format_description(" in source
    assert "RowSpeech.from_values(" in source
