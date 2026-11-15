"""Four more Practice Site lessons: menus, people, plugin updates, spam (WP-R-049, PRD D4).

The first three Practice Site lessons teach the loop -- look, change with a
preview, find it in Change History, undo -- and this module applies it to the
jobs a site owner meets in the first month: a menu, a new person and their
role, a plugin update done safely, and comments that are spam and comments
that are not. Like the first three they run on the Practice Site only, so
:func:`~quill.core.tutorials.wordpress_practice_lessons.practice_only_problems`
holds for them too.

A step names a command only where the Workbench's menu bar has one, with the
key from :data:`~quill.core.wordpress.workbench_window_menu.WORDPRESS_KEYS`;
the context-menu commands have no chord by design, so those steps say where
the command is and teach Shift+F10.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial
from quill.core.tutorials.wordpress_practice_lessons import PRACTICE_TRACK_ID, workbench_step
from quill.core.wordpress.workbench_practice import PRACTICE_NAME

__all__ = [
    "CHANGED",
    "MATERIAL_NOTE",
    "more_practice_lessons",
    "move_to_practice",
    "open_workbench",
]

#: The check that a change reached the Practice Site through the Workbench.
CHANGED = "practice-site-changed"

#: Said wherever a lesson needs what Set Up the Lesson Material adds.
MATERIAL_NOTE = (
    "This lesson uses the lesson material: Tools > Practice Site, Set Up the Lesson "
    "Material. The first Break It on Purpose lesson walks you through it."
)


def open_workbench() -> Step:
    """The editor's own row that opens the Workbench."""
    return Step(
        title="Open the WordPress Workbench",
        body=(
            "Open the Workbench from the editor's Tools menu, under WordPress. It is one "
            "window for everything on your sites, and every step here happens in it."
        ),
        command="wordpress.workbench",
        hear="WordPress Workbench, and the tree of your sites.",
    )


def move_to_practice() -> Step:
    """Make the Practice Site the current site, so later steps work there."""
    return Step(
        title="Move to the Practice Site",
        body=(
            f"In the tree, arrow to Sites and then to {PRACTICE_NAME}. That makes it the "
            "current site, so every Go key in this lesson lands on its lists and no other."
        ),
        keys=("Up", "Down"),
        hear=f"{PRACTICE_NAME}, and the tree level it is on.",
    )


