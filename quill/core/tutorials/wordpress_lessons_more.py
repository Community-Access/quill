"""The last four WordPress lessons: pictures, the check, versions, comments.

Split from :mod:`quill.core.tutorials.wordpress_lessons` to stay under the
module size cap; that module has the examples, the key layer and the first
three lessons, and assembles all seven.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.tutorials.model import Step, Tutorial
from quill.core.tutorials.wordpress_lessons import SITE_NAME, layer_keys

__all__ = ["later_wordpress_lessons"]


def later_wordpress_lessons(
    command: Callable[[str], str],
    *,
    track: str,
    surfaces: tuple[str, ...],
    app: str,
) -> tuple[Tutorial, ...]:
    """Lessons four to seven, with the same arguments as the first three."""
    return (
        Tutorial(
            slug="wordpress-pictures",
            title="Pictures with alternative text",
            track=track,
            minutes=6,
            surfaces=surfaces,
            summary=(
                "Put a picture from the site's Media Library into a post with good "
                "alternative text, and fix a picture in the library that has none."
            ),
            steps=(
                Step(
                    title="Open a post to put a picture in",
                    body=(
                        "Choose Open Page or Post and pick Posts. Type part of a title "
                        "in Find by title or status and press Enter, then Enter again "
                        "on the one you want. The post you wrote earlier is a good one."
                    ),
                    command=command("open"),
                    keys=layer_keys("open"),
                    hear="Each row's title, its status, and when it last changed.",
                ),
                Step(
                    title="Choose a picture from the library",
                    body=(
                        "Put the cursor where the picture should go. In the Insert "
                        "menu, choose Picture from the Media Library, and pick "
                        "photo-volunteers from the list."
                    ),
                    command=command("insert_from_library"),
                    keys=layer_keys("insert_from_library"),
                    hear="Insert from Media Library, and the Files list, newest first.",
                ),
                Step(
                    title="Listen to the alternative text",
                    body=(
                        "A picture dialog opens on Alternative text. That is what a "
                        "screen reader says in place of the picture, so it should say "
                        "what the picture shows and why it is there. This one already "
                        "has some, from the library."
                    ),
                    hear=('Alternative text, "Volunteers sorting donations at the spring fair".'),
                    note=(
                        "Suggest Alternative Text asks your chosen AI for a first try. "
                        "Check the Decorative box for a picture that adds nothing a "
                        "visitor needs, like a divider."
                    ),
                ),
                Step(
                    title="Insert it",
                    body=(
                        "Change the text if you can say it better for this post, then "
                        "press Insert. The text belongs to this placement, so the same "
                        "picture can say something different in another post."
                    ),
                    hear='"Picture inserted:" and its alternative text.',
                ),
                Step(
                    title="Find a picture with none",
                    body=(
                        "Open the Media Library, in Tools, WordPress. Type banner in "
                        "Find and press Enter. The wide-banner picture has no "
                        "alternative text, and its row says so."
                    ),
                    command=command("media_library"),
                    keys=layer_keys("media_library"),
                    hear="Each file's title, type, size, alternative text and date.",
                ),
                Step(
                    title="Give it alternative text",
                    body=(
                        "With wide-banner selected, press Edit Alternative Text, write "
                        "a short description, and press OK. This changes the library's "
                        "own text, which new placements start from."
                    ),
                    hear=f'"Alternative text saved on {SITE_NAME}."',
                ),
                Step(
                    title="Review every picture in the post",
                    body=(
                        "Back in your post, Alt Text Review, in Tools, WordPress, lists "
                        "every picture with its text, so the empty ones and the weak "
                        "ones are easy to find and fix."
                    ),
                    command=command("alt_text_review"),
                    keys=layer_keys("alt_text_review"),
                    hear="How many pictures there are, and how many to look at.",
                ),
            ),
            closing=(
                "Every picture now says something to somebody who cannot see it. "
                "Check Before Publishing finds any you missed."
            ),
            then=("wordpress-check",),
        ),
        Tutorial(
            slug="wordpress-check",
            title="Check Before Publishing",
            track=track,
            minutes=5,
            surfaces=surfaces,
            summary=(
                "Have a post checked for the problems that trip up visitors, go to "
                "each one, and fix it before anybody else meets it."
            ),
            steps=(
                Step(
                    title="Open the post with problems",
                    body=(
                        "Choose Open Page or Post and pick Posts. Type draft in Find "
                        "by title or status and press Enter. On the test site, open "
                        "Things to check before publishing. It was made with one "
                        "problem of each kind."
                    ),
                    command=command("open"),
                    keys=layer_keys("open"),
                    hear="Things to check before publishing, Draft, and when it last changed.",
                ),
                Step(
                    title="Run the check",
                    body=(
                        "In the Tools menu, open WordPress and choose Check Before "
                        "Publishing. It reads the whole post the way a careful visitor "
                        "would, and nothing on the site changes."
                    ),
                    command=command("check"),
                    keys=layer_keys("check"),
                    hear=(
                        "How many things there are to look at, with the problems and "
                        "the things to check counted separately."
                    ),
                ),
                Step(
                    title="Listen to the list",
                    body=(
                        "Arrow down Things to look at. Each one says what to look at "
                        "and why: a heading 1 in the body, a skipped heading level, "
                        "link text that says click here, a picture with no alternative "
                        "text, a table with no header row, and a few more."
                    ),
                    hear="One finding a line, each with its reason.",
                ),
                Step(
                    title="Go to one",
                    body=(
                        "Press Go to It on the finding you want to fix. The list "
                        "closes and the cursor lands on that place in the post, so you "
                        "can fix it there and then."
                    ),
                    hear="The line of the post the finding is about.",
                ),
                Step(
                    title="Fix it, and check again",
                    body=(
                        "Make the fix, then run Check Before Publishing again. Work "
                        "down the list until it is empty, or until what is left is "
                        "something you chose on purpose."
                    ),
                    command=command("check"),
                    keys=layer_keys("check"),
                    hear=(
                        'One fewer each time, and at the end, "Ready to publish: no '
                        'problems found".'
                    ),
                    note=(
                        "None of the findings stops you publishing. Publish runs the "
                        "same check and reads you the summary in its question."
                    ),
                ),
            ),
            closing=(
                "The check is the second pair of eyes a sighted editor has by "
                "default. Run it before every publish; it costs a few seconds."
            ),
            then=("wordpress-versions",),
        ),
        Tutorial(
            slug="wordpress-versions",
            title="Go back to a previous version",
            track=track,
            minutes=5,
            surfaces=surfaces,
            summary=(
                "Hear the earlier versions of a post, the ones kept on this computer "
                "and the site's own history, read one, and put it back."
            ),
            steps=(
                Step(
                    title="Open a post with a history",
                    body=(
                        "Open the welcome post again with Open by Web Address. The test "
                        "site changed it three times when it was set up, so it has a "
                        "history to look through."
                    ),
                    command=command("open_by_address"),
                    keys=layer_keys("open_by_address"),
                    hear="Opened Welcome to the test site, or your working copy of it.",
                ),
                Step(
                    title="Open Previous Versions",
                    body=(
                        "In the File menu, open WordPress and choose Previous Versions. "
                        f"It lists the versions {app} kept, newest first, and then the "
                        "site's own history."
                    ),
                    command=command("versions"),
                    keys=layer_keys("versions"),
                    hear="Each row's date, title, and why it was kept, such as On the site.",
                ),
                Step(
                    title="Read one before choosing",
                    body=(
                        "Select a version and press View. The whole text opens in a "
                        "window of its own, where you can read it or copy a paragraph "
                        "out of it. Escape brings you back to the list."
                    ),
                    hear="The Version window, with the title and then the text.",
                ),
                Step(
                    title="Put it back",
                    body=(
                        "Press Restore on the version you want. It goes into the "
                        "editor in place of your text, and nothing is sent to the "
                        "site until you choose to."
                    ),
                    hear=(
                        '"Version put in the editor. Nothing was sent; your text before '
                        'is in Previous Versions."'
                    ),
                ),
                Step(
                    title="Hear what is different",
                    body=(
                        "Compare with Site, in File, WordPress, lists the differences "
                        "between the site's copy and yours, a line at a time. It is the "
                        "check worth making before you send a restored version."
                    ),
                    command=command("compare"),
                    keys=layer_keys("compare"),
                    hear="Lines starting Site: for the site's copy, and Yours: for yours.",
                    note=(
                        "Changed your mind? Your text from before the restore is the "
                        "newest row in Previous Versions, marked Before restore."
                    ),
                ),
            ),
            closing=(
                "Nothing you send is ever lost: the site's copy is kept before every "
                "update. Restore is the way back, and it never publishes."
            ),
            then=("wordpress-comments",),
        ),
        Tutorial(
            slug="wordpress-comments",
            title="Answer comments",
            track=track,
            minutes=5,
            surfaces=surfaces,
            summary=(
                "Hear the comments waiting for you, reply to one, approve it, and "
                "deal with the spam."
            ),
            steps=(
                Step(
                    title="Open Comments",
                    body=(
                        "In the Tools menu, open WordPress and choose Comments. It "
                        "starts with the ones waiting for you, because those are the "
                        "ones nobody else can see yet."
                    ),
                    command=command("comments"),
                    keys=layer_keys("comments"),
                    hear=(
                        "Comments: Waiting, and the site's name, then the list. On the "
                        "test site, Alex asks when the next session starts."
                    ),
                ),
                Step(
                    title="Read the whole comment",
                    body=(
                        "Each row says who wrote it, on which post, when, and its first "
                        "words. Tab to Details to read the whole comment before you "
                        "decide what to do."
                    ),
                    hear="The comment's full text.",
                ),
                Step(
                    title="Reply to it",
                    body=(
                        "Tab back to the list and press Reply. Write your answer and "
                        "press OK. It is published under your name, under the comment "
                        "it answers."
                    ),
                    hear=f'"Reply to Alex published on {SITE_NAME}."',
                ),
                Step(
                    title="Approve it",
                    body=(
                        "Press Approve on the comment. It goes on the site for everybody "
                        "to read, and leaves this list of waiting ones."
                    ),
                    hear='"Comment from Alex approved."',
                    note=(
                        "Spam and Trash are beside Approve, for the comments that "
                        "should never be seen."
                    ),
                ),
                Step(
                    title="Look in the spam",
                    body=(
                        "Press Show and choose Spam. WordPress catches most junk by "
                        "itself, but now and then a real comment lands here, and Not "
                        "Spam sends it back to Waiting."
                    ),
                    hear="Comments: Spam, and the comments in it.",
                ),
            ),
            closing=(
                "Waiting Count on First Use, in the same window, has the number of "
                "waiting comments said to you the first time you use the site in a "
                "session, so they never pile up unnoticed."
            ),
        ),
    )
