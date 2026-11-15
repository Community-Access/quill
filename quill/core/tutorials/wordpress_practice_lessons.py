"""Three WordPress Workbench lessons that run only against the Practice Site.

The Practice Site is a WordPress on this computer (``127.0.0.1:9400``) that
nobody else can see, so these lessons can ask somebody to change a post, look
at Change History, undo, and finally reset the whole site, without risking
anything real. Every step that touches content happens on the Practice Site:
the lessons start it, connect it, move to it by name, and never name another
site or a command that sends anything to one (Copy to Site, Make Them the
Same, Publish). :func:`practice_only_problems` states that rule as a check,
and the catalogue test calls it.

The Workbench is QUILL's own window -- QUILL Lite does not have it -- so the
track is QUILL's alone. Each step names the Workbench command and carries the
key from the Workbench's own menu table (:data:`WORDPRESS_KEYS`), so the key
a lesson teaches is the key the window binds.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Track, Tutorial
from quill.core.wordpress.workbench_practice import PRACTICE_NAME, site_url
from quill.core.wordpress.workbench_window_menu import WORDPRESS_KEYS, command

__all__ = [
    "FORBIDDEN_COMMANDS",
    "PRACTICE_TRACK",
    "PRACTICE_TRACK_ID",
    "practice_lessons",
    "practice_only_problems",
]

PRACTICE_TRACK_ID = "wordpress-practice"
PRACTICE_TRACK = Track(
    PRACTICE_TRACK_ID,
    "The WordPress Workbench, on the Practice Site",
    "Start a WordPress site on this computer, change a post there, read Change "
    "History, undo, and reset the site -- all with nothing real at stake.",
)

#: Commands that send work to another site. No practice lesson may name one.
FORBIDDEN_COMMANDS = frozenset({
    command("copy_to_site"),
    command("make_same"),
    command("publish"),
    command("plain_batch"),
})

#: Where the Practice Site answers, as the lessons say it.
ADDRESS = site_url()


def _wb(verb: str) -> tuple[str, tuple[str, ...]]:
    """A Workbench command id and its key from the window's own table."""
    command_id = command(verb)
    key = WORDPRESS_KEYS.get(command_id, "")
    return command_id, ((key,) if key else ())


def _step(verb: str, **fields: str) -> Step:
    command_id, keys = _wb(verb)
    return Step(command=command_id, keys=keys, **fields)


