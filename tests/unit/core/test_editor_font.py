"""The size of the text, and the one rule that keeps a rich document intact.

QUILL could not change the size of its own text at all until 2026-09-16: no
``SetFont`` on any editor control, no font setting, no zoom command. For an
audience that includes low-vision users that is not a missing preference, it is
the product not working, and it is the largest of the sixteen ways QuillLite was
ahead of the editor (bad.md 4.3, the P0 viability bar).

The rule worth testing is the rich/plain split. In a rich document the run point
sizes *are* the heading ladder, so applying the user's chosen size with SetFont
would flatten a Heading 1 and a body paragraph to one size -- and heading
navigation and the headings list would follow it down, because they read the
ladder.
"""

from __future__ import annotations

import pytest

from quill.core.editor_font import (
    DEFAULT_FONT_POINTS,
    MAX_FONT_POINTS,
    MIN_FONT_POINTS,
    clamp_font_points,
    editor_points_for,
    sets_font,
    zoom_for,
)
from quill.core.heading_ladder import BODY_POINT_SIZE


def test_a_plain_document_gets_the_size_you_asked_for() -> None:
    assert editor_points_for(18, rich=False) == 18.0


def test_a_rich_document_is_not_given_a_font_at_all() -> None:
    """bad.md R5. SetFont on wxMSW applies to the WHOLE control, existing runs
    included, so calling it on a rich document flattens the heading ladder no
    matter which size is passed -- the body size included, which is what both
    editors used to pass. The zoom is the entire answer there."""
    assert sets_font(rich=False) is True
    assert sets_font(rich=True) is False


def test_the_fallback_size_for_a_caller_that_ignores_that_is_the_body_size() -> None:
    assert editor_points_for(18, rich=True) == BODY_POINT_SIZE


def test_a_rich_document_zooms_by_what_was_asked_over_the_ladder() -> None:
    assert zoom_for(22, rich=True) == (22, int(BODY_POINT_SIZE))


def test_a_plain_document_never_zooms() -> None:
    """The font itself changed; zooming as well would double the effect."""
    assert zoom_for(22, rich=False) == (0, 0)


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (0, MIN_FONT_POINTS),
        (400, MAX_FONT_POINTS),
        (MIN_FONT_POINTS, MIN_FONT_POINTS),
        (MAX_FONT_POINTS, MAX_FONT_POINTS),
        (14, 14),
        ("14", 14),
        (14.6, 14),
    ],
)
def test_a_size_is_clamped_rather_than_refused(given: object, expected: int) -> None:
    """A hand-edited settings file with a size of 400 should give somebody a
    readable editor, not an editor that will not start."""
    assert clamp_font_points(given) == expected


@pytest.mark.parametrize("given", [None, "large", object(), True, [12]])
def test_nonsense_gives_the_default(given: object) -> None:
    assert clamp_font_points(given) == DEFAULT_FONT_POINTS


def test_both_editors_read_the_same_two_settings() -> None:
    """QuillLite's field names, deliberately, so a settings file carried between
    the two products means the same thing in both (bad.md G1)."""
    from quill.core.lite.settings import Settings as LiteSettings
    from quill.core.settings import Settings as QuillSettings

    for settings in (LiteSettings(), QuillSettings()):
        assert hasattr(settings, "font_name")
        assert hasattr(settings, "font_size")


def test_quill_clamps_a_nonsense_size_it_reads_back() -> None:
    """A hand-edited settings file with a size of 900 must not be able to make
    the editor unusable -- it gives the largest readable size instead."""
    from quill.core.settings import Settings

    settings = Settings.from_dict({"font_size": 900, "font_name": "Consolas"})
    assert settings.font_size == MAX_FONT_POINTS
    assert settings.font_name == "Consolas"

    assert Settings.from_dict({"font_size": "nonsense"}).font_size == DEFAULT_FONT_POINTS
