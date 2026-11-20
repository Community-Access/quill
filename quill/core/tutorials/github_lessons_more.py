"""The rest of the GitHub lessons of D8 (GitHub PRD D8, GH-R-105).

:mod:`quill.core.tutorials.github_lessons` has the first look round, an
issue, Dry Run, a pull request, a failed run and the clean-up. These are the
other lessons D8 lists, in teaching order: triage your inbox, build an issue
form, file an issue with it, plan a milestone, organize a project board, give
someone access and use the API Console. D8's branch rule lesson waits
for a way to make a rule on one repository from the Workbench.

All but the inbox happen on ``quill-practice``. The inbox lesson works on
your real inbox, so it uses only what changes nothing on GitHub (Snooze is
this computer's own) or what is harmless (marking one notification read).
Giving someone access ends at the preview, because the practice repository
has nobody else to give it to. Where GitHub may refuse a step (a project
needs the project permission), the step says what to do.
"""

from __future__ import annotations

from quill.core.github.practice_repository import PRACTICE_NAME
from quill.core.tutorials.github_lessons import (
    GITHUB_TRACK_ID,
    _go_practice,
    _open_workbench,
    _wb,
)
from quill.core.tutorials.model import Step, Tutorial

__all__ = ["FIRST_MORE", "more_github_lessons"]

_SURFACES = ("GitHub Workbench",)
_MENU = "Shift+F10"
#: The first of these lessons, which the failed-run lesson leads on to.
FIRST_MORE = "github-triage-inbox"
_LAST_THEN = ("github-practice-finish",)


def _context(title: str, body: str, *, hear: str = "", note: str = "") -> Step:
    """A step done from the row's context menu (the command has no key of its own)."""
    return Step(title=title, body=body, keys=(_MENU,), hear=hear, note=note)


def _sheet() -> Step:
    return _wb(
        "properties",
        title="Open its properties",
        body=(
            "Properties shows everything about the row you are on, a page at a time, and "
            "changes what GitHub lets you change."
        ),
        hear="Its properties, on the General page.",
    )


def _triage() -> Tutorial:
    return Tutorial(
        slug="github-triage-inbox",
        title="Triage your inbox",
        track=GITHUB_TRACK_ID,
        minutes=6,
        surfaces=_SURFACES,
        summary=(
            "Work through what is waiting for you: read it, put it off for a day, and "
            "know which review requests are yours and which are your team's."
        ),
        steps=(
            _open_workbench(),
            _wb(
                "go_inbox",
                title="Go to the inbox",
                body=(
                    "Needs My Attention gathers everything waiting on you, across GitHub. "
                    "The Inbox is all of it, newest first."
                ),
                hear="Inbox, and how many rows it has.",
            ),
            Step(
                title="Look at Review Requests",
                body=(
                    "Arrow down the tree to Review Requests. A row that ends in team review "
                    "request was asked of a team you are on, not of you by name, so someone "
                    "else on the team may take it."
                ),
                keys=("Down",),
                hear="Review Requests.",
            ),
            _wb(
                "mark_read",
                title="Mark one read",
                body=(
                    "On a notification you have dealt with, Mark Read. It stays in the list "
                    "but no longer counts as unread, here or on GitHub."
                ),
                hear="Marked read.",
            ),
            _context(
                "Put one off until tomorrow",
                "Open the context menu on a notification and choose Snooze for One Day. "
                "It leaves the list until tomorrow. Only this computer knows; GitHub is "
                "not told.",
                hear="Snoozed here for one day. GitHub was not changed.",
            ),
            _context(
                "Bring it back",
                "Changed your mind? Unsnooze Locally, on the same menu, brings the notification "
                "back into the list now.",
                hear="Unsnoozed here. GitHub was not changed.",
            ),
        ),
        closing=(
            "That is triage: read it, put it off, or open it and deal with it. Mark Done "
            "on the same menu takes a notification out of GitHub's inbox altogether."
        ),
        then=("github-build-form",),
    )


def _build_form() -> Tutorial:
    return Tutorial(
        slug="github-build-form",
        title="Build an issue form",
        track=GITHUB_TRACK_ID,
        minutes=8,
        surfaces=_SURFACES,
        summary=(
            "Make an issue form, the questions people answer when they open an issue, "
            "and save it to the practice repository."
        ),
        steps=(
            _open_workbench(),
            _go_practice(),
            Step(
                title="Go to Templates",
                body=(
                    "Arrow down to Templates under the repository. It lists the issue forms "
                    "and templates the repository already has."
                ),
                keys=("Down",),
                hear="Templates.",
            ),
            _wb(
                "new_here",
                title="Start a new form",
                body=(
                    "New Here, on Templates, asks what to make. Choose Issue form, then "
                    "start from Bug report, so there are questions to look at already."
                ),
                hear="What to make in the repository.",
            ),
            Step(
                title="Name the file",
                body=(
                    "Keep the name it offers, bug-report. That is the file in "
                    ".github/ISSUE_TEMPLATE that GitHub reads."
                ),
                keys=("Enter",),
                hear="The form builder, with the form's questions.",
            ),
            Step(
                title="Look through the questions",
                body=(
                    "Tab to the list of questions and arrow through them. Each says its kind "
                    "(a text box, a drop-down, check boxes) and whether it is required."
                ),
                keys=("Tab", "Down"),
                hear="Each question's label, its kind and whether it is required.",
            ),
            Step(
                title="Save it",
                body=(
                    "Save commits the form to the repository's default branch. QUILL checks "
                    "it first, the way GitHub would, and says anything wrong."
                ),
                hear="Saved, and the file's name.",
                note="Saving is a commit, so it shows in the repository's history.",
            ),
        ),
        closing="The next lesson fills in the form you just made.",
        then=("github-issue-form",),
    )


