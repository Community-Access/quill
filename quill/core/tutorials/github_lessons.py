"""The GitHub lessons, on the practice repository (GitHub PRD 22.8 and D8).

Six short lessons in the shared tutorials engine. Every one works in
``quill-practice``, the private repository Help > Practice on GitHub... makes
in your own account, so nothing a lesson asks you to change matters to anyone:
make it and look round; your first issue (label, comment, close); Dry Run;
reviewing and merging a pull request; reading a failed run; and deleting the
repository when you are done.

A step about a Workbench command names it and carries the key from the
Workbench's own table (:data:`~quill.core.github.workbench_window_menu.WORKBENCH_KEYS`),
so the key a lesson teaches is the key the window binds. Commands with no key
of their own are reached from the context menu, and the step says so.
"""

from __future__ import annotations

from quill.core.github.practice_repository import PRACTICE_NAME
from quill.core.github.workbench_window_menu import WORKBENCH_KEYS
from quill.core.tutorials.model import Step, Track, Tutorial

__all__ = ["GITHUB_TRACK", "GITHUB_TRACK_ID", "github_lessons"]

GITHUB_TRACK_ID = "github"
GITHUB_TRACK = Track(
    GITHUB_TRACK_ID,
    "GitHub, on a practice repository",
    "Make a private repository to practise on, then file and close an issue, "
    "try Dry Run, review and merge a pull request, read a failed run, and "
    "delete the repository when you finish.",
)

_SURFACES = ("GitHub Workbench",)
_MENU = "Shift+F10"


def _wb(verb: str, *, title: str, body: str, hear: str = "", note: str = "") -> Step:
    """A step about a Workbench command, with the key the window binds."""
    command_id = f"github.workbench.{verb}"
    key = WORKBENCH_KEYS.get(command_id, "")
    return Step(
        title=title,
        body=body,
        command=command_id if key else "",
        keys=(key,) if key else (),
        hear=hear,
        note=note,
    )


def _open_workbench() -> Step:
    return Step(
        title="Open the GitHub Workbench",
        body=(
            "The Workbench is the window for everything on GitHub. Open it from the "
            "editor's GitHub menu, signed in with the account you want to practise in."
        ),
        command="file.open_github_items",
        hear="GitHub Workbench, and its tree.",
    )


def _go_practice() -> Step:
    return _wb(
        "practice",
        title="Go to the practice repository",
        body=(
            f"Choose Practice on GitHub from the Help menu, then Open It. The tree moves "
            f"to {PRACTICE_NAME} in your account."
        ),
        hear=f"{PRACTICE_NAME} is ready to practise on.",
    )


