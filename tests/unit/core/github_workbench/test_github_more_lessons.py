"""The rest of D8's GitHub lessons, and Help > Tutorials (GH-R-105)."""

from __future__ import annotations

from quill.core.github.workbench_window_menu import GO_NODES, WINDOW_MENU, WORKBENCH_KEYS
from quill.core.tutorials.github_lessons import github_lessons
from quill.core.tutorials.github_lessons_more import more_github_lessons
from quill.core.workbench.menus import all_rows

#: D8's eleven, by slug; the branch rule waits for a way to make one in the Workbench.
D8 = {
    "your first look around": "github-practice-start",
    "triage an inbox": "github-triage-inbox",
    "file an issue with a form": "github-issue-form",
    "review a pull request": "github-first-review",
    "fix a failed run": "github-failed-run",
    "plan a milestone": "github-milestone",
    "organize a project board": "github-project-board",
    "give someone access": "github-give-access",
    "build an issue form": "github-build-form",
    "use the API Console": "github-api-console",
}


def test_every_d8_lesson_but_the_branch_rule_is_there() -> None:
    slugs = {lesson.slug for lesson in github_lessons()}
    assert set(D8.values()) <= slugs


def test_the_track_is_one_chain_ending_with_the_clean_up() -> None:
    lessons = github_lessons()
    assert lessons[-1].slug == "github-practice-finish"
    for here, following in zip(lessons, lessons[1:], strict=False):
        assert here.then == (following.slug,), here.slug


def test_every_step_teaches_the_key_the_window_binds() -> None:
    for lesson in more_github_lessons():
        assert lesson.steps and lesson.summary and lesson.closing, lesson.slug
        for step in lesson.steps:
            assert step.hear, (lesson.slug, step.title)
            if step.command.startswith("github.workbench."):
                assert step.keys == (WORKBENCH_KEYS[step.command],), step.title


def test_help_has_tutorials_on_a_key_and_it_goes_to_help_and_learning() -> None:
    rows = {row.command_id: row for menu, row in all_rows(WINDOW_MENU) if menu.title == "&Help"}
    tutorials = rows["github.workbench.help_tutorials"]
    assert tutorials.label == "&Tutorials" and tutorials.key == "Ctrl+F2"
    assert GO_NODES["github.workbench.help_tutorials"] == ("", "help_tutorials")
