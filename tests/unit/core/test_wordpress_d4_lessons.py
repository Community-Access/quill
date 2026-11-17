"""WP-R-049 (PRD D4): the practice lessons, Break It on Purpose, and the first week.

What these hold the lessons to:

* every Practice Site and Break It lesson stays on the Practice Site;
* every Workbench step teaches the key the window binds;
* each Break It lesson's fixing step is watched for (a check), and the step
  after it reads the list again;
* the first week is seven days, one lesson each, that only do what the person
  chooses -- no Trash, no Delete, no Empty, no Sign Out;
* both editors teach all of it, each in its own command table.
"""

from __future__ import annotations

import pytest

from quill.core.tutorials.wordpress_break_it_lessons import (
    BREAK_TRACK_ID,
    MATERIAL_READY,
    break_it_lessons,
)
from quill.core.tutorials.wordpress_first_week import FIRST_WEEK_TRACK_ID, first_week_lessons
from quill.core.tutorials.wordpress_practice_lessons import (
    FORBIDDEN_COMMANDS,
    PRACTICE_TRACK_ID,
    for_lite,
    practice_only_problems,
)
from quill.core.tutorials.wordpress_practice_more import CHANGED, more_practice_lessons
from quill.core.tutorials.wordpress_practice_sites import site_practice_lessons
from quill.core.wordpress.menu import lite_handler
from quill.core.wordpress.workbench_window_menu import PREFIX, WORDPRESS_KEYS, command
from quill.tools.build_tutorials_reference import catalogue_for

PRACTICE = more_practice_lessons() + site_practice_lessons()
BREAK = break_it_lessons()
WEEK = first_week_lessons(lambda name: f"wordpress.{name}", surfaces=("QUILL",), app="QUILL")
ALL_PRACTICE = PRACTICE + BREAK


def test_the_seven_d4_topics_each_have_a_practice_lesson() -> None:
    assert [t.slug for t in PRACTICE] == [
        "workbench-practice-menus",
        "workbench-practice-people",
        "workbench-practice-updates",
        "workbench-practice-spam",
        "workbench-practice-custom-types",
        "workbench-practice-staging",
        "workbench-practice-site-sets",
    ]
    assert all(t.track == PRACTICE_TRACK_ID for t in PRACTICE)


def test_break_it_sets_up_then_fixes_the_four_problems() -> None:
    assert [t.slug for t in BREAK] == [
        "break-it-set-up",
        "break-it-alt-text",
        "break-it-broken-link",
        "break-it-plugin-conflict",
        "break-it-permalink",
    ]
    assert all(t.track == BREAK_TRACK_ID for t in BREAK)
    set_up = BREAK[0]
    assert MATERIAL_READY in {s.check for s in set_up.steps}
    assert command("practice") in {s.command for s in set_up.steps}


@pytest.mark.parametrize("lesson", BREAK[1:], ids=lambda t: t.slug)
def test_each_fix_is_checked_and_then_heard(lesson) -> None:
    """The fixing step carries a check; a later step reads the place again."""
    checked = [i for i, s in enumerate(lesson.steps) if s.check in (CHANGED, "text-changed")]
    assert checked, lesson.slug
    assert checked[0] < len(lesson.steps) - 1, "nothing after the fix to hear it gone"


@pytest.mark.parametrize("lesson", ALL_PRACTICE, ids=lambda t: t.slug)
def test_each_lesson_stays_on_the_practice_site(lesson) -> None:
    assert practice_only_problems((lesson,)) == []
    assert all(s.command not in FORBIDDEN_COMMANDS for s in lesson.steps)


@pytest.mark.parametrize("lesson", ALL_PRACTICE, ids=lambda t: t.slug)
def test_each_workbench_step_leads_with_the_key_the_window_binds(lesson) -> None:
    for step in lesson.steps:
        if step.command.startswith(PREFIX):
            assert step.command in WORDPRESS_KEYS, step.command
            assert step.keys[0] == WORDPRESS_KEYS[step.command], step.title


def test_the_first_week_is_seven_days_one_lesson_each() -> None:
    assert [t.title.split(":")[0] for t in WEEK] == [f"Day {n}" for n in range(1, 8)]
    assert all(t.track == FIRST_WEEK_TRACK_ID for t in WEEK)
    assert all(t.minutes <= 8 for t in WEEK), "short means short"
    for day, after in zip(WEEK, WEEK[1:], strict=False):
        assert day.then == (after.slug,)


def test_the_first_week_does_nothing_destructive() -> None:
    """These run on a real site: no step may name a command that removes anything."""
    destructive = {"trash", "sign_out", "regenerate_sizes", "site_find_replace", "bulk_edit"}
    named = {s.command.removeprefix("wordpress.") for t in WEEK for s in t.steps if s.command}
    assert named.isdisjoint(destructive), named & destructive
    # The day that publishes says no keeps it a draft, and checks it first.
    publish_day = WEEK[-1]
    names = [s.command for s in publish_day.steps]
    assert names.index("wordpress.check") < names.index("wordpress.publish")
    assert "stays a draft" in publish_day.steps[-1].body


def test_quill_and_quill_lite_teach_the_same_first_week() -> None:
    quill = [t for t in catalogue_for("quill").tutorials if t.track == FIRST_WEEK_TRACK_ID]
    lite = [t for t in catalogue_for("quilllite").tutorials if t.track == FIRST_WEEK_TRACK_ID]
    assert [t.slug for t in quill] == [t.slug for t in lite] == [t.slug for t in WEEK]
    for ours, theirs in zip(quill, lite, strict=True):
        for mine, other in zip(ours.steps, theirs.steps, strict=True):
            if mine.command:
                assert other.command == lite_handler(mine.command)
            assert mine.keys == other.keys


def test_quill_lite_teaches_every_workbench_lesson_in_its_own_table() -> None:
    """Lite opens the same Workbench: the same lessons, editor rows as Lite's handlers,
    Workbench keys kept as literals, and no checks (Lite's lessons watch for nothing)."""
    for track in (PRACTICE_TRACK_ID, BREAK_TRACK_ID):
        quill = [t for t in catalogue_for("quill").tutorials if t.track == track]
        lite = [t for t in catalogue_for("quilllite").tutorials if t.track == track]
        assert [t.slug for t in quill] == [t.slug for t in lite]
        for ours, theirs in zip(quill, lite, strict=True):
            for mine, other in zip(ours.steps, theirs.steps, strict=True):
                assert other.check == ""
                assert other.keys == mine.keys
                if mine.command.startswith(PREFIX):
                    assert other.command == ""
                elif mine.command:
                    assert other.command == lite_handler(mine.command)


def test_for_lite_maps_a_lesson_it_is_given() -> None:
    (lesson,) = for_lite((BREAK[1],))
    assert {s.command for s in lesson.steps} <= {"", "cmd_wp_workbench"}
    assert not any(s.check for s in lesson.steps)


def test_the_checks_are_ones_quill_can_answer() -> None:
    from quill.ui.quill_tutorials import PROBE

    used = {s.check for t in ALL_PRACTICE for s in t.steps if s.check}
    assert used <= PROBE.known()
