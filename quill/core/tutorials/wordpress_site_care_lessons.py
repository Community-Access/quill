"""A lesson on looking after a site, on the Practice Site (wordpress.md 9.17, gap 12).

The seven WordPress lessons teach writing; the three Practice Site lessons
teach changing, reviewing and undoing. This one walks the rest of what a site
owner does that the 9.16 and 9.17 work added: the Overview's At a Glance and
wp-admin Screens, menus and their earlier versions, people, Site Health,
fonts, every kind of widget, and the big-file and Word commands in the
editor. It runs on the Practice Site, in the practice track, so nothing it
teaches touches a real site.

A step names a command only where the command has an id the app resolves
(the editor's WordPress rows); the Workbench's context-menu commands have no
chord by design, so those steps say where the command is instead.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial
from quill.core.tutorials.wordpress_practice_lessons import PRACTICE_TRACK_ID
from quill.core.wordpress.workbench_practice import PRACTICE_NAME

__all__ = ["site_care_lessons"]


def site_care_lessons(
    *, surfaces: tuple[str, ...] = ("WordPress Workbench",)
) -> tuple[Tutorial, ...]:
    """Look after a site: glance, menus, people, health, fonts, widgets, files."""
    return (
        Tutorial(
            slug="workbench-practice-site-care",
            title="Look after a site",
            track=PRACTICE_TRACK_ID,
            minutes=10,
            surfaces=surfaces,
            summary=(
                "Read how the site is doing, bring back a lost menu item, check its people, "
                "its health, its fonts and its widgets, and move big files and Word documents "
                f"in and out, all on the {PRACTICE_NAME}."
            ),
            steps=(
                Step(
                    title="Open the WordPress Workbench",
                    body=(
                        f"Open the Workbench and move to the {PRACTICE_NAME} under Sites. "
                        "Everything in this lesson happens there."
                    ),
                    command="wordpress.workbench",
                    hear="WordPress Workbench, and the tree of your sites.",
                ),
                Step(
                    title="Read At a Glance",
                    body=(
                        "Open Overview with Right Arrow, then At a Glance. Each row is one "
                        "sentence: posts and pages by status, comments waiting, the people, "
                        "WordPress's version and the theme."
                    ),
                    keys=("Right",),
                    hear="Posts, then how many are published, drafts and scheduled.",
                    note=("A count your role may not see is left out rather than said as zero."),
                ),
                Step(
                    title="Find what is only in wp-admin",
                    body=(
                        "Open wp-admin Screens, under Overview. Each row is a wp-admin screen, "
                        "the place in the Workbench nearest to it, and how much of it the "
                        "Workbench does. Enter says why and opens it in your browser."
                    ),
                    keys=("Enter",),
                    hear="Settings > Permalinks, Only in wp-admin.",
                ),
                Step(
                    title="Bring back a menu item",
                    body=(
                        "Open Menus and Navigation and choose a menu. Its context menu, "
                        "Shift+F10, has Earlier Versions, which brings back items removed "
                        "since QUILL first read the menu, after a preview. Ctrl+Z takes them "
                        "out again."
                    ),
                    keys=("Shift+F10",),
                    hear="Earlier Versions of the menu, newest first.",
                ),
                Step(
                    title="Check the people and the site's health",
                    body=(
                        "Open People, then Users, to hear each person and their role; then "
                        "Site Health, where WordPress's own checks are listed worst first."
                    ),
                    hear="Each person's name, username and role.",
                ),
                Step(
                    title="Hear the fonts and the widgets",
                    body=(
                        "Under Appearance, Fonts lists the fonts the site has installed, and "
                        "Widgets and Sidebars lists each widget area. On an area, Shift+F10 "
                        "has Add a Widget, which offers every kind of widget the site has, "
                        "and Preview Widgets, the area as a visitor sees it."
                    ),
                    keys=("Shift+F10",),
                    hear="Each widget, then what a visitor sees of it.",
                    note="A block theme has no widget areas; its header and footer are templates.",
                ),
                Step(
                    title="Upload a big file",
                    body=(
                        "Back in the editor, Upload a Large File first says how much space the "
                        "site already uses beside the file's size, then asks for its title, "
                        "caption and description once it is there."
                    ),
                    command="wordpress.upload_large_file",
                    hear="Upload, the file's size, and what the site already uses.",
                ),
                Step(
                    title="Download your writing as Word",
                    body=(
                        "Download My Writing asks whether each page and post should be a "
                        "Markdown file or a Word document. Send a Folder as Drafts reads Word "
                        "documents too, so a folder can go back as drafts."
                    ),
                    command="wordpress.download_writing",
                    hear="Save each page and post as: Markdown files, or Word documents.",
                ),
            ),
            closing=(
                "You can now look after a site the way wp-admin does, and know where wp-admin "
                "is still the place. Reset the Practice Site whenever you want to start fresh."
            ),
        ),
    )
