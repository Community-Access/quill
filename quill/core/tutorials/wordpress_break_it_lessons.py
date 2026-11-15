"""Break It on Purpose: Practice Site lessons that start broken (WP-R-049, PRD D4).

Each lesson begins with something already wrong on the Practice Site -- a
picture with no alternative text, a link to a page that is not there, two
plugins fighting over one shortcode, a misspelt address -- and teaches the
Workbench's way of finding it and fixing it. The broken state is put there by
Tools > Practice Site, Set Up the Lesson Material
(:mod:`quill.core.wordpress.workbench_practice_material`), which writes only
into the Practice Site's own folder on this computer, shows what it will add
first, and goes into Change History with Take Away as its undo.

The step that fixes each problem carries a check: the lesson window watches
the Workbench for a change made on the Practice Site
(:data:`~quill.core.tutorials.wordpress_practice_more.CHANGED`), so it
notices the fix rather than the key. The step after it reads the list again,
so you hear for yourself that the problem has gone.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Track, Tutorial
from quill.core.tutorials.wordpress_practice_lessons import workbench_step
from quill.core.tutorials.wordpress_practice_more import CHANGED, move_to_practice, open_workbench
from quill.core.wordpress.workbench_practice import PRACTICE_NAME

__all__ = ["BREAK_TRACK", "BREAK_TRACK_ID", "MATERIAL_READY", "break_it_lessons"]

BREAK_TRACK_ID = "wordpress-break-it"
BREAK_TRACK = Track(
    BREAK_TRACK_ID,
    "Break It on Purpose, on the Practice Site",
    "Four problems put on the Practice Site on purpose -- a missing alt text, a broken "
    "link, a plugin conflict and a wrong address -- and how the Workbench finds and fixes "
    "each one.",
)

#: The check that the lesson material is on the Practice Site.
MATERIAL_READY = "lesson-material-ready"


def break_it_lessons(
    *, surfaces: tuple[str, ...] = ("WordPress Workbench",)
) -> tuple[Tutorial, ...]:
    """Set the problems up, then find and fix each of the four."""
    track = BREAK_TRACK_ID
    return (
        Tutorial(
            slug="break-it-set-up",
            title="Set up the broken Practice Site",
            track=track,
            minutes=4,
            surfaces=surfaces,
            summary=(
                f"Put four problems on the {PRACTICE_NAME} on purpose, after hearing exactly "
                "what will be added, and learn how to take them away again."
            ),
            steps=(
                Step(
                    title="Know what is about to happen",
                    body=(
                        f"These lessons need something wrong to find. The {PRACTICE_NAME} "
                        "lesson material adds it to the WordPress on this computer only, never "
                        "to a real site, and lists every piece before it adds any."
                    ),
                    hear="Nothing yet: this step is what comes next.",
                    note="Start the Practice Site first; the Practice Site track shows how.",
                ),
                open_workbench(),
                workbench_step(
                    "practice",
                    title="Open Practice Site",
                    body=(
                        "In the Workbench's Tools menu, choose Practice Site. Once the site "
                        "has been started at least once, the list ends with Set Up the Lesson "
                        "Material."
                    ),
                    hear="Practice Site, and what you can do with it now.",
                ),
                Step(
                    title="Choose Set Up the Lesson Material",
                    body=(
                        "Arrow to Set Up the Lesson Material and press Enter. Read the "
                        "question to the end: it names the picture, the posts, the page, the "
                        "plugins, the comments and the event it adds."
                    ),
                    keys=("Down", "Enter"),
                    hear="Set up the lesson material on the Practice Site, and the list.",
                ),
                Step(
                    title="Answer Set Up",
                    body=(
                        "Choose Set Up. The default answer is Cancel, so Enter by habit does "
                        "nothing. If the site is running the material is there at once; if "
                        "not, it arrives when you next start it."
                    ),
                    hear="The lesson material is on the Practice Site, and what it holds.",
                    check=MATERIAL_READY,
                    note=(
                        "Practice Site, Take Away the Lesson Material, removes exactly what "
                        "was added, and Ctrl+Z in the list does the same. Reset removes "
                        "everything."
                    ),
                ),
            ),
            closing="Now there is something to fix. Start with the picture.",
            then=("break-it-alt-text",),
        ),
        Tutorial(
            slug="break-it-alt-text",
            title="Fix a picture with no alt text",
            track=track,
            minutes=5,
            surfaces=surfaces,
            summary=(
                "Find the picture nobody described, using Needs My Attention, and give it "
                "alternative text a screen reader can say."
            ),
            steps=(
                open_workbench(),
                workbench_step(
                    "go_inbox",
                    title="Open Accessibility",
                    body=(
                        "Go to Needs My Attention, then arrow to Accessibility. It lists every "
                        "picture without alternative text, on every site. A screen reader says "
                        "only image for each of them."
                    ),
                    keys=("Down",),
                    hear="Accessibility, and Bake sale table, Practice Site.",
                ),
                workbench_step(
                    "sheet",
                    title="Open the picture's Properties",
                    body=(
                        "On Bake sale table, open Properties. Its second page is Alt Text and "
                        "Caption; Ctrl+Tab moves there."
                    ),
                    keys=("Ctrl+Tab",),
                    hear="Bake sale table Properties, then Alt Text and Caption.",
                ),
                Step(
                    title="Write the alt text",
                    body=(
                        "In Alt text, say what the picture shows to somebody who cannot see "
                        "it: a folding table of cakes under a striped awning. Choose OK, and "
                        "yes to the preview."
                    ),
                    keys=("Enter",),
                    hear="What will change: Alt text, then the list again.",
                    check=CHANGED,
                ),
                workbench_step(
                    "refresh",
                    title="Hear that it has gone",
                    body=(
                        "Refresh reads Accessibility from the site again. Bake sale table is "
                        "no longer in it, because it now has alternative text."
                    ),
                    hear="Accessibility, without Bake sale table.",
                    note=(
                        "In the editor, Tools > WordPress > Alt Text Review does the same for "
                        "the pictures in the page you are writing."
                    ),
                ),
            ),
            closing="One picture, one sentence, and somebody who cannot see it now knows it.",
            then=("break-it-broken-link",),
        ),
        Tutorial(
            slug="break-it-broken-link",
            title="Fix a broken link",
            track=track,
            minutes=7,
            surfaces=surfaces,
            summary=(
                "Find a link that goes nowhere, open the post it is in, point it at a page that "
                "exists, and send the post back."
            ),
            steps=(
                open_workbench(),
                workbench_step(
                    "go_inbox",
                    title="Open Broken Links",
                    body=(
                        "Go to Needs My Attention, then arrow to Broken Links. The Workbench "
                        "follows the links in the newest published posts and pages and lists "
                        "the ones the site could not reach."
                    ),
                    keys=("Down",),
                    hear="Broken link, Where to Find Us, and the address it could not reach.",
                    note=(
                        "If it says the site does not offer link checking, Check This Page in "
                        "the editor finds the same link in the next steps."
                    ),
                ),
                move_to_practice(),
                workbench_step(
                    "go_posts",
                    title="Open the post in the editor",
                    body=(
                        "Go to Posts, arrow to Where to Find Us and press Enter. Writing "
                        "happens in the editor, so that is where the post opens."
                    ),
                    keys=("Enter",),
                    hear="Where to Find Us, in the editor.",
                ),
                Step(
                    title="Hear where the link goes",
                    body=(
                        "Move to the words our address page and use Hear Where a Link Goes. "
                        "It says the address and whether the page is there."
                    ),
                    command="wordpress.hear_link",
                    hear="Our address page goes to our-old-address, which is not there.",
                ),
                Step(
                    title="Point it at a real page",
                    body=(
                        "Select the words our address page, then use Link to a Page on This "
                        "Site and choose Contact Us. The words stay; only where they lead "
                        "changes."
                    ),
                    command="wordpress.insert_link",
                    hear="The pages on this site, then the document again.",
                    check="text-changed",
                ),
                Step(
                    title="Send the post back",
                    body=(
                        "Publish or Update sends the corrected post to the Practice Site. It "
                        "is already published, so this is an update, and it says so."
                    ),
                    command="wordpress.publish",
                    hear="Updated Where to Find Us on Practice Site.",
                ),
                Step(
                    title="Check the page",
                    body=(
                        "Check This Page follows every link in the post and says which go "
                        "nowhere. None should now; Broken Links agrees after F5."
                    ),
                    command="wordpress.check_page",
                    hear="All the links reach their pages.",
                ),
            ),
            closing="A dead link costs a visitor a trip; finding it costs you one list.",
            then=("break-it-plugin-conflict",),
        ),
        Tutorial(
            slug="break-it-plugin-conflict",
            title="Fix a plugin conflict",
            track=track,
            minutes=6,
            surfaces=surfaces,
            summary=(
                "Hear Site Health name a conflict between two plugins, switch one of them off, "
                "and hear the problem go."
            ),
            steps=(
                open_workbench(),
                move_to_practice(),
                workbench_step(
                    "go_health",
                    title="Read Site Health",
                    body=(
                        "Go to Site Health lists WordPress's own checks for the current site, "
                        "worst first. The first one is new: two plugins both answer the "
                        "countdown shortcode."
                    ),
                    hear="Two plugins both answer the countdown shortcode, critical.",
                ),
                workbench_step(
                    "next_pane",
                    title="Read what it means",
                    body=(
                        "Next Pane moves to the details: which two plugins, what a visitor "
                        "sees on a page that uses the shortcode, and the fix, which is to "
                        "switch one off."
                    ),
                    hear="Practice Countdown and Practice Countdown Plus are both on.",
                ),
                workbench_step(
                    "go_plugins",
                    title="Go to Plugins",
                    body=(
                        "Go to Plugins lists the plugins on the current site, each with "
                        "whether it is on. Arrow to Practice Countdown Plus, the newer of the "
                        "two."
                    ),
                    hear="Practice Countdown Plus, active.",
                ),
                Step(
                    title="Switch it off",
                    body=(
                        "Press Shift+F10 and choose Activate or Deactivate. The Workbench asks "
                        "first and says what depends on the plugin; answer Deactivate."
                    ),
                    keys=("Shift+F10",),
                    hear="Practice Countdown Plus, inactive.",
                    check=CHANGED,
                ),
                workbench_step(
                    "go_health",
                    title="Hear the problem go",
                    body=(
                        "Go to Site Health again and press F5. The conflict is no longer "
                        "listed, because only one plugin answers the shortcode now."
                    ),
                    keys=("F5",),
                    hear="Site Health, without the countdown problem.",
                ),
            ),
            closing=(
                "When something breaks after a plugin goes on, switching the newest one off "
                "is the first thing to try, and it is undone as easily."
            ),
            then=("break-it-permalink",),
        ),
        Tutorial(
            slug="break-it-permalink",
            title="Fix a wrong address",
            track=track,
            minutes=6,
            surfaces=surfaces,
            summary=(
                "Hear a page's misspelt address, correct its slug in Properties, and take the "
                "lesson material away when you are done."
            ),
            steps=(
                open_workbench(),
                move_to_practice(),
                workbench_step(
                    "go_pages",
                    title="Go to Pages",
                    body=(
                        "Go to Pages lists the current site's pages. Arrow to Contact Us; the "
                        "details pane says its address, which ends contcat-us."
                    ),
                    hear="Contact Us, published.",
                ),
                workbench_step(
                    "sheet",
                    title="Open its Properties",
                    body=(
                        "Properties on Contact Us opens on General, where Slug is the last "
                        "part of the address: the words after the site's name."
                    ),
                    hear="Contact Us Properties, on its title.",
                ),
                Step(
                    title="Correct the slug",
                    body=(
                        "Tab to Slug, replace contcat-us with contact-us, and choose OK. The "
                        "preview shows the old and new address before anything is sent."
                    ),
                    keys=("Tab", "Enter"),
                    hear="What will change: Slug, then the list again.",
                    check=CHANGED,
                ),
                workbench_step(
                    "copy_link",
                    title="Copy the new address",
                    body=(
                        "Copy Link puts the page's address on the clipboard, so you can paste "
                        "it anywhere and hear that it now ends contact-us."
                    ),
                    hear="Copied the address of Contact Us.",
                ),
                workbench_step(
                    "practice",
                    title="Take the lesson material away",
                    body=(
                        "Practice Site, then Take Away the Lesson Material, removes every "
                        "piece the material added, fixed or not, and the two practice plugins."
                        " Anything else you made stays."
                    ),
                    hear="Take away the lesson material, and what it removes.",
                ),
            ),
            closing=(
                "Those are the four problems people most often meet on a site, and you have "
                "found and fixed each one without leaving the keyboard."
            ),
        ),
    )