def github_lessons() -> tuple[Tutorial, ...]:
    """The six GitHub lessons, in teaching order."""
    track = GITHUB_TRACK_ID
    return (
        Tutorial(
            slug="github-practice-start",
            title="Make a repository to practise on",
            track=track,
            minutes=5,
            surfaces=_SURFACES,
            summary=(
                f"Make {PRACTICE_NAME}, a private repository with issues, a pull request "
                "and a failing run, and find your way round it."
            ),
            steps=(
                _open_workbench(),
                _wb(
                    "practice",
                    title="Make the practice repository",
                    body=(
                        "Choose Practice on GitHub from the Help menu. QUILL says what it will "
                        "make and asks first; say Yes. It is private, in your own account, and "
                        "nothing else of yours is touched."
                    ),
                    hear="Made, private, with a workflow that fails on purpose, 3 issues.",
                    note="Making it takes a few seconds; you hear each part as it is made.",
                ),
                Step(
                    title="Look round",
                    body=(
                        "The tree is now at the repository. Arrow down through its places: "
                        "Issues, Pull Requests, Runs and the rest. Enter on one lists it."
                    ),
                    keys=("Down", "Enter"),
                    hear="Issues, and a count of open issues.",
                ),
            ),
            closing=(
                "You have somewhere to make mistakes. The next lessons all happen here, and "
                "the last one deletes it."
            ),
            then=("github-first-issue",),
        ),
        Tutorial(
            slug="github-first-issue",
            title="Label, comment on and close an issue",
            track=track,
            minutes=6,
            surfaces=_SURFACES,
            summary="Work one issue from start to finish: a label, a comment, and closing it.",
            steps=(
                _open_workbench(),
                _go_practice(),
                _wb(
                    "go_issues",
                    title="List the issues",
                    body=(
                        "Go to the repository's Issues. The list holds the three practice issues, "
                        "newest first."
                    ),
                    hear="Issues, 3 shown.",
                ),
                Step(
                    title="Label the typo",
                    body=(
                        "Select the issue about the greeting's typo and open its context menu. "
                        "Choose Labels, and check practice: bug."
                    ),
                    keys=(_MENU,),
                    hear="Labels for the issue, and the practice labels.",
                ),
                _wb(
                    "comment",
                    title="Comment on it",
                    body=(
                        "Open the comment window, write a line saying you will fix it, and "
                        "post it. Preview reads it to you first if you like."
                    ),
                    hear="Comment on, and the issue's number.",
                ),
                Step(
                    title="Close it as completed",
                    body=(
                        "From the context menu choose Close or Reopen. QUILL asks why, as GitHub "
                        "does; choose Completed."
                    ),
                    keys=(_MENU,),
                    hear="Closed as completed.",
                ),
            ),
            closing="That is the whole life of most issues: a label, a word, and closing it.",
            then=("github-dry-run",),
        ),
        Tutorial(
            slug="github-dry-run",
            title="Try a command without sending it",
            track=track,
            minutes=4,
            surfaces=_SURFACES,
            summary="Turn Dry Run on, walk through a command, hear what it would have sent.",
            steps=(
                _open_workbench(),
                _go_practice(),
                _wb(
                    "dry_run",
                    title="Turn Dry Run on",
                    body=(
                        "Turn Dry Run on from the Tools menu. Every write now asks and previews "
                        "as usual, then stops."
                    ),
                    hear="Dry Run is on.",
                ),
                Step(
                    title="Try closing an issue",
                    body=(
                        "Select an open issue, choose Close or Reopen from its context menu and "
                        "answer the question as if you meant it."
                    ),
                    keys=(_MENU,),
                    hear="Dry run: QUILL would send PATCH, and Nothing was changed.",
                ),
                _wb(
                    "dry_run",
                    title="Turn it off again",
                    body=(
                        "The same command turns Dry Run off, and writes go to GitHub again. It "
                        "is also off whenever QUILL starts."
                    ),
                    hear="Dry Run is off.",
                ),
            ),
            closing="Use Dry Run whenever you want to see a command through before it counts.",
            then=("github-first-review",),
        ),
        Tutorial(
            slug="github-first-review",
            title="Review and merge a pull request",
            track=track,
            minutes=8,
            surfaces=_SURFACES,
            summary="Read a pull request's change, find out whether it can merge, and merge it.",
            steps=(
                _open_workbench(),
                _go_practice(),
                _wb(
                    "go_pulls",
                    title="List the pull requests",
                    body=(
                        "Go to the repository's Pull Requests and select the one that fixes the "
                        "greeting."
                    ),
                    hear="Pull Requests, 1 shown.",
                ),
                _wb(
                    "diff",
                    title="Read the change",
                    body=(
                        "Open its file differences. In the patch lines, check Changed Lines "
                        "Only and arrow through: an added and a removed line each have a sound."
                    ),
                    hear="PR diff, and the changed file.",
                ),
                Step(
                    title="Ask whether it can merge",
                    body=(
                        "Close the diff. From the pull request's context menu choose Why "
                        "Can't I Merge? It names the commit its answer is about."
                    ),
                    keys=(_MENU,),
                    hear="can merge into main, as of commit",
                    note="The practice run fails on purpose, but it is not a required check.",
                ),
                _wb(
                    "merge",
                    title="Merge it",
                    body=(
                        "Merge it. QUILL checks again, asks how to merge, and asks you to type "
                        "the number, then merges only the commit it checked, nothing newer."
                    ),
                    hear="Merged, and the new commit.",
                ),
            ),
            closing="Reading, asking and merging is most of what a reviewer does all day.",
            then=("github-failed-run",),
        ),
        Tutorial(
            slug="github-failed-run",
            title="Read a failed run",
            track=track,
            minutes=5,
            surfaces=_SURFACES,
            summary="Find out why a workflow run failed, and run only what failed again.",
            steps=(
                _open_workbench(),
                _go_practice(),
                _wb(
                    "go_runs",
                    title="List the runs",
                    body=(
                        "Go to the repository's Runs and select a failed one. The practice "
                        "workflow fails every time."
                    ),
                    hear="failure, Practice checks.",
                ),
                _wb(
                    "what_failed",
                    title="Read what failed",
                    body=(
                        "Open What Failed: the failing step and its last log lines, as one text "
                        "you can read with the arrows."
                    ),
                    hear="What failed, and Fail on purpose.",
                ),
                _wb(
                    "rerun_failed",
                    title="Run only the failure again",
                    body=(
                        "Close the text and re-run the failed jobs. It will fail again, which "
                        "is the point here; in a real repository you would fix it first."
                    ),
                    hear="re-run",
                ),
            ),
            closing="What Failed is usually all you need; the jobs window has the whole log.",
            then=("github-practice-finish",),
        ),
        Tutorial(
            slug="github-practice-finish",
            title="Delete the practice repository",
            track=track,
            minutes=2,
            surfaces=_SURFACES,
            summary=f"Delete {PRACTICE_NAME}, or start it over fresh.",
            steps=(
                _open_workbench(),
                _wb(
                    "practice",
                    title="Delete it",
                    body=(
                        "Choose Practice on GitHub from the Help menu, then Delete It, and say "
                        "Yes. Delete It and Start Over makes a fresh one instead."
                    ),
                    hear=f"Deleted, and {PRACTICE_NAME}.",
                    note=(
                        "GitHub lets an app delete a repository only with the delete_repo "
                        "permission; without it, QUILL says where on GitHub to delete it."
                    ),
                ),
            ),
            closing="That is the track. Everything you practised works the same on real work.",
        ),
    )