def practice_lessons(
    *, surfaces: tuple[str, ...] = ("WordPress Workbench",)
) -> tuple[Tutorial, ...]:
    """Start and connect the Practice Site; change, review and undo; reset it."""
    track = PRACTICE_TRACK_ID
    return (
        Tutorial(
            slug="workbench-practice-start",
            title="Start the Practice Site",
            track=track,
            minutes=6,
            surfaces=surfaces,
            summary=(
                "Start a WordPress site on this computer and connect the Workbench to it, "
                "so the next lessons have somewhere safe to work."
            ),
            steps=(
                Step(
                    title="Know where you will be working",
                    body=(
                        f"The {PRACTICE_NAME} is a whole WordPress that runs on this computer "
                        f"only, at {ADDRESS}. Nobody else can see it, and nothing you do there "
                        "reaches any of your real sites. Every lesson in this track works "
                        "there and nowhere else."
                    ),
                    note=(
                        "The Workbench labels it as practice wherever its name appears, and "
                        "asks you by name before anything from it could go to a real site."
                    ),
                ),
                Step(
                    title="Open the WordPress Workbench",
                    body=(
                        "The Workbench is the window for everything on your WordPress "
                        "sites. Open it from the editor's WordPress menu."
                    ),
                    command="wordpress.workbench",
                    hear="WordPress Workbench, and the tree of your sites.",
                ),
                _step(
                    "practice",
                    title="Open Practice Site",
                    body=(
                        "In the Workbench's Tools menu, choose Practice Site. It is one short "
                        "list of what you can do with the site right now."
                    ),
                    hear="Practice Site, and Start the Practice Site.",
                ),
                Step(
                    title="Start it",
                    body=(
                        "Choose Start the Practice Site and press Enter. The first start builds "
                        "a fresh WordPress with a welcome page, a first post and a draft, so "
                        "give it two or three minutes. Later starts take under a minute."
                    ),
                    keys=("Enter",),
                    hear=f"The Practice Site is running at {ADDRESS}. Connect it in a moment.",
                    note=(
                        "If something else on this computer is using its port, it says so "
                        "and does not start. Stop the other copy first."
                    ),
                ),
                _step(
                    "practice",
                    title="Connect it",
                    body=(
                        "Open Practice Site again and choose Connect It as Practice Site. "
                        "The site made a one-time password for QUILL when it started; the "
                        "Workbench keeps it in Windows Credential Manager, so you type "
                        "nothing."
                    ),
                    hear="Practice Site is connected. It is under Sites.",
                ),
            ),
            closing=(
                "The Practice Site is now one of your sites in the tree. It stays there, "
                "with everything you do to it, until you reset it."
            ),
            then=("workbench-practice-change",),
        ),
        Tutorial(
            slug="workbench-practice-change",
            title="Change a practice post, then undo it",
            track=track,
            minutes=6,
            surfaces=surfaces,
            summary=(
                "Open a post on the Practice Site, change its title, find the change in "
                "Change History, and put it back."
            ),
            steps=(
                Step(
                    title="Move to the Practice Site",
                    body=(
                        "In the tree, arrow to Sites and then to Practice Site. Doing this "
                        "first makes the Practice Site the current site, so every later step "
                        "works there."
                    ),
                    keys=("Up", "Down"),
                    hear="Practice Site, and the tree level it is on.",
                ),
                _step(
                    "go_posts",
                    title="Go to its posts",
                    body=(
                        "Go to Posts lists the current site's posts in the list beside the "
                        "tree. Because you moved to the Practice Site, these are its posts."
                    ),
                    hear="A First Practice Post, Hello world, and My Next Practice Story.",
                ),
                _step(
                    "sheet",
                    title="Open A First Practice Post's Properties",
                    body=(
                        "Arrow to A First Practice Post and open Properties. Everything about "
                        "the post is on one sheet, one field at a time."
                    ),
                    hear="A First Practice Post Properties, on its title.",
                ),
                Step(
                    title="Change the title",
                    body=(
                        "Add the word Practised to the end of the title and choose OK. The "
                        "Workbench shows you what it is about to send, and sends it only "
                        "when you say yes."
                    ),
                    keys=("End", "Enter"),
                    hear="What will change, then the list again with the new title.",
                ),
                _step(
                    "history",
                    title="Read Change History",
                    body=(
                        "Change History lists every change made in the Workbench this "
                        "session, newest first, and says which ones can be undone."
                    ),
                    hear="Change History, with your title change first.",
                ),
                _step(
                    "undo",
                    title="Undo it",
                    body=(
                        "Close Change History and, from the list, undo the last WordPress "
                        "change. The Workbench puts the old title back on the site."
                    ),
                    hear="The undo said in words, and the list with the old title.",
                    note="Undo works in the list, not in the filter box, where it edits the text.",
                ),
            ),
            closing=(
                "That is the whole loop the Workbench uses everywhere: look, change with a "
                "preview, find it in Change History, and undo it if you need to."
            ),
            then=("workbench-practice-reset",),
        ),
        Tutorial(
            slug="workbench-practice-reset",
            title="Reset the Practice Site",
            track=track,
            minutes=4,
            surfaces=surfaces,
            summary=(
                "Stop the Practice Site and put it back as new, knowing exactly what a reset "
                "removes and what it leaves alone."
            ),
            steps=(
                _step(
                    "practice",
                    title="Stop it",
                    body=(
                        "Open Practice Site and choose Stop the Practice Site. Stopping keeps "
                        "everything on it for next time; it only ends the server."
                    ),
                    hear="The practice site has stopped.",
                ),
                _step(
                    "practice",
                    title="Choose Reset",
                    body=(
                        "Open Practice Site again and choose Reset the Practice Site. Read "
                        "the question to the end before answering: it lists what is removed."
                    ),
                    hear=(
                        "Reset the Practice Site, and that it permanently deletes everything "
                        "on it and cannot be undone."
                    ),
                    note=(
                        "Reset removes the posts, pages, uploads and settings on the Practice "
                        "Site, its connection, and its stored password. Your real sites are "
                        "not touched."
                    ),
                ),
                Step(
                    title="Answer Reset",
                    body=(
                        "Choose Reset. The default answer is Cancel, so pressing Enter by "
                        "habit does nothing."
                    ),
                    hear="The practice site is new again. Start it to use it.",
                ),
            ),
            closing=(
                "Start it again whenever you want a clean site to practise on; the first "
                "lesson in this track walks you through it."
            ),
        ),
    )


def practice_only_problems(tutorials: tuple[Tutorial, ...]) -> list[str]:
    """Why these lessons could touch something other than the Practice Site ("" if none)."""
    problems: list[str] = []
    for tutorial in tutorials:
        for number, step in enumerate(tutorial.steps, start=1):
            where = f"{tutorial.slug} step {number}"
            if step.command in FORBIDDEN_COMMANDS:
                problems.append(f"{where}: {step.command} sends work to another site.")
            text = " ".join((step.body, step.hear, step.note))
            if "https://" in text or ("http://" in text and ADDRESS not in text):
                problems.append(f"{where}: names a site address other than the Practice Site.")
    return problems
