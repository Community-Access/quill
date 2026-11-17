"""Three Practice Site lessons beyond one site's posts (WP-R-049, PRD D4).

Custom types and fields, copying from staging to live, and Site Sets. The
Practice Site stands in for staging -- the copy you try things on -- and the
lessons stop short of sending anything to a real site: they compare, take a
snapshot, and say how Copy to Site asks before it sends, without naming that
command as a step, which
:func:`~quill.core.tutorials.wordpress_practice_lessons.practice_only_problems`
would refuse.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial
from quill.core.tutorials.wordpress_practice_lessons import PRACTICE_TRACK_ID, workbench_step
from quill.core.tutorials.wordpress_practice_more import (
    CHANGED,
    MATERIAL_NOTE,
    move_to_practice,
    open_workbench,
)
from quill.core.wordpress.workbench_practice import PRACTICE_NAME

__all__ = ["site_practice_lessons"]


def site_practice_lessons(
    *, surfaces: tuple[str, ...] = ("WordPress Workbench",)
) -> tuple[Tutorial, ...]:
    """Custom types and fields; staging to live; across sites with a Site Set."""
    track = PRACTICE_TRACK_ID
    return (
        Tutorial(
            slug="workbench-practice-custom-types",
            title="Custom types and their fields",
            track=track,
            minutes=7,
            surfaces=surfaces,
            summary=(
                "Hear what kinds of content the Practice Site has beyond posts and pages, open "
                "an event, and change its Event date field."
            ),
            steps=(
                open_workbench(),
                move_to_practice(),
                Step(
                    title="Open the Content Model",
                    body=(
                        "Under the Practice Site, arrow to Content Model. Each row is one kind "
                        "of content or one field, who registered it, and whether QUILL can "
                        "reach it."
                    ),
                    keys=("Down",),
                    hear="Practice Events, post type, and the plugin that registered it.",
                    note=MATERIAL_NOTE,
                ),
                Step(
                    title="Open Practice Events",
                    body=(
                        "Arrow up to More Content Types and then into Practice Events. A "
                        "custom type gets a list of its own, like Posts and Pages."
                    ),
                    keys=("Up", "Right"),
                    hear="Winter Concert, published.",
                ),
                workbench_step(
                    "sheet",
                    title="Open the event's Properties",
                    body=(
                        "Properties on Winter Concert has its title and status like any post, "
                        "and its own fields on a page of their own, among them Event date."
                    ),
                    hear="Winter Concert Properties, on its title.",
                ),
                Step(
                    title="Change Event date",
                    body=(
                        "Move to the fields page, find Event date, and change it to "
                        "2026-12-06 19:00. Choose OK; the Workbench shows what it will send "
                        "and sends it when you say yes."
                    ),
                    keys=("Ctrl+Tab", "Enter"),
                    hear="What will change: Event date, then the list again.",
                    check=CHANGED,
                ),
                workbench_step(
                    "history",
                    title="Find it in Change History",
                    body=(
                        "Change History has the field change like any other, and Undo puts "
                        "the old date back. A field is no harder to undo than a title."
                    ),
                    hear="Change History, with the Event date change first.",
                ),
            ),
            closing=(
                "Every content type a plugin adds, and every field it exposes, works the same "
                "way as a post: a list, Properties, a preview, and undo."
            ),
            then=("workbench-practice-staging",),
        ),
        Tutorial(
            slug="workbench-practice-staging",
            title="From staging to live, without surprises",
            track=track,
            minutes=8,
            surfaces=surfaces,
            summary=(
                f"Treat the {PRACTICE_NAME} as your staging copy: change a page there, compare "
                "it with your real site, and take a snapshot before anything is copied."
            ),
            steps=(
                Step(
                    title="Know what staging is",
                    body=(
                        "Staging is a copy of a site where changes are tried first; live is "
                        f"the site visitors see. Here the {PRACTICE_NAME} is staging, and one "
                        "of your connected sites is live."
                    ),
                    hear="Nothing yet: this step is the idea.",
                    note=(
                        "If you have only the Practice Site connected, you can follow every "
                        "step but Compare Sites, which needs a second site."
                    ),
                ),
                open_workbench(),
                move_to_practice(),
                workbench_step(
                    "go_pages",
                    title="Change a page on staging",
                    body=(
                        "Go to Pages, open Properties on Welcome to Your Practice Site, and "
                        "add the word Updated to its title. This is the change you will "
                        "compare."
                    ),
                    keys=("Alt+Enter",),
                    hear="Welcome to Your Practice Site Properties, then the list again.",
                    check=CHANGED,
                ),
                workbench_step(
                    "compare_sites",
                    title="Compare staging with live",
                    body=(
                        "Compare Sites asks for the other site and then lists what differs: "
                        "pages, posts, plugins, themes and settings, each with what it is on "
                        "each side. Nothing is changed by comparing."
                    ),
                    hear="What differs between Practice Site and your other site.",
                ),
                workbench_step(
                    "snapshot",
                    title="Take a snapshot of live first",
                    body=(
                        "Move to your live site under Sites and Take a Snapshot. It reads the "
                        "site and saves it on this computer, so if a copy goes wrong Put Back "
                        "from a Snapshot can undo it."
                    ),
                    keys=("Up", "Down"),
                    hear="Snapshot taken, and where it is kept.",
                ),
                Step(
                    title="Know how the copy asks",
                    body=(
                        "Copy to Site, on an item's context menu, is how a change goes from "
                        "staging to live. From the Practice Site it always asks first, naming "
                        "both sites, with No as the answer Enter gives."
                    ),
                    hear="Nothing yet: this lesson stops here, with live untouched.",
                    note=(
                        "When you do copy for real, read the preview to the end: it lists "
                        "every item that will change on the live site."
                    ),
                ),
            ),
            closing=(
                "Change on staging, compare, snapshot, then copy with your eyes open: live "
                "only changes when you have said its name."
            ),
            then=("workbench-practice-site-sets",),
        ),
        Tutorial(
            slug="workbench-practice-site-sets",
            title="Across sites with a Site Set",
            track=track,
            minutes=6,
            surfaces=surfaces,
            summary=(
                "Name a set of your sites, point Across Sites at it, read the same list on every "
                "site in the set at once, and remove the set again."
            ),
            steps=(
                open_workbench(),
                workbench_step(
                    "site_sets",
                    title="Make a Site Set",
                    body=(
                        "Site Sets asks for a name, then for the sites in it. Call it "
                        f"Practising and check {PRACTICE_NAME}. A set is kept on this computer "
                        "and changes nothing on any site."
                    ),
                    hear="Practising: 1 sites.",
                ),
                workbench_step(
                    "scope",
                    title="Point Across Sites at the set",
                    body=(
                        "Across Sites Scope chooses whether Across Sites covers every site or "
                        "one set. Choose Practising, so what you read next is only the sites "
                        "in it."
                    ),
                    hear="Across Sites covers Practising.",
                ),
                workbench_step(
                    "go_across",
                    title="Read across the set",
                    body=(
                        "Go to Across Sites lists the same name on every site in scope: a "
                        "plugin, a person, a category. Arrow into Plugins to hear each plugin "
                        "and the sites it is on."
                    ),
                    keys=("Right",),
                    hear="Across Sites, and the kinds it can compare.",
                ),
                workbench_step(
                    "scope",
                    title="Go back to every site",
                    body=(
                        "Across Sites Scope again, and choose Every site. A set you are not "
                        "using costs nothing, and Every site is what Needs My Attention always "
                        "uses."
                    ),
                    hear="Across Sites covers every site.",
                ),
                workbench_step(
                    "site_sets",
                    title="Remove the set",
                    body=(
                        "Site Sets with the same name, Practising, and every site unchecked "
                        "removes the set. Nothing on any site changes."
                    ),
                    hear="Removed Practising.",
                ),
            ),
            closing=(
                "A Site Set is a name for some of your sites. Make one for the sites you look "
                "after together, such as a client's three."
            ),
        ),
    )