def _file_with_form() -> Tutorial:
    return Tutorial(
        slug="github-issue-form",
        title="File an issue with a form",
        track=GITHUB_TRACK_ID,
        minutes=5,
        surfaces=_SURFACES,
        summary="Open an issue by answering a form's questions instead of writing it free.",
        steps=(
            _open_workbench(),
            _go_practice(),
            _wb(
                "go_issues",
                title="List the issues",
                body=(
                    "New issues are made from the Issues list, where New Here knows to make "
                    "an issue."
                ),
                hear="Issues, and how many are open.",
            ),
            _wb(
                "new_here",
                title="Start a new issue",
                body=(
                    "New Here on Issues asks which form or template to use. Choose Bug "
                    "report, the form from the last lesson."
                ),
                hear="The forms and templates this repository has.",
            ),
            Step(
                title="Answer the questions",
                body=(
                    "Each question is its own control, labelled as the form labels it. A "
                    "required one says so. Tab moves to the next."
                ),
                keys=("Tab",),
                hear="The first question's label.",
            ),
            Step(
                title="Send it",
                body=(
                    "When the questions are answered, OK files the issue on GitHub, with each "
                    "answer under its question."
                ),
                keys=("Enter",),
                hear="Created, and the issue's number.",
                note=(
                    "A form QUILL cannot fill is said before you start, and a blank issue "
                    "is still offered."
                ),
            ),
        ),
        closing="Forms make every report arrive with the same answers, in the same order.",
        then=("github-milestone",),
    )


def _milestone() -> Tutorial:
    return Tutorial(
        slug="github-milestone",
        title="Plan a milestone",
        track=GITHUB_TRACK_ID,
        minutes=6,
        surfaces=_SURFACES,
        summary="Make a milestone, put issues in it and give it a due date.",
        steps=(
            _open_workbench(),
            _go_practice(),
            _wb(
                "go_issues",
                title="List the issues",
                body=(
                    "A milestone gathers issues towards one goal or date, so start from one "
                    "of the issues."
                ),
                hear="Issues, and how many are open.",
            ),
            _sheet(),
            Step(
                title="Make the milestone",
                body=(
                    "Go to the Organize page. Beside Milestone, New Milestone... asks for a "
                    "name; type First release. It is made on GitHub and chosen at once."
                ),
                keys=("Ctrl+Tab",),
                hear="Created First release.",
            ),
            Step(
                title="Save the issue",
                body=(
                    "OK saves the issue with its milestone. The milestone now counts it as "
                    "one of its open issues."
                ),
                keys=("Enter",),
                hear="Saved.",
            ),
            Step(
                title="Give it a due date",
                body=(
                    "Arrow to Milestones under the repository, then to First release, and "
                    "open its properties. The due date is a field there; type it as "
                    "year-month-day and press OK."
                ),
                keys=("Down", "Alt+Enter"),
                hear="Saved.",
            ),
            _context(
                "See what is in it",
                "On the milestone, open the context menu and choose Find Issues in Milestone. "
                "It lists the milestone's issues, open and closed.",
                hear="Issues, filtered to the milestone.",
            ),
        ),
        closing=(
            "Add the other issues the same way, or put one in from its Milestone... command "
            "on the issue's context menu."
        ),
        then=("github-project-board",),
    )


