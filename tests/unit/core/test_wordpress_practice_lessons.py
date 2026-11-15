"""The Workbench practice lessons: on the Practice Site only, keys from the window's table."""

from __future__ import annotations

from dataclasses import replace

import pytest

from quill.core.tutorials.model import Step
from quill.core.tutorials.wordpress_practice_lessons import (
    FORBIDDEN_COMMANDS,
    PRACTICE_TRACK_ID,
    practice_lessons,
    practice_only_problems,
)
from quill.core.wordpress.workbench_window_menu import PREFIX, WORDPRESS_KEYS, command
from quill.tools.build_tutorials_reference import catalogue_for

LESSONS = practice_lessons()
SLUGS = ["workbench-practice-start", "workbench-practice-change", "workbench-practice-reset"]


def test_the_three_lessons_cover_start_change_history_undo_and_reset() -> None:
    assert [t.slug for t in LESSONS] == SLUGS
    named = {s.command for t in LESSONS for s in t.steps}
    for verb in ("practice", "go_posts", "sheet", "history", "undo"):
        assert command(verb) in named, verb


@pytest.mark.parametrize("slug", SLUGS)
def test_each_lesson_stays_on_the_practice_site(slug: str) -> None:
    lesson = next(t for t in LESSONS if t.slug == slug)
    assert practice_only_problems((lesson,)) == []
    assert all(s.command not in FORBIDDEN_COMMANDS for s in lesson.steps)


@pytest.mark.parametrize("slug", SLUGS)
def test_each_workbench_step_teaches_the_key_the_window_binds(slug: str) -> None:
    lesson = next(t for t in LESSONS if t.slug == slug)
    for step in lesson.steps:
        if step.command.startswith(PREFIX):
            assert step.command in WORDPRESS_KEYS, step.command
            assert step.keys == (WORDPRESS_KEYS[step.command],), step.title


def test_the_check_catches_a_lesson_that_would_leave_the_practice_site() -> None:
    bad = replace(
        LESSONS[0],
        steps=(
            Step(title="Copy", body="x" * 80, command=command("copy_to_site")),
            Step(title="Elsewhere", body="Open https://radio.example and look around there."),
        ),
    )
    found = practice_only_problems((bad,))
    assert len(found) == 2


def test_both_editors_teach_them_because_both_open_the_workbench() -> None:
    quill = [t.slug for t in catalogue_for("quill").tutorials if t.track == PRACTICE_TRACK_ID]
    assert quill[:4] == [*SLUGS, "workbench-practice-site-care"]  # 9.17 gap 12, same track
    lite = [t.slug for t in catalogue_for("quilllite").tutorials if t.track == PRACTICE_TRACK_ID]
    assert lite == quill