def more_practice_lessons(
    *, surfaces: tuple[str, ...] = ("WordPress Workbench",)
) -> tuple[Tutorial, ...]:
    """Menus; a new person and a role; updating plugins safely; spam and challenges."""
    track = PRACTICE_TRACK_ID
    return (
        Tutorial(
            slug="workbench-practice-menus",
            title="Change a menu, then put it back",
            track=track,
            minutes=7,
            surfaces=surfaces,
            summary=(
                "Find the Practice Site's menu, add the welcome page to it, put its items in "
                "order, and bring the menu back as it was."
            ),
            steps=(
                open_workbench(),
                move_to_practice(),
                workbench_step(
                    "go_appearance",
                    title="Go to Appearance",
                    body=(
                        "Go to Appearance opens the part of the tree for how the site looks: "
                        "themes, templates, patterns, widgets, and menus."
                    ),
                    hear="Appearance, and the themes the site has.",
                ),
                Step(
                    title="Open Menus and Navigation",
                    body=(
                        "Arrow down the tree to Menus and Navigation. Each row is one menu, "
                        "and the details say where on the site it shows."
                    ),
                    keys=("Down",),
                    hear="Practice Menu, and how many items it has.",
                    note=MATERIAL_NOTE,
                ),
                Step(
                    title="Add a menu item",
                    body=(
                        "On Practice Menu, press Shift+F10 and choose Add Menu Item. Pick the "
                        "page called Welcome to Your Practice Site. The Workbench shows what it "
                        "is about to add and adds it only when you say yes."
                    ),
                    keys=("Shift+F10",),
                    hear="What will change, then the menu with one more item.",
                    check=CHANGED,
                ),
                Step(
                    title="Put the items in order",
                    body=(
                        "Shift+F10 again has Arrange Items, a list of the menu's items with "
                        "Move Up and Move Down. Move the welcome page to the top, the place a "
                        "visitor meets first."
                    ),
                    keys=("Shift+F10",),
                    hear="Arrange Items, then each item with its place in the menu.",
                    check=CHANGED,
                ),
                Step(
                    title="Bring the menu back as it was",
                    body=(
                        "Earlier Versions, on the same context menu, lists the menu as QUILL "
                        "first read it and since. Choose the oldest to put it back, after a "
                        "preview. Ctrl+Z in the list does the same for the last change."
                    ),
                    keys=("Shift+F10",),
                    hear="Earlier Versions of Practice Menu, newest first.",
                ),
            ),
            closing=(
                "A menu is one of the few things a visitor sees on every page, so it is worth "
                "knowing it can always be put back."
            ),
            then=("workbench-practice-people",),
        ),
        Tutorial(
            slug="workbench-practice-people",
            title="Add a person and choose their role",
            track=track,
            minutes=7,
            surfaces=surfaces,
            summary=(
                "Hear what each role may do, add a person to the Practice Site as an Author, "
                "change their role, and see the site as they would."
            ),
            steps=(
                open_workbench(),
                move_to_practice(),
                workbench_step(
                    "go_users",
                    title="Go to Users",
                    body=(
                        "Go to Users lists the people on the current site, each with their "
                        "username and role. On a fresh Practice Site that is only admin."
                    ),
                    hear="admin, Administrator.",
                ),
                workbench_step(
                    "roles",
                    title="Hear what the roles may do",
                    body=(
                        "Roles and What They May Do says each role in plain words before you "
                        "give one to anybody: a Contributor writes but cannot publish, an "
                        "Author publishes their own, an Editor publishes anyone's."
                    ),
                    hear="Subscriber, then what a subscriber may do.",
                ),
                workbench_step(
                    "new_here",
                    title="Add a person",
                    body=(
                        "In Users, New Here opens Add a Person. Give a username such as "
                        "practice-helper and an email address, and set Role to Author. The "
                        "role starts at Subscriber, the one that can do least."
                    ),
                    hear="Add a Person, Practice Site, on Username.",
                    check=CHANGED,
                    note="Nobody is emailed: the Practice Site cannot send mail.",
                ),
                Step(
                    title="Change their role",
                    body=(
                        "Arrow to practice-helper, press Shift+F10 and choose Change Role. "
                        "Choose Editor. The Workbench refuses any change that would lock you "
                        "out of your own site, and says why."
                    ),
                    keys=("Shift+F10",),
                    hear="Change Role, then practice-helper, Editor.",
                    check=CHANGED,
                ),
                workbench_step(
                    "view_as",
                    title="See the site as they would",
                    body=(
                        "View As Role shows the Workbench as an Editor would see it: the lists "
                        "and commands an Editor has, and nothing else. Choose your own role "
                        "again to come back."
                    ),
                    hear="Viewing as Editor, and the lists an Editor has.",
                ),
            ),
            closing=(
                "Give the smallest role that lets somebody do their job. You can always raise "
                "it later, and the Workbench says plainly what each one allows."
            ),
            then=("workbench-practice-updates",),
        ),
        Tutorial(
            slug="workbench-practice-updates",
            title="Update plugins safely",
            track=track,
            minutes=8,
            surfaces=surfaces,
            summary=(
                "Take a snapshot first, find what is waiting to update, read what changed, run "
                "the update, and check the site's health afterwards."
            ),
            steps=(
                open_workbench(),
                move_to_practice(),
                workbench_step(
                    "snapshot",
                    title="Take a snapshot first",
                    body=(
                        "Take a Snapshot saves the site's posts, pages, patterns and terms on "
                        "this computer before you change anything, so there is something to "
                        "go back to."
                    ),
                    hear="Snapshot taken, and where it is kept.",
                ),
                workbench_step(
                    "go_inbox",
                    title="Find what is waiting",
                    body=(
                        "Go to Needs My Attention, then arrow to Updates. It lists WordPress, "
                        "plugins, themes and translations with an update waiting, on every "
                        "site you have, with the installed and the new version."
                    ),
                    keys=("Down",),
                    hear="Updates, and each one with its site and its two versions.",
                    note=(
                        "A fresh Practice Site may have none waiting. The steps are the same "
                        "on your own site."
                    ),
                ),
                Step(
                    title="Read what changed",
                    body=(
                        "On an update, Shift+F10 has Check for Updates on WordPress.org, which "
                        "reads the plugin's own page: listen for security fixes, breaking "
                        "changes and database updates before you go on."
                    ),
                    keys=("Shift+F10",),
                    hear="The plugin, its newest version, and what that version changed.",
                ),
                Step(
                    title="Run the update in wp-admin",
                    body=(
                        "Press Enter on the update. WordPress does not let any app run updates "
                        "from outside, so this opens Dashboard, Updates in your browser, where "
                        "you choose it and update."
                    ),
                    keys=("Enter",),
                    hear="Your browser, on WordPress Updates.",
                ),
                workbench_step(
                    "go_health",
                    title="Check the site's health afterwards",
                    body=(
                        "Back in the Workbench, Go to Site Health and press F5. A problem that "
                        "was not there before the update is the first thing to look at."
                    ),
                    keys=("F5",),
                    hear="Site Health, worst first, and Up to date.",
                    note=(
                        "If an update broke something, Go to Plugins has Activate or "
                        "Deactivate on each plugin's context menu."
                    ),
                ),
            ),
            closing=(
                "Snapshot, read, update, check: four steps, every time, and an update is "
                "rarely a surprise."
            ),
            then=("workbench-practice-spam",),
        ),
        Tutorial(
            slug="workbench-practice-spam",
            title="Spam, real comments, and challenges",
            track=track,
            minutes=7,
            surfaces=surfaces,
            summary=(
                "Tell a held spam comment from a real question, approve and answer the real "
                "one, and hear where the challenges for forms are kept."
            ),
            steps=(
                open_workbench(),
                move_to_practice(),
                workbench_step(
                    "go_inbox",
                    title="Open Held as Spam",
                    body=(
                        "Go to Needs My Attention, then arrow to Held as Spam. It gathers the "
                        "comments and form entries every site doubted, with who sent them."
                    ),
                    keys=("Down",),
                    hear="Held as Spam, and Cheap Watches Today, Practice Site.",
                    note=MATERIAL_NOTE,
                ),
                workbench_step(
                    "next_pane",
                    title="Read why it was held",
                    body=(
                        "Next Pane moves to the details, which say what the comment says and "
                        "why the site held it. This one is spam: leave it where it is."
                    ),
                    hear="Cheap Watches Today, and the comment in full.",
                    note=(
                        "Ctrl+Shift+A on a held comment means Not Spam, and lets it through. "
                        "Not Spam, and Allow This Sender, lets that person's next ones through "
                        "too."
                    ),
                ),
                workbench_step(
                    "go_comments",
                    title="Find the real question",
                    body=(
                        "Go to Comments lists the current site's comments, waiting ones first. "
                        "Sam Rivera is asking when the bake sale is, a real question from a "
                        "real visitor."
                    ),
                    hear="Sam Rivera, waiting, on A First Practice Post.",
                ),
                workbench_step(
                    "approve",
                    title="Approve it",
                    body=(
                        "Approve puts the comment on the site where everybody can read it. "
                        "Unapprove sends it back to waiting if you change your mind."
                    ),
                    hear="Approved, Sam Rivera.",
                    check=CHANGED,
                ),
                workbench_step(
                    "reply",
                    title="Answer it",
                    body=(
                        "Reply opens a box for your answer, written as you, under Sam's "
                        "comment. Say Saturday, and send it."
                    ),
                    hear="Reply to Sam Rivera, on the box for your answer.",
                    check=CHANGED,
                ),
                Step(
                    title="Hear where the challenges are",
                    body=(
                        "On a site in the Sites list, Shift+F10 has Form Spam Questions: the "
                        "short questions visitors answer before a form is sent, and how many "
                        "entries each week were held."
                    ),
                    keys=("Shift+F10",),
                    hear="Form Spam Questions, or that this site has no forms plugin.",
                    note=(
                        "The Practice Site has no forms plugin, so it says so. On a site with "
                        "QUILL Accessible Forms the questions are listed."
                    ),
                ),
            ),
            closing=(
                "Spam waits for you in one place across every site, and a real comment gets "
                "an answer in two keys."
            ),
        ),
    )