def _project() -> Tutorial:
    return Tutorial(
        slug="github-project-board",
        title="Organize a project board",
        track=GITHUB_TRACK_ID,
        minutes=8,
        surfaces=_SURFACES,
        summary=(
            "Make a project for the practice repository, put an issue and an idea in it, "
            "and say how it is going."
        ),
        steps=(
            _open_workbench(),
            _go_practice(),
            _wb(
                "go_issues",
                title="List the issues",
                body=(
                    "A project is made from the issue you want in it first, so it starts with "
                    "something on it."
                ),
                hear="Issues, and how many are open.",
            ),
            _sheet(),
            Step(
                title="Make the project",
                body=(
                    "Go to the Projects page. New Project... asks for a name; type Practice "
                    "board. It is made in your account, linked to the repository, and "
                    "checked, so OK puts this issue in it."
                ),
                keys=("Ctrl+Tab", "Enter"),
                hear="Created Practice board.",
                note=(
                    "Projects need the project permission. If GitHub refuses, Account > "
                    "GitHub Permissions adds it in one step."
                ),
            ),
            _wb(
                "go_repo_projects",
                title="Go to the repository's projects",
                body=(
                    "Projects under the repository lists the boards it is linked to, Practice "
                    "board among them."
                ),
                hear="Projects, and Practice board.",
            ),
            _context(
                "Add an idea",
                "On Practice board, Add Draft Issue... puts a note on the board before it is "
                "an issue at all. Type a title; the body can stay empty.",
                hear="Draft issue added to Practice board.",
            ),
            _context(
                "Say how it is going",
                "Post Status Update..., on the same menu, tells everyone who follows the "
                "board whether it is on track. Choose On track.",
                hear="Practice board: status update posted.",
            ),
        ),
        closing=(
            "Each item's own properties set its fields, such as its Status column, and Make "
            "a Draft an Issue... turns an idea into real work."
        ),
        then=("github-give-access",),
    )


def _access() -> Tutorial:
    return Tutorial(
        slug="github-give-access",
        title="Give someone access",
        track=GITHUB_TRACK_ID,
        minutes=6,
        surfaces=_SURFACES,
        summary=(
            "See who has access, make an access template, and preview giving it to a "
            "person, without sending anything."
        ),
        steps=(
            _open_workbench(),
            _go_practice(),
            Step(
                title="See who has access",
                body=(
                    "Arrow to People, then Collaborators and Team Access. On a repository of "
                    "your own, it is you, as admin."
                ),
                keys=("Down",),
                hear="Collaborators and Team Access, and you.",
            ),
            _wb(
                "dry_run",
                title="Turn Dry Run on",
                body=(
                    "Nobody else is in the practice repository, so practise the preview "
                    "only. With Dry Run on, nothing is sent."
                ),
                hear="Dry Run is on.",
            ),
            Step(
                title="Make an access template",
                body=(
                    "Account > Roles and Access > Access Templates..., then New Template.... "
                    f"Name it Contributor and write one line: write on your-name/{PRACTICE_NAME}."
                ),
                hear="Saved Contributor: 1 place.",
                note=(
                    "A template can hold many lines: a role on each repository, and member "
                    "of org/team for a team."
                ),
            ),
            Step(
                title="Preview giving it",
                body=(
                    "Account > Roles and Access > Apply Access Template..., choose "
                    "Contributor, and type any login. The preview says each change in words; "
                    "say No."
                ),
                hear="Invite, the login, with write access.",
            ),
            _wb(
                "dry_run",
                title="Turn Dry Run off",
                body=(
                    "The same command turns Dry Run off again, so the changes you make for real "
                    "are sent."
                ),
                hear="Dry Run is off.",
            ),
        ),
        closing=(
            "On a real repository, the same preview's Yes sends each change and says how "
            "many worked. Change History has every one."
        ),
        then=("github-api-console",),
    )


def _api_console() -> Tutorial:
    return Tutorial(
        slug="github-api-console",
        title="Use the API Console",
        track=GITHUB_TRACK_ID,
        minutes=6,
        surfaces=_SURFACES,
        summary=("Ask GitHub anything it has an API for, and read the answer by arrow keys."),
        steps=(
            _open_workbench(),
            _go_practice(),
            _wb(
                "api_console",
                title="Open the console",
                body=(
                    "The API Console sends any GitHub request. It is for what the Workbench "
                    "has no window for, or to see exactly what GitHub says."
                ),
                hear="GitHub API Console.",
            ),
            Step(
                title="Ask about the repository",
                body=(
                    f"Leave Method as GET. In Path, type /repos/your-name/{PRACTICE_NAME}. "
                    "What it does names the request before anything is sent."
                ),
                keys=("Tab",),
                hear="What it does, naming the request and what it needs.",
            ),
            Step(
                title="Send it",
                body=(
                    "Press Send. A GET only asks a question, so it goes at once, with nothing "
                    "to confirm."
                ),
                hear="The answer, as a tree.",
            ),
            Step(
                title="Read the answer",
                body=(
                    "Tab to the answer and arrow through it. Each field is a row; Right "
                    "opens one that has more inside."
                ),
                keys=("Tab", "Down", "Right"),
                hear="Each field's name and value.",
                note=(
                    "A request that changes something asks you to type its method first, "
                    "and needs Full access for this account in the Workbench."
                ),
            ),
        ),
        closing="That is the track's last new tool. The next lesson clears up.",
        then=_LAST_THEN,
    )


def more_github_lessons() -> tuple[Tutorial, ...]:
    """The other GitHub lessons D8 lists, in teaching order."""
    return (
        _triage(),
        _build_form(),
        _file_with_form(),
        _milestone(),
        _project(),
        _access(),
        _api_console(),
    )
