"""The coding lesson, shared by QUILL and QUILL Lite (code.md 5.9): your first project task.

Open a sample project, ask for a small change, review it, run the tests, and
undo the turn: the whole loop once, slowly, with what you should hear at each
step. It belongs to the Developer profile, so each editor shows the Coding
track only while coding is on (:func:`quill.core.tutorials.model.without_track`).

*ids* maps the lesson's actions to each editor's commands, as the dictation
lessons do, so one text teaches both and the keys render live.
"""

from __future__ import annotations

from collections.abc import Mapping

from quill.core.tutorials.model import Step, Track, Tutorial

__all__ = ["CODING_TRACK", "CODING_TRACK_ID", "coding_lessons"]

CODING_TRACK_ID = "coding"

CODING_TRACK = Track(
    CODING_TRACK_ID,
    "Coding, in the Developer profile",
    "Work on a folder of code with an AI: ask for a change, review every edit, "
    "allow the commands it runs, hear the test results, and undo a whole turn.",
)


def coding_lessons(ids: Mapping[str, str], *, surfaces: tuple[str, ...]) -> tuple[Tutorial, ...]:
    """The lesson. *ids*: ``open_folder``, ``task``, ``undo``, ``stop``."""
    return (
        Tutorial(
            slug="first-project-task",
            title="Your first project task",
            track=CODING_TRACK_ID,
            minutes=12,
            surfaces=surfaces,
            summary=(
                "Open a small project, ask for one change, review it, let the agent run "
                "the tests, hear the result, and put everything back with one command."
            ),
            steps=(
                Step(
                    title="Make a practice folder",
                    body=(
                        "Make an empty folder and put one small file of code in it, such "
                        "as a Python file with a function that has a mistake in it. A "
                        "project is just a folder; nothing in it is changed until you say."
                    ),
                    note=(
                        "Use a copy, not your real work, the first time. Undo Last Turn "
                        "puts files back, but practising on a copy costs nothing."
                    ),
                ),
                Step(
                    title="Open the folder as a project",
                    body=(
                        "Open Project Folder is in the File menu. Choose Browse for a "
                        "Folder and pick your practice folder. The status bar's Project "
                        "cell now names it."
                    ),
                    command=ids["open_folder"],
                    hear="Project, and the folder's name, is open.",
                ),
                Step(
                    title="Ask for one small change",
                    body=(
                        "Press the task command. With a project open it starts a project "
                        "task rather than a document task. Type one plain request, such as "
                        "fix the add function and run the tests, and press Enter."
                    ),
                    command=ids["task"],
                    hear='Nothing at first; then "The plan is ready", with the number of steps.',
                    note=(
                        "The first time, QUILL may ask whether to use the project's notes "
                        "for AI agents, if it has any. Read Them First shows them."
                    ),
                ),
                Step(
                    title="Read the plan",
                    body=(
                        "Press Alt+P in the task window to put the cursor on the plan, and "
                        "read it with the arrow keys. Nothing has changed yet."
                    ),
                    keys=("Alt+P",),
                ),
                Step(
                    title="Review the change",
                    body=(
                        "When the agent has an edit, Review Changes opens on a list of "
                        "files. Press Enter on a file, read the change with its line "
                        "numbers, and Accept or Reject it. Apply Accepted Changes writes "
                        "what you accepted; Reject All writes nothing."
                    ),
                    hear="The window's own title and the first file's row.",
                ),
                Step(
                    title="Allow the test command",
                    body=(
                        "Run This Command? shows the exact command. Arrow through it, then "
                        "Allow once. A warning line appears only when QUILL sees a risk, "
                        "such as reaching the internet."
                    ),
                    hear='The result in one sentence, such as "Tests: 3 passed."',
                ),
                Step(
                    title="Undo the whole turn",
                    body=(
                        "Undo Last Agent Turn, in Edit under Agent Work, puts every file the "
                        "turn changed back as it was and removes files it made."
                    ),
                    command=ids["undo"],
                    hear='"Undid turn 1", and which files are back.',
                    note=(
                        "If you edited one of those files yourself since, undo refuses and "
                        "offers to show you the file as it was, so nothing of yours is lost."
                    ),
                ),
                Step(
                    title="Try coach mode",
                    body=(
                        "Check Coach mode (Alt+A) in the task window and ask how to fix the "
                        "mistake yourself. The agent explains and points to a file and line; "
                        "you make the change in the editor."
                    ),
                    keys=("Alt+A",),
                    note=f"Stop Agent stops a task from any window: {ids['stop_label']}.",
                ),
            ),
            closing=(
                "That is the whole loop. Every change is reviewed before it is written, "
                "every command asks first, and one command undoes a turn."
            ),
        ),
    )
