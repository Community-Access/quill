"""Your first week with a site: one short lesson a day, the same in QUILL and QUILL Lite.

PRD D4 (WP-R-049) asks for a first-week path for a new site owner: one short
lesson a day, each finishing with something real on their own site. Unlike
the Practice Site lessons these may run on a real site, so every day is built
to one rule: **nothing happens that the person did not choose, and nothing is
destructive by default.** A day saves a draft rather than publishing, writes
one alt text the person picks, fixes one finding the person understands,
approves or answers a comment rather than deleting one, and publishes on the
last day only if the person is ready -- with Check Before Publishing first and
Schedule as the other answer.

Both editors reach WordPress through the one row table
(``quill/core/wordpress/menu.py``), so, like :mod:`wordpress_lessons`, the days
are written once and each editor passes a function from a row's short name to
its own command id. The WordPress Workbench's Start Here points here
(:data:`quill.core.wordpress.workbench_help.START_HERE`).
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.tutorials.model import Step, Track, Tutorial
from quill.core.tutorials.wordpress_lessons import layer_keys

__all__ = ["FIRST_WEEK_TRACK", "FIRST_WEEK_TRACK_ID", "first_week_lessons"]

FIRST_WEEK_TRACK_ID = "wordpress-first-week"
FIRST_WEEK_TRACK = Track(
    FIRST_WEEK_TRACK_ID,
    "Your first week with a site",
    "For a new site owner: one short lesson a day for seven days, on your own site, each "
    "ending with something real -- and nothing happens that you did not choose.",
)


def first_week_lessons(
    command: Callable[[str], str],
    *,
    surfaces: tuple[str, ...],
    app: str,
) -> tuple[Tutorial, ...]:
    """Seven days. *command* maps a WordPress row's short name to this editor's command id."""
    track = FIRST_WEEK_TRACK_ID

    def row(name: str, **fields: str) -> Step:
        return Step(command=command(name), keys=layer_keys(name), **fields)

    return (
        Tutorial(
            slug="first-week-1-connect",
            title="Day 1: Connect your site",
            track=track,
            minutes=5,
            surfaces=surfaces,
            summary=(
                f"Connect {app} to your own site and hear the role you have there. By the end "
                "your site is one of your sites."
            ),
            steps=(
                row(
                    "connect",
                    title="Open Connect a Site",
                    body=(
                        "Connect a Site asks for your site's address and gets an application "
                        "password through your browser, so you never type your own password "
                        f"into {app}."
                    ),
                    hear="The Connect a WordPress Site dialog, on Kind of site.",
                    note="The WordPress track's first lesson walks through this form in full.",
                ),
                Step(
                    title="Approve it in your browser",
                    body=(
                        "Press Get Password with My Browser, sign in on your site if it asks, "
                        "and choose Approve. You can take the password away again on your "
                        "site at any time."
                    ),
                    keys=("Enter",),
                    hear="Connected to your site as, and your role.",
                ),
                row(
                    "sites",
                    title="Hear it in your sites",
                    body=(
                        "Sites lists every site you have connected, with your role on each. "
                        "Your role decides what every later day can do."
                    ),
                    hear="Your site's name, its address and your role.",
                ),
            ),
            closing="Your site is connected. Tomorrow, write something on it that nobody sees yet.",
            then=("first-week-2-draft",),
        ),
        Tutorial(
            slug="first-week-2-draft",
            title="Day 2: Save a draft on your site",
            track=track,
            minutes=6,
            surfaces=surfaces,
            summary=(
                "Write a short post and save it to your site as a draft: it is on the site, and "
                "nobody but you can see it."
            ),
            steps=(
                row(
                    "new_post",
                    title="Start a new post",
                    body=(
                        "New Post asks for a title and opens an empty document for the post. "
                        "Call it something you would really publish, such as News for this "
                        "month."
                    ),
                    hear="New post, and the title box.",
                ),
                Step(
                    title="Write a paragraph",
                    body=(
                        "Write two or three sentences, the way you would in any document. "
                        "Headings and lists come across to WordPress as blocks by themselves."
                    ),
                    hear="Your words, as you type them.",
                ),
                row(
                    "save_draft",
                    title="Save it to your site as a draft",
                    body=(
                        "Save Draft to Site sends the post as a draft. A draft is saved on the "
                        "site and is not public until you publish it, which is a separate "
                        "choice."
                    ),
                    hear="Saved the draft to your site.",
                ),
            ),
            closing="There is a draft on your site. On day 7 you can choose to publish it.",
            then=("first-week-3-alt-text",),
        ),
        Tutorial(
            slug="first-week-3-alt-text",
            title="Day 3: Describe one picture",
            track=track,
            minutes=6,
            surfaces=surfaces,
            summary=(
                "Hear which pictures on your site have no alternative text, and describe one "
                "you know, so a screen reader can say what it shows."
            ),
            steps=(
                row(
                    "alt_text_review",
                    title="Open Alt Text Review",
                    body=(
                        "Alt Text Review lists pictures and what each one's alternative text "
                        "says, starting with the ones that have none. Nothing changes until "
                        "you write something."
                    ),
                    hear="Alt Text Review, and the first picture without alt text.",
                ),
                Step(
                    title="Choose one you know",
                    body=(
                        "Arrow through the list to a picture you can describe: one you took "
                        "or chose yourself. Skip any you are unsure of; there is no need to "
                        "do them all today."
                    ),
                    keys=("Down",),
                    hear="Each picture's name and where it is used.",
                ),
                Step(
                    title="Write what it shows",
                    body=(
                        "Type one plain sentence about what the picture shows and why it is "
                        "there, then save. Only that picture changes."
                    ),
                    keys=("Enter",),
                    hear="Saved the alt text, and the next picture.",
                ),
            ),
            closing="One picture on your site can now be heard as well as seen.",
            then=("first-week-4-check",),
        ),
        Tutorial(
            slug="first-week-4-check",
            title="Day 4: Fix one thing the check finds",
            track=track,
            minutes=8,
            surfaces=surfaces,
            summary=(
                "Check the whole site for problems, read what was found, and fix one finding "
                "you understand, knowing it can be undone."
            ),
            steps=(
                row(
                    "check_site",
                    title="Check the whole site",
                    body=(
                        "Check the Whole Site reads your pages and posts and lists what it "
                        "found: missing alt text, skipped headings, links that go nowhere. "
                        "Reading changes nothing."
                    ),
                    hear="How many pages were checked, then each finding.",
                ),
                Step(
                    title="Pick one finding",
                    body=(
                        "Arrow through the findings and pick one you understand, such as a "
                        "skipped heading level. Each finding says which page and what is "
                        "wrong."
                    ),
                    keys=("Down",),
                    hear="Each finding, with its page.",
                ),
                Step(
                    title="Fix that one",
                    body=(
                        "Where a finding offers a fix, choose it for that one only. You see "
                        "the change before it is sent, and nothing else on the site is "
                        "touched."
                    ),
                    keys=("Enter",),
                    hear="What will change, then the fix said in words.",
                ),
                row(
                    "undo_site_fix",
                    title="Know how to take it back",
                    body=(
                        "Undo Site Fix lists the fixes made from the check and puts any of "
                        "them back as it was. You do not need it today; it is good to know "
                        "where it is."
                    ),
                    hear="Undo Site Fix, and the fix you just made.",
                ),
            ),
            closing="One real problem fewer on your site, and a way back if you ever need one.",
            then=("first-week-5-comments",),
        ),
        Tutorial(
            slug="first-week-5-comments",
            title="Day 5: Answer your comments",
            track=track,
            minutes=6,
            surfaces=surfaces,
            summary=(
                "Hear the comments waiting on your site, and approve or answer one you choose. "
                "Nothing is deleted."
            ),
            steps=(
                row(
                    "comments",
                    title="Open Comments",
                    body=(
                        "Comments lists the comments on your site, waiting ones first, with "
                        "who wrote them and on which post. If none are waiting, that is a "
                        "good day."
                    ),
                    hear="Each comment's author, its post, and whether it is waiting.",
                ),
                Step(
                    title="Approve one you are happy with",
                    body=(
                        "On a waiting comment you want visitors to see, choose Approve. It "
                        "goes on the site under its post. Leave any you are unsure of where "
                        "they are."
                    ),
                    keys=("Enter",),
                    hear="Approved, and the author's name.",
                ),
                Step(
                    title="Answer one",
                    body=(
                        "On a comment that asks something, choose Reply and write your "
                        "answer. It appears under theirs, as you, when you send it."
                    ),
                    hear="Reply, and the box for your answer.",
                    note="Spam can wait for another day; marking it spam is never urgent.",
                ),
            ),
            closing="Somebody who wrote to your site has heard back from you.",
            then=("first-week-6-menu",),
        ),
        Tutorial(
            slug="first-week-6-menu",
            title="Day 6: Look after your menu",
            track=track,
            minutes=6,
            surfaces=surfaces,
            summary=(
                "Hear your site's menu as a visitor meets it, add one page to it if you want "
                "to, and learn where its earlier versions are."
            ),
            steps=(
                row(
                    "menus",
                    title="Open Menus",
                    body=(
                        "Menus lists your site's menus and each one's items in order: the "
                        "first thing a visitor meets on every page."
                    ),
                    hear="Each menu, and its items in order.",
                ),
                Step(
                    title="Add a page if one is missing",
                    body=(
                        "If an important page, such as Contact, is not in the menu, add it "
                        "and put it where it belongs. If the menu is right as it is, leave it."
                    ),
                    keys=("Enter",),
                    hear="What will change, then the menu again.",
                ),
                row(
                    "menu_history",
                    title="Know where its earlier versions are",
                    body=(
                        "Menu History keeps the menu as it was before each change, so any "
                        "version can be put back. That is why trying a change here is safe."
                    ),
                    hear="Menu History, newest first.",
                ),
            ),
            closing="Your menu is the way you want it, and it can always go back.",
            then=("first-week-7-publish",),
        ),
        Tutorial(
            slug="first-week-7-publish",
            title="Day 7: Publish when you are ready",
            track=track,
            minutes=7,
            surfaces=surfaces,
            summary=(
                "Open the draft from day 2, check it, and publish it, schedule it, or keep it "
                "as a draft: the choice is yours."
            ),
            steps=(
                row(
                    "open",
                    title="Open your draft",
                    body=(
                        "Open Page or Post lists your site's pages and posts, drafts included. "
                        "Choose the draft you saved on day 2."
                    ),
                    hear="Your draft's title, in the editor.",
                ),
                row(
                    "check",
                    title="Check it before publishing",
                    body=(
                        "Check Before Publishing reads the post the way a careful editor "
                        "would: headings, link text, pictures without alt text. Fix what it "
                        "finds first."
                    ),
                    hear="What the check found, or that it found nothing.",
                ),
                row(
                    "publish",
                    title="Publish it, or not yet",
                    body=(
                        "Publish or Update asks before anything goes public. Say yes if you "
                        "are ready; say no and it stays a draft. Nothing is lost either way."
                    ),
                    hear="Publish this post, and the question.",
                    note="Schedule Publish is the other answer: it goes public by itself later.",
                ),
            ),
            closing=(
                "That is your first week: a site you have connected, written on, described, "
                "checked, answered and arranged. The WordPress track goes further."
            ),
        ),
    )
